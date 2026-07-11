"""FastAPI application: serves the recipe API, the SSE bartender chat, and the
static frontend. Run with ``uvicorn app.main:app``.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import cellar, config, llm, memory, recipes, substitutions
from .config import settings
from .knowledge import kb
from .netinfo import lan_ip, url as build_url
from .schemas import CellarIngredientCreate, CellarInventoryUpdate, ChatRequest, LLMConfigRequest, RecipePayload

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
    version="0.2.0",
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
        "cellar": cellar.cellar.summary()["status_counts"],
    }


@app.get("/api/cocktails")
async def list_cocktails(
    type: str | None = Query(default=None, description="classic | signature | mocktail | all"),
    q: str | None = Query(default=None, description="search query"),
    availability: str | None = Query(default=None, description="available | substitutable | missing | all"),
):
    out = []
    for summary in kb.list(type=type, q=q):
        recipe = kb.get(summary.slug)
        item = summary.model_dump()
        if recipe:
            item["availability"] = cellar.cellar.evaluate(recipe)
        if availability and availability != "all":
            if not item.get("availability") or item["availability"]["status"] != availability:
                continue
        out.append(item)
    return out


@app.get("/api/cocktails/{slug}")
async def get_cocktail(slug: str):
    recipe = kb.get(slug)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"Recipe '{slug}' not found")
    item = recipe.model_dump()
    item["availability"] = cellar.cellar.evaluate(recipe)
    return item


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream the bartender's reply as Server-Sent Events.

    Each event is ``data: {"delta": "..."}\\n\\n``; the stream ends with
    ``data: [DONE]\\n\\n``. Errors are surfaced as ``data: {"error": "..."}``.
    After the reply, a best-effort memory note is extracted in the background.
    """
    if not llm.configured():
        return StreamingResponse(
            _error_stream(
                "LLM 尚未配置 / LLM not configured. 请在 ⚙️ 设置 里填好接口与密钥。"
            ),
            media_type="text/event-stream",
        )

    history = [m.model_dump() for m in req.messages]
    last_user = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
    context = kb.build_chat_context(
        query=last_user,
        rolling_memory=memory.load_rolling(),
        conversations=memory.load_conversations_compact(),
    )
    if req.context_summary.strip():
        context += (
            "\n\n## 当前对话较早内容摘要 / Earlier session summary\n"
            "这只是较早上下文的压缩记录，用来理解客人的偏好和已经聊过的方向；"
            "不要逐条回答摘要里的旧问题，优先回应最后一条用户消息。\n"
            f"{req.context_summary.strip()}\n"
        )
    context += "\n\n" + cellar.cellar.build_context()

    async def event_gen():
        full: list[str] = []
        try:
            async for delta in llm.chat_stream(history, context):
                full.append(delta)
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001 — surface to the client
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        # Fire-and-forget: remember anything durable from this exchange.
        asyncio.create_task(_maybe_remember(history, "".join(full)))

    return StreamingResponse(event_gen(), media_type="text/event-stream")


async def _maybe_remember(history: list[dict], assistant_text: str) -> None:
    try:
        delta = await llm.extract_memory_delta(history + [{"role": "assistant", "content": assistant_text}])
        if delta:
            memory.append_rolling(delta)
    except Exception:  # noqa: BLE001 — memory is best-effort, never break chat
        pass


@app.post("/api/recipes/save")
async def save_recipe(payload: RecipePayload):
    """Persist a generated signature to Markdown; distill its design thread to memory."""
    try:
        slug, path = recipes.save_signature(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not save recipe: {exc}")

    drink_name = payload.name.en or payload.name.zh or slug
    memory_saved = False
    if payload.conversation:
        history = [m.model_dump() for m in payload.conversation]
        distilled = await llm.distill_conversation(history, drink_name)
        memory.save_conversation(slug, distilled)
        memory_saved = True
    memory.append_rolling(f"和客人一起设计了特调「{drink_name}」。")
    kb.reload()
    substitutions.engine.mark_dirty(cellar.cellar, reason="recipe")
    return {"slug": slug, "path": str(path), "ok": True, "memory_saved": memory_saved}


@app.delete("/api/cocktails/{slug}")
async def delete_cocktail(slug: str):
    """Delete a saved signature (and its conversation memory). Classics/mocktails are not deletable here."""
    sig_dir = (settings.data_dir / "cocktails" / "signatures").resolve()
    candidate = (sig_dir / f"{slug}.md").resolve()
    try:
        candidate.relative_to(sig_dir)  # guard against path traversal
    except ValueError:
        raise HTTPException(status_code=400, detail="Only saved signatures can be deleted.")
    if not candidate.exists():
        matches = [r for r in kb.by_type("signature") if r.slug == slug]
        if matches:
            for path in sig_dir.glob("*.md"):
                if path.stem == slug:
                    continue
                try:
                    if f"slug: {slug}" in path.read_text(encoding="utf-8"):
                        candidate = path
                        break
                except OSError:
                    continue
        if not candidate.exists():
            raise HTTPException(status_code=404, detail=f"Signature '{slug}' not found.")
    deleted_stem = candidate.stem
    candidate.unlink()
    memory.delete_conversation(slug)
    if deleted_stem != slug:
        memory.delete_conversation(deleted_stem)
    kb.reload()
    substitutions.engine.mark_dirty(cellar.cellar, reason="recipe")
    return {"ok": True, "slug": slug}


@app.get("/api/memory")
async def get_memory():
    return {"rolling": memory.load_rolling(), "conversations": memory.load_conversations_compact()}


@app.post("/api/memory/clear")
async def clear_memory():
    return memory.clear_all()


@app.get("/api/cellar")
async def get_cellar():
    out = cellar.cellar.summary()
    out["matrix_status"] = substitutions.engine.status()
    return out


@app.patch("/api/cellar/inventory")
async def update_cellar_inventory(req: CellarInventoryUpdate):
    try:
        return cellar.cellar.update_inventory(req.ingredient_id, req.status, req.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/cellar/ingredients")
async def add_cellar_ingredient(req: CellarIngredientCreate):
    try:
        return cellar.cellar.add_ingredient(req.name, req.category, req.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/cellar/ingredients/{ingredient_id}")
async def delete_cellar_ingredient(ingredient_id: str):
    try:
        return cellar.cellar.delete_ingredient(ingredient_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/cellar/refresh")
async def refresh_substitutions():
    """Manually trigger a background substitution refresh (matrix + unknowns)."""
    started = substitutions.engine.force_refresh(cellar.cellar, kb)
    return {"started": started, "status": substitutions.engine.status()}


# ---- LLM settings (live URL / key / model + connection test) -------------- #

@app.get("/api/llm/config")
async def get_llm_config():
    """Current LLM config. The key itself is never returned — only a hint."""
    return {
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "has_key": settings.llm_configured,
        "key_hint": config.key_hint(),
    }


@app.post("/api/llm/config")
async def set_llm_config(req: LLMConfigRequest):
    """Update LLM config in memory + .env, then reset the cached client."""
    config.update_llm_config(req.base_url, req.api_key, req.model)
    llm.reset_client()
    return {
        "ok": True,
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "has_key": settings.llm_configured,
        "key_hint": config.key_hint(),
    }


@app.post("/api/llm/test")
async def test_llm(req: LLMConfigRequest):
    """Validate URL/key/model with a tiny chat completion. Never raises."""
    return await llm.test_llm(req.base_url, req.api_key, req.model)


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
