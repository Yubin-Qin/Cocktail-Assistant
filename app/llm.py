"""LLM layer: a thin, OpenAI-compatible client wrapped around the bartender
persona. Streams chat completions and extracts structured recipes the model
emits inline.
"""
from __future__ import annotations

import json
import re
import time
from typing import AsyncIterator

from openai import AsyncOpenAI

from .config import settings

# --------------------------------------------------------------------------- #
# Client (lazily created so importing this module never requires a key)
# --------------------------------------------------------------------------- #

_client: AsyncOpenAI | None = None


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-configured",
        )
    return _client


def configured() -> bool:
    return settings.llm_configured


def reset_client() -> None:
    """Drop the cached client so the next call picks up new config."""
    global _client
    _client = None


def _clean_error(exc: Exception) -> str:
    """Reduce an OpenAI/HTTP exception to a short, readable message for the UI."""
    msg = getattr(exc, "message", None) or str(exc)
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        inner = body.get("message") or body.get("error")
        if isinstance(inner, str) and inner:
            msg = inner
        elif isinstance(inner, dict) and inner.get("message"):
            msg = str(inner["message"])
    return msg.strip()[:400] or str(exc)


# --------------------------------------------------------------------------- #
# Bartender persona + output protocol
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """\
你是「调酒师」——一位经验丰富、温暖、有品位的专业调酒师，经营一家小而精致的吧台。
You are "The Bartender" — an experienced, warm, tasteful professional running a small, \
refined bar.

## 你的两件事 / Your two jobs
1. **回答调酒问题 / Answer bartending questions** — 配方、器具、技巧、替代材料、风味原理、\
基酒知识、餐酒搭配等。基于下方「酒吧知识库」作答；若知识库没有，诚实说明并给出专业判断。
   Recipe specs, tools, technique, substitutions, flavor theory, base spirits, pairings. \
Ground answers in the "Bar Knowledge Base" below; if it's not there, say so and give a \
reasoned, professional opinion.

2. **与客人共同设计特调 / Co-design a signature with the guest** — 这是核心体验。当客人想要\
一杯专属酒时，**不要立刻给配方**，而是先像真实调酒师一样聊几句：了解 ta 的故事、心情、\
偏好的风味层次（甜/酸/苦/烈/花香/烟熏…）、基酒倾向、想要的酒精度与杯型。可以主动问 1–2 个\
关键问题，也可以提议 1–2 个方向让客人选。一起把「这杯酒要讲什么」聊清楚，再落配方。
   This is the core experience. When a guest wants a signature, **do not jump to a recipe**. \
First chat like a real bartender: understand their story, mood, preferred flavor layers \
(sweet/sour/bitter/strong/floral/smoky…), base-spirit leanings, desired ABV and glassware. \
Ask 1–2 key questions or offer 1–2 directions to choose from. Nail down "what is this drink \
about" together, then commit to a recipe.

## 关于「情绪」/ On mood
知识库里每款经典/无酒精酒都标注了 `mood:`（情绪特征）。当客人描述一种心情时，先用它去匹配\
已有酒款（"这种心情，我们酒吧刚好有一杯…"）；若要新设计，让新酒的 `story` 清楚呼应那份情绪。
Every classic/mocktail in the knowledge base has a `mood:` tag. When a guest describes a \
feeling, first match it to an existing drink ("for that mood, we happen to have…"); when \
designing new, make the new drink's `story` clearly echo that mood.

## 短期记忆 / Memory
你会看到「短期记忆」一栏——里面是你和这位客人过往的记录（ta 喝过什么、偏好、聊过的故事）。\
**自然地用上它**：可以提"上次那杯…"、"记得你偏好苦味"等，但别生硬复述。
You'll see a "Short-term memory" section — notes from past visits with this guest \
(what they've had, preferences, stories). Use it naturally ("last time you had…", \
"remembering you like bitter"), without reciting it verbatim.

## 设计要「站在真实配方上」/ Design from real recipes, don't freestyle
设计特调时，**优先改编**「相关参考」里按客人描述匹配到的真实配方（结构、比例、技法），\
而不是凭空捏造。可以在对话里说明你借用了哪杯的骨架、做了什么调整。这让新酒更可复现、更平衡。
When designing, **adapt from** the real recipes in "Relevant references" (structure, ratios, \
technique) rather than inventing from nothing. Say which you borrowed a skeleton from and \
what you changed — this keeps new drinks reproducible and balanced.

## 当前酒库优先 / Respect the current cellar
你会看到「当前酒库」一栏。设计特调和回答“我现在能调什么”时，**优先使用当前拥有的材料**。\
杯子不算库存；冰块和水默认可用。若某个关键材料缺失，不要假装它存在：先说明缺什么，再给出\
已有材料内的替代方向。最终完整配方默认只使用当前拥有的材料，除非客人明确接受采购或替代。
You'll see a "Current cellar" section. When designing signatures or answering what can be \
made now, **prioritize in-stock ingredients**. Glassware is not inventory; ice and water are \
assumed available. If a key ingredient is missing, say so and suggest an in-cellar substitute. \
Final recipes should use in-stock ingredients unless the guest explicitly accepts buying or \
substituting something.

## 风格 / Style
- 像吧台对面的人在聊天：自然、有温度、不啰嗦。Like talking across the bar: natural, warm, concise.
- 用客人使用的语言回复（中文问就中文答，英文问就英文答）。Reply in the guest's language.
- 设计特调时讲清楚「为什么这么配」——风味层次、结构、情绪逻辑。
- 所有用量用公制（ml / g / dash），基酒在前。
- 安全与法律：可主动推荐无酒精（mocktail）方案；可以提供高酒精鸡尾酒（如长岛冰茶）；不主动提供危险饮法（如B52轰炸机需要点燃后饮用）。

## 当你端出一杯原创特调时 / When you serve an original signature
**铁律 / Hard rule**：当你在一条回复里**创作、命名并端出一杯原创特调**（无论你主动提议还是
应客人要求），**这条回复就必须以它的 ```json 配方块结尾**。演绎（量酒、摇壶、讲风味故事、
命名）在前，```json 紧跟在后——二者是**同一条回复、一次性发出**的整体。**绝不要只演绎、只命名、
只描述一杯原创酒却忘了 json**：没有 json，前端就无法生成配方卡，客人就拿不到能保存/复刻的配方。
那等于把酒端到客人面前却不给配方。如果你已经摇完壶、起了名字、推杯过去——现在就把 json 补上。

> 仅在「推荐一款**已有**的经典 / 无酒精酒」时**不需要** json（那是检索，不是创作）。任何
> **原创**特调都必须配 json。

**Hard rule**: whenever you create, name, and serve an ORIGINAL signature in a reply (whether you
proposed it or the guest asked), **that reply MUST end with its ```json recipe block**. The
performance (pouring, shaking, flavor, story, naming) comes first; the ```json follows
immediately — they are ONE reply, sent together. **Never roleplay making, naming, or describing
an original drink without appending its json** — without json the UI renders no recipe card and
the guest gets nothing saveable. If you've already shaken, named it, and slid the glass over,
emit the json now.

> Recommending an EXISTING classic/mocktail needs NO json (that's retrieval, not creation). Any
> ORIGINAL signature MUST come with json.

1. 自然语言铺垫（客人唯一会实时看到的部分）：像真实调酒师那样说一句"让我想想……"+ 你的
   思路与命名，例如"让我想想……午后慵懒，我用接骨木花的清雅做骨架、再轻盈收尾……这一杯，我叫
   它『周日花园』。配方是这样：". 不要直接吐 json，也**不要只演绎不收尾**。
2. 紧跟一个独立的 ```json 代码块——前端会把它渲染成配方卡，所以**只放结构化数据**，别写闲聊。

1. Lead with natural language (the only part streamed to the guest): "Let me think… a slow
   afternoon, I'll build on an elderflower base and finish it light and floral… I'll call this
   one 'Sunday Garden'. Here's the recipe:" — never dump JSON raw, and never stop at the
   performance.
2. Then a single ```json block — the UI renders it as a card, so put only structured data inside.

```json
{
  "name": {"zh": "中文名", "en": "English Name"},
  "type": "signature",
  "base": "Gin",
  "glass": "Coupe",
  "garnish": "橙皮 / Orange peel",
  "abv": "~18%",
  "flavor": "1–2 句风味描述（入口、中段、收尾）/ 1–2 sentences on the taste",
  "mood": "这杯酒适合的情绪或场合 / the mood or occasion it suits",
  "tags": ["aperitif", "floral"],
  "story": "1–2 句设计理念与情绪 / design rationale + mood",
  "ingredients": [{"amount": "45 ml", "item": "Gin 金酒"}],
  "steps": ["1. ...", "2. ..."],
  "bartender_notes": "平衡要点、可调方向、常见错误",
  "variants": "可选的一两句变体建议 / optional"
}
```

注意 / Notes:
- `ingredients` 至少 3 项；`steps` 是完整的、可执行的步骤；`story` 要呼应客人给的故事/心情。
- `flavor` 与 `mood` 是字符串（不是数组），尽量像知识库里 `风味特征`/`情绪特征` 那样写得具体、有画面。
- 最终配方应优先使用「当前酒库」中已有材料；若使用替代项，在 `bartender_notes` 里写清楚原材料、替代材料和风味影响。
- 原创特调的演绎与 ```json **在同一条回复**发出、且只发一次；纯问答或推荐已有酒款时不要输出 json。
"""


# --------------------------------------------------------------------------- #
# Streaming chat
# --------------------------------------------------------------------------- #

async def chat_stream(history: list[dict], context: str) -> AsyncIterator[str]:
    """Yield assistant text deltas, with the knowledge-grounded system prompt prepended."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}]
    for m in history:
        role = m.get("role")
        if role in ("user", "assistant") and m.get("content"):
            messages.append({"role": role, "content": m["content"]})

    stream = await client().chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        stream=True,
        temperature=0.85,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# --------------------------------------------------------------------------- #
# Memory helpers (cheap, non-streaming calls)
# --------------------------------------------------------------------------- #

async def extract_memory_delta(history: list[dict]) -> str:
    """Extract at most one durable memory note from the latest exchange.

    Returns a short Chinese sentence, or "" if nothing worth remembering.
    """
    recent = [m for m in history if m.get("role") in ("user", "assistant")][-6:]
    if not recent:
        return ""
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    messages = [
        {"role": "system", "content": (
            "你是一个记忆助手。读取最近一段调酒师与客人的对话，提炼**最多 1 条**值得长期记住的"
            "事实（例如：客人喝过/点过哪杯、口味偏好、忌口、情绪或故事背景、喜欢的风格）。"
            "用一句简短中文输出，开头不要加前缀。如果没有任何值得记住的内容，只输出英文单词 NONE。"
            "不要输出任何解释或多余文字。"
        )},
        {"role": "user", "content": convo},
    ]
    try:
        resp = await client().chat.completions.create(
            model=settings.llm_model, messages=messages, temperature=0, max_tokens=80
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001 — memory is best-effort
        return ""
    if not text or text.upper().startswith("NONE"):
        return ""
    return text


async def distill_conversation(history: list[dict], drink_name: str) -> str:
    """Distill a design thread into a short narrative memory for the saved drink."""
    convo = "\n".join(
        f"{m['role']}: {m['content']}" for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    )
    messages = [
        {"role": "system", "content": (
            "你是一个记忆助手。下面是调酒师与客人共同设计一杯特调的对话，最终酒款名为"
            f"「{drink_name}」。请把它提炼成 2–4 句中文叙事，记录：客人最初的需求/心情、"
            "你们讨论的方向与取舍、最终为什么这样配。只输出叙事本身，不要标题、不要 json。"
        )},
        {"role": "user", "content": convo[:6000]},
    ]
    try:
        resp = await client().chat.completions.create(
            model=settings.llm_model, messages=messages, temperature=0.3, max_tokens=260
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"（对话摘要失败：{str(exc)[:80]}）"


# --------------------------------------------------------------------------- #
# Smart substitution helpers (non-streaming, structured JSON)
# --------------------------------------------------------------------------- #

def _judge_fewshot_turns(fewshot):
    """Render substitution few-shot examples as user/assistant pairs for the
    judge prompt (calibrates verdict + confidence from a 0–10 score)."""
    turns = []
    for e in fewshot or []:
        try:
            s = int(e.get("substitutability"))
        except (TypeError, ValueError):
            continue
        verdict = "yes" if s >= 7 else "conditional" if s >= 4 else "no"
        conf = "high" if (s >= 8 or s <= 2) else "medium"
        turns.append({"role": "user", "content":
            f"missing={e.get('missing','')}; sub={e.get('substitute','')} ({e.get('substitute_purpose','')})"})
        turns.append({"role": "assistant", "content": json.dumps({
            "missing_id": e.get("missing", ""), "substitute_id": e.get("substitute", ""),
            "verdict": verdict, "confidence": conf, "conditions": "",
            "dosage_note": "", "reason": str(e.get("rationale", "") or ""),
        }, ensure_ascii=False)})
    return turns


def _resolve_fewshot_turns(fewshot):
    """Render few-shot examples for the unknown-name resolver (reinforces the
    'uncertain -> null' rule with explicit null examples)."""
    turns = []
    for e in fewshot or []:
        turns.append({"role": "user", "content": e.get("raw", "")})
        turns.append({"role": "assistant", "content": json.dumps({
            "raw": e.get("raw", ""),
            "mapped_id": e.get("mapped_id", "") or None,
            "substitute_id": e.get("substitute_id", "") or None,
            "confidence": e.get("confidence", "medium"),
            "reason": e.get("reason", ""),
            "dosage_note": e.get("dosage_note", ""),
        }, ensure_ascii=False)})
    return turns


def _extract_json_array(text: str) -> list | None:
    """Tolerantly pull the first JSON array out of an LLM reply."""
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


async def infer_profiles(items: list[dict], cli=None, model: str | None = None) -> list[dict]:
    """Infer a flavor/family/function/abv/intensity profile per ingredient.

    ``items`` is a list of ``{id, zh, en, category, ...}``. Returns a list of
    profile dicts (each carrying ``id``), best-effort; never raises.
    """
    if not items:
        return []
    catalog = "\n".join(
        f"- id={it.get('id', '')} | {it.get('zh', '')} / {it.get('en', '')} | cat={it.get('category', '')}"
        for it in items
    )
    messages = [
        {"role": "system", "content": (
            "你是调酒与风味专家。为下列每种材料推断结构化特性,用于判断替代关系。"
            "对每个材料输出一个 JSON 对象,字段:\n"
            "- family: 核心风味族,取自 [orange, elderflower, nut, coffee, berry, herbal, "
            "citrus, caramel, vanilla, spicy, neutral]\n"
            "- flavor: 对象,键取自 [sweet,sour,bitter,citrus,fruity,floral,herbal,spicy,"
            "nutty,coffee,smoky,vanilla,caramel],值 0-3(只写非零项,至少一个 >0)\n"
            "- function: 数组,取自 [sweetener,flavoring,acid,base,dilution,bitter,texture,aromatic]\n"
            "- abv: 酒精度数字(糖浆/果汁/水 0;利口酒 15-40;基酒 40+)\n"
            "- intensity: 风味强度数字(浓缩>1,标准=1,稀释<1)\n"
            "只输出一个 JSON 数组,每个元素都要带 id 字段,顺序对应输入。不要任何其它文字。"
        )},
        {"role": "user", "content": catalog},
    ]
    resp = await (cli or client()).chat.completions.create(
        model=model or settings.llm_model, messages=messages, temperature=0, max_tokens=2000
    )
    text = (resp.choices[0].message.content or "").strip()
    data = _extract_json_array(text)
    return data if isinstance(data, list) else []


async def judge_substitutions(pairs: list[dict], cli=None, model: str | None = None, fewshot=None) -> list[dict]:
    """Judge whether each ``sub`` can substitute for ``missing``.

    ``pairs`` is a list of ``{"missing": {...}, "sub": {...}}`` where each
    side carries id/label/category/family/flavor/function/abv/intensity.
    Returns a list of verdict dicts (each keyed by ``missing_id`` /
    ``substitute_id``), best-effort; never raises.
    """
    if not pairs:
        return []
    body = json.dumps(pairs, ensure_ascii=False)
    messages = [
        {"role": "system", "content": (
            "你是资深调酒师。判断每对材料里 sub 能否在一般鸡尾酒中替代 missing,综合考虑"
            "风味族、风味向量、功能角色、酒精度和强度差异。对每对输出一个 JSON 对象:\n"
            "- verdict: yes | conditional | no\n"
            "- confidence: high | medium | low\n"
            "- conditions: 适用场景或限制(中文,可空字符串)\n"
            "- dosage_note: 用量调整建议(中文,可空字符串)\n"
            "- reason: 一句中文理由\n"
            "只输出一个 JSON 数组,每个元素都要带 missing_id 和 substitute_id 字段,顺序对应输入。"
            "不要任何其它文字。"
        )},
    ]
    if fewshot:
        messages += _judge_fewshot_turns(fewshot)
    messages.append({"role": "user", "content": body[:6000]})
    resp = await (cli or client()).chat.completions.create(
        model=model or settings.llm_model, messages=messages, temperature=0, max_tokens=1800
    )
    text = (resp.choices[0].message.content or "").strip()
    data = _extract_json_array(text)
    return data if isinstance(data, list) else []


async def resolve_unknown_materials(
    items: list[str],
    catalog: list[dict],
    stock: list[str],
    cli=None,
    model: str | None = None,
    fewshot=None,
) -> list[dict]:
    """Conservatively map unrecognized ingredient names to catalog entries or
    in-stock substitutes. **Never hallucinates**: anything uncertain -> null.

    ``items`` is a list of unknown raw names; ``catalog`` is a list of
    ``{id, zh, en, aliases}``; ``stock`` is a list of in-stock ids. Returns a
    list of ``{raw, mapped_id, substitute_id, confidence, reason, dosage_note}``
    (best-effort; never raises).
    """
    if not items:
        return []
    cat_text = "\n".join(
        f"- {c.get('id','')} | {c.get('zh','')} / {c.get('en','')} | aliases: {', '.join(c.get('aliases', []))}"
        for c in catalog
    )
    msgs = [
        {"role": "system", "content": (
            "你是严谨的调酒材料专家。下面是一些鸡尾酒配方里未能自动识别的材料名，以及当前材料库的"
            "条目清单与库存。对每个未知名做**保守**判断，绝不可臆测：\n"
            "1. mapped_id：它是否**就是**材料库中某条目的同一种材料（同物异名，如『单糖浆』= simple_syrup）？"
            "只有你完全确信是同一材料时才填该 id；否则填 null。\n"
            "2. substitute_id：它能否用材料库某条目**近似替代**？只有你确信在一般鸡尾酒中可替代时才填该 id，"
            "并给出 confidence（high/medium/low）、理由与用量调整；否则填 null。\n"
            "3. 两个都不确定就都填 null —— 不要猜。\n"
            "优先让 substitute_id 命中库存(in_stock)中的材料，更实用。\n"
            "只输出一个 JSON 数组，每个元素 {raw, mapped_id, substitute_id, confidence, reason, dosage_note}。"
            "raw 必须原样回填，mapped_id/substitute_id 为 null 或材料库里的 id。不要输出任何其它文字。"
        )},
    ]
    if fewshot:
        messages += _resolve_fewshot_turns(fewshot)
    messages.append({"role": "user", "content": (
        f"材料库条目（只可选这里的 id）：\n{cat_text}\n\n"
        f"库存(in_stock) ids：{', '.join(stock) or '(空)'}\n\n"
        "未知材料名：\n" + "\n".join(f"- {x}" for x in items)
    )})
    try:
        resp = await (cli or client()).chat.completions.create(
            model=model or settings.llm_model, messages=msgs, temperature=0, max_tokens=2200
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001 — best-effort
        return []
    data = _extract_json_array(text)
    return data if isinstance(data, list) else []


# --------------------------------------------------------------------------- #
# Recipe extraction (the model emits a ```json block when finalizing)
# --------------------------------------------------------------------------- #

_JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def extract_recipe(text: str) -> dict | None:
    """Pull the last fenced JSON object out of an assistant message.

    Returns the parsed dict if it looks like a recipe (has ingredients & steps),
    otherwise None.
    """
    matches = _JSON_FENCE_RE.findall(text)
    for raw in reversed(matches):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and ("ingredients" in data or "steps" in data):
            return data
    return None


# --------------------------------------------------------------------------- #
# Connection test (Settings → Test button)
# --------------------------------------------------------------------------- #

async def test_llm(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Make a tiny chat completion to validate URL/key/model. Never raises.

    Empty ``api_key`` falls back to the currently stored key, so a user can
    test before re-entering it.
    """
    burl = (base_url or settings.llm_base_url).strip()
    key = (api_key and api_key.strip()) or settings.llm_api_key
    mdl = (model or settings.llm_model).strip()

    if not burl:
        return {"ok": False, "error": "Base URL is empty."}
    if not key or key.startswith("sk-your"):
        return {"ok": False, "error": "No API key set. Enter one and try again."}
    if not mdl:
        return {"ok": False, "error": "Model is empty."}

    start = time.monotonic()
    try:
        client = AsyncOpenAI(base_url=burl, api_key=key)
        resp = await client.chat.completions.create(
            model=mdl,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=3,
            temperature=0,
        )
        latency = int((time.monotonic() - start) * 1000)
        reply = ""
        if resp.choices:
            reply = (resp.choices[0].message.content or "").strip()
        return {"ok": True, "latency_ms": latency, "model": mdl, "base_url": burl, "reply": reply}
    except Exception as exc:  # noqa: BLE001 — surface a friendly message
        latency = int((time.monotonic() - start) * 1000)
        return {"ok": False, "error": _clean_error(exc), "latency_ms": latency, "model": mdl, "base_url": burl}
