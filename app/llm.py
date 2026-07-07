"""LLM layer: a thin, OpenAI-compatible client wrapped around the bartender
persona. Streams chat completions and extracts structured recipes the model
emits inline.
"""
from __future__ import annotations

import json
import re
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

## 风格 / Style
- 像吧台对面的人在聊天：自然、有温度、不啰嗦。Like talking across the bar: natural, warm, concise.
- 用客人使用的语言回复（中文问就中文答，英文问就英文答）。Reply in the guest's language.
- 设计特调时讲清楚「为什么这么配」——风味层次、结构、情绪逻辑。
- 所有用量用公制（ml / g / dash），基酒在前。
- 安全与法律：不鼓励未成年人或孕妇饮酒，可主动推荐无酒精（mocktail）方案；不提供极致烈酒\
或危险饮法。

## 当要给出一杯完整配方时 / When you commit to a recipe
当讨论成熟、或客人明确说「给我配方 / give me the recipe」时，**先**用 1–2 句话讲设计理念，\
**然后**输出一个独立的 ```json 代码块，严格遵循下面的 schema（必须包含这些键）：

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

注意：
- `ingredients` 至少 3 项；`steps` 是完整的、可执行的步骤；`story` 要呼应客人给的故事/心情。
- `flavor` 与 `mood` 是字符串（不是数组），尽量像知识库里 `风味特征`/`情绪特征` 那样写得具体、有画面。
- 这块 json 是给前端渲染成「配方卡」的，**只**在最终敲定时输出一次，聊天过程中不要反复输出。
- json 之外，正常用自然语言和客人对话。
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
