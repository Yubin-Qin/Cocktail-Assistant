# 🍸 Cocktail — 调酒学习 App

A bilingual (中文 / English) cocktail-learning app with a clean, Apple-style UI. Browse detailed classic cocktails and mocktails step by step, and chat with an AI bartender who answers questions **and** iteratively designs a signature drink from your story, mood, and taste preferences — then saves it back as Markdown.

> 调酒学习 App：中英双语、苹果风格界面。可逐步浏览经典鸡尾酒与无酒精特调的详细做法；也可与 AI 调酒师对话，它会解答问题、并和你一起根据故事/心情/口味偏好**反复打磨**一杯专属特调，最后一键存成 Markdown。

- **Knowledge is data, not code.** Every recipe lives as a Markdown file under `data/`. Add or edit a `.md` and the app picks it up — no code changes, no database.
- **The only external service is an LLM** through an OpenAI-compatible interface (official OpenAI, Azure, Ollama, LM Studio, any gateway).
- **Runs locally, reachable from your phone** on the same Wi-Fi.

---

## ✨ Features / 功能

| | |
| --- | --- |
| 📖 **Recipe library** | Classics, signatures, and mocktails with full step-by-step instructions, ingredients, story, bartender notes, and variations. |
| 🤖 **AI bartender chat** | One conversational interface that (a) answers bartending questions and (b) co-designs a signature with you — discussing flavor layers and mood — then emits a structured recipe card. |
| 💾 **Save to Markdown** | Any generated signature is one click away from becoming a new `.md` under `data/cocktails/signatures/` (and a fresh few-shot example for future designs). |
| 📱 **Mobile + Web** | Responsive, installable-feeling PWA-style UI; auto-detects your LAN address. |
| 🌐 **Bilingual** | Toggle 中/英 in the UI; recipe content is authored bilingually. |

---

## 🚀 Quick start / 快速开始

### Prerequisites
- Python **3.10+** (developed on 3.12)
- An OpenAI-compatible LLM API key (optional for browsing recipes, required for the bartender chat)

### Run it (macOS / Linux)

```bash
cd Cocktail
bash run.sh
```

`run.sh` will, the first time:
1. Create an isolated virtualenv at `./venv` (your system Python stays untouched),
2. Install dependencies from `requirements.txt`,
3. Print your **LAN address** so your phone can connect,
4. Launch the server.

Then open:

- **This computer:** http://localhost:8000
- **Your phone (same Wi-Fi):** the `局域网 / LAN` URL printed in the terminal, e.g. `http://192.168.1.42:8000`

### Configure the LLM

```bash
cp .env.example .env
# then edit .env and set LLM_API_KEY (and LLM_BASE_URL / LLM_MODEL if needed)
```

> **`.env` is gitignored** — it holds your real API key and is never committed. **`.env.example` is the tracked template** you copy from. You can also edit these live in the app's ⚙️ Settings panel (changes persist back to `.env`).
>
> Likewise, `data/cellar/inventory.yml` (your personal liquor stock) is gitignored — copy `data/cellar/inventory.example.yml` to start your own. The bartender's memory under `data/memory/` and AI-generated signatures are also gitignored as personal data.

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | Your API key |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model id |
| `HOST` | `0.0.0.0` | Bind address (`0.0.0.0` = all interfaces / LAN) |
| `PORT` | `8000` | Port |
| `DATA_DIR` | `./data` | Where recipe Markdown lives |

### Manual run (without `run.sh`)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🗂 Project structure / 项目结构

```
Cocktail/
├── app/                     # FastAPI backend
│   ├── main.py              # app, routes, static mount, startup banner
│   ├── config.py            # settings (loaded from .env)
│   ├── knowledge.py         # loads + indexes all recipe Markdown
│   ├── llm.py               # OpenAI client + bartender prompt + streaming
│   ├── recipes.py           # recipe dict <-> Markdown conversion, save()
│   ├── schemas.py           # pydantic models
│   └── netinfo.py           # LAN IP detection
├── data/                    # ← all bartending knowledge lives here
│   ├── README.md            #   how to author a recipe (read this!)
│   ├── _TEMPLATE.md         #   the canonical template
│   ├── cocktails/
│   │   ├── classics/        #   traditional cocktails
│   │   └── signatures/      #   original designs (few-shot examples for the LLM)
│   └── mocktails/           #   non-alcoholic
├── frontend/                # vanilla HTML/CSS/JS (no build step)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── requirements.txt
├── .env.example
└── run.sh
```

---

## ➕ Adding or editing a recipe / 新增或编辑配方

Everything is a Markdown file. See **[`data/README.md`](data/README.md)** for the full field reference and copy `data/_TEMPLATE.md` to start. Short version:

1. Drop a new `my-drink.md` into `data/cocktails/classics/`, `…/signatures/`, or `data/mocktails/`.
2. Fill in the YAML frontmatter (`type`, `base`, `glass`, `flavor`, …) and the bilingual body sections (Story / Ingredients / Steps / Bartender Notes / Variations).
3. Reload the app — it appears in the grid immediately. No restart needed for content edits.

---

## 🧠 How the AI bartender works

- On each message, the backend builds a **knowledge-grounded system prompt**: the *full text of every signature* (house style + few-shot examples) plus a *compact index* of all classics and mocktails.
- The bartender converses naturally. When you and it agree on a direction and you ask it to finalize, it emits a structured recipe as a fenced JSON block; the UI renders that as a recipe card with a **💾 保存为 .md** button.
- Saving writes `data/cocktails/signatures/<slug>.md` — that new file then becomes additional context for future designs.

No vector database, no embeddings, no extra services: the corpus is small enough to ground directly in the prompt, which keeps "the only external interface is an LLM" true.

---

## 🛠 Development

```bash
source venv/bin/activate
uvicorn app.main:app --reload        # hot reload during dev
```

API endpoints: `GET /api/health`, `GET /api/info`, `GET /api/cocktails`, `GET /api/cocktails/{slug}`, `POST /api/chat` (SSE), `POST /api/recipes/save`. Interactive docs at `http://localhost:8000/docs`.

See **[`CONTRIBUTING.md`](CONTRIBUTING.md)** for data-authoring rules, code style, and the PR flow.

---

## 📜 License

MIT — see [`LICENSE`](LICENSE). Recipe data under `data/` is yours to keep, edit, and share.
