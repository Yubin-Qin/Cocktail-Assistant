"""FastAPI application: serves the recipe API, the SSE bartender chat, and the
static frontend. Run with ``uvicorn app.main:app``.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import llm, recipes
from .config import settings
from .knowledge import kb
from .netinfo import lan_ip, url as build_url
from .schemas import ChatRequest, RecipePayload

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# --------------------------------------------------------------------------- #
# Lifespan — print the access banner once on startup
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    lan = lan_ip()
    port = settings.port
    print("\n" + "─" * 60)
    print("🍸  Cocktail app is running  /  调酒学习 App 已启动")
    print("─" * 60)
    print(f"   本机  Local  :  {build_url('localhost', port)}")
    print(f"   局域网 LAN   :  {build_url(lan, port)}    ← 手机访问这个 / open on your phone")
    print(f"   接口文档 Docs:  {build_url('localhost', port)}/docs")
    cfg = "✅ configured" if llm.configured() else "⚠️  not configured (set LLM_API_KEY in .env)"
    print(f"   LLM          :  {settings.llm_model} @ {settings.llm_base_url}  ({cfg})")
    print("─" * 60 + "\n")
    yield


app = FastAPI(
    title="Cocktail App",
    description="Bilingual cocktail-learning app with an AI bartender.",
    version="0.1.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# API routes (registered before the static mount so they take precedence)
# --------------------------------------------------------------------------- #

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/info")
async def info():
    lan = lan_ip()
    return {
        "localhost_url": build_url("localhost", settings.port),
        "lan_url": build_url(lan, settings.port),
        "llm_configured": llm.configured(),
        "llm_model": settings.llm_model,
        "counts": kb.counts(),
    }


@app.get("/api/cocktails")
async def list_cocktails(
    type: str | None = Query(default=None, description="classic | signature | mocktail | all"),
    q: str | None = Query(default=None, description="search query"),
):
    return kb.list(type=type, q=q)


@app.get("/api/cocktails/{slug}")
async def get_cocktail(slug: str):
    recipe = kb.get(slug)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Recipe '{slug}' not found")
    return recipe


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream the bartender's reply as Server-Sent Events.

    Each event is ``data: {"delta": "..."}\\n\\n``; the stream ends with
    ``data: [DONE]\\n\\n``. Errors are surfaced as ``data: {"error": "..."}``.
    """
    if not llm.configured():
        return StreamingResponse(
            _error_stream(
                "LLM 尚未配置 / LLM not configured. 请在 .env 设置 LLM_API_KEY 后重启服务。"
            ),
            media_type="text/event-stream",
        )

    history = [m.model_dump() for m in req.messages]
    context = kb.build_chat_context()

    async def event_gen():
        try:
            async for delta in llm.chat_stream(history, context):
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001 — surface to the client
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/recipes/save")
async def save_recipe(payload: RecipePayload):
    """Persist a generated signature to Markdown and return its slug + path."""
    try:
        slug, path = recipes.save_signature(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not save recipe: {exc}")
    return {"slug": slug, "path": str(path), "ok": True}


# --------------------------------------------------------------------------- #
# Static frontend (mounted last so /api/* wins)
# --------------------------------------------------------------------------- #

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    @app.get("/")
    async def index_fallback():
        return {"message": f"Frontend directory not found at {FRONTEND_DIR}. "
                           "It is created as part of the project."}


async def _error_stream(message: str):
    yield f"data: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
