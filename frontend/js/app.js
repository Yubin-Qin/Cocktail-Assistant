/* =========================================================================
   Cocktail — front-end logic (vanilla JS, no framework)
   ========================================================================= */
"use strict";

/* ----------------------------- i18n ------------------------------------ */
const I18N = {
  zh: {
    appTitle: "调酒",
    recipes: "菜单", bartender: "调酒师",
    recipesTitle: "鸡尾酒配方",
    recipesSub: "经典、特调与无酒精 — 点开任意一杯查看完整做法。",
    all: "全部", classic: "经典", signature: "特调", mocktail: "无酒精",
    searchPh: "按名字、基酒、风味搜索…",
    composerPh: "和调酒师聊聊你的故事、心情，或问个调酒问题…",
    welcome: "晚上好 🌆 我是你的调酒师。想喝点什么？可以告诉我今晚的故事和心情，我来为你量身定制一杯；也可以问我任何关于调酒的问题。",
    save: "💾 存为 .md", saved: "已保存", viewInMenu: "在菜单中查看",
    ingredients: "配方 Ingredients", steps: "步骤 Steps",
    story: "故事 Story", notes: "调酒师笔记 Bartender Notes", variants: "变体 Variations",
    flavor: "风味", mood: "情绪",
    configWarn: "LLM 尚未配置，请在 .env 设置 LLM_API_KEY 后重启服务。",
    noResults: "没有找到匹配的配方", loading: "加载中…",
    base: "基酒", glass: "杯型", abv: "酒精度", difficulty: "难度",
    chatError: "出错了，请稍后重试",
  },
  en: {
    appTitle: "Cocktail",
    recipes: "Recipes", bartender: "Bartender",
    recipesTitle: "Cocktail Recipes",
    recipesSub: "Classics, signatures & mocktails — tap any card for the full method.",
    all: "All", classic: "Classic", signature: "Signature", mocktail: "Mocktail",
    searchPh: "Search by name, base, flavor…",
    composerPh: "Tell the bartender your story, mood, or ask a question…",
    welcome: "Good evening 🌆 I'm your bartender. What are you in the mood for? Tell me your story or mood tonight and I'll craft something just for you — or ask me anything about cocktails.",
    save: "💾 Save as .md", saved: "Saved", viewInMenu: "View in menu",
    ingredients: "Ingredients", steps: "Steps",
    story: "Story", notes: "Bartender Notes", variants: "Variations",
    flavor: "Flavor", mood: "Mood",
    configWarn: "LLM is not configured. Set LLM_API_KEY in .env and restart.",
    noResults: "No matching recipes", loading: "Loading…",
    base: "Base", glass: "Glass", abv: "ABV", difficulty: "Difficulty",
    chatError: "Something went wrong, please retry",
  },
};

const QUICK = {
  zh: [
    "想喝一杯庆祝的，帮我设计一杯",
    "今天有点累，想要舒缓的一杯",
    "聊聊一杯酒的口感层次该怎么设计",
    "Negroni 没有金巴利，怎么替代？",
  ],
  en: [
    "Design me a celebratory drink",
    "I'm tired today — something soothing",
    "How do you design a drink's flavor layers?",
    "How do I substitute Campari in a Negroni?",
  ],
};

/* ----------------------------- state ----------------------------------- */
const state = {
  lang: localStorage.getItem("cocktail.lang") || "zh",
  view: "recipes",
  filter: "all",
  query: "",
  recipes: [],
  info: null,
  chat: [],          // {role, text, recipe?}
  streaming: false,
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const t = (key) => (I18N[state.lang][key] ?? key);
const nameOf = (n) => (n && (n[state.lang] || n.en || n.zh)) || "—";

/* ----------------------------- init ------------------------------------ */
document.addEventListener("DOMContentLoaded", init);

async function init() {
  applyLang();
  bindChrome();
  moveSegThumb();
  await Promise.all([loadInfo(), loadRecipes()]);
  renderGrid();
  renderQuickPrompts();
  initChat();
  window.addEventListener("resize", moveSegThumb);
}

function bindChrome() {
  // segmented view switch
  $$(".seg-btn").forEach((btn) =>
    btn.addEventListener("click", () => switchView(btn.dataset.view))
  );
  // language toggle
  $("#langToggle").addEventListener("click", toggleLang);
  // filters
  $$(".chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      $$(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.filter = chip.dataset.filter;
      renderGrid();
    })
  );
  // search
  $("#searchInput").addEventListener("input", (e) => {
    state.query = e.target.value.toLowerCase().trim();
    renderGrid();
  });
  // sheet close
  $("#sheetClose").addEventListener("click", closeSheet);
  $("#sheetOverlay").addEventListener("click", (e) => {
    if (e.target.id === "sheetOverlay") closeSheet();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSheet();
  });
  // composer
  const input = $("#chatInput");
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });
  $("#sendBtn").addEventListener("click", sendChat);
}

function autosize() {
  const el = $("#chatInput");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
}

/* ----------------------------- language -------------------------------- */
function applyLang() {
  document.documentElement.lang = state.lang;
  $$("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  $$("[data-i18n-ph]").forEach((el) => (el.placeholder = t(el.dataset.i18nPh)));
  $("#langLabel").textContent = state.lang === "zh" ? "中文" : "EN";
}

function toggleLang() {
  state.lang = state.lang === "zh" ? "en" : "zh";
  localStorage.setItem("cocktail.lang", state.lang);
  applyLang();
  renderGrid();
  renderQuickPrompts();
  initChat(true);
}

/* ----------------------------- views ----------------------------------- */
function switchView(view) {
  state.view = view;
  $$(".seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.remove("active"));
  $("#view-" + view).classList.add("active");
  moveSegThumb();
  if (view === "bartender") scrollChatToBottom();
}

function moveSegThumb() {
  const active = $(".seg-btn.active");
  const thumb = $(".seg-thumb");
  if (active && thumb) {
    thumb.style.width = active.offsetWidth + "px";
    thumb.style.left = active.offsetLeft + "px";
  }
}

/* ----------------------------- data ------------------------------------ */
async function loadInfo() {
  try {
    state.info = await fetchJSON("/api/info");
    $("#lanInfo").textContent =
      state.lang === "zh"
        ? `局域网访问 / LAN: ${state.info.lan_url}`
        : `LAN: ${state.info.lan_url}`;
  } catch (e) {
    /* ignore — non-fatal */
  }
}

async function loadRecipes() {
  try {
    state.recipes = await fetchJSON("/api/cocktails");
  } catch (e) {
    state.recipes = [];
  }
}

async function fetchJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

/* ----------------------------- recipes grid ---------------------------- */
function renderGrid() {
  const grid = $("#recipeGrid");
  const empty = $("#recipeEmpty");
  let items = state.recipes;
  if (state.filter !== "all") items = items.filter((r) => r.type === state.filter);
  if (state.query) {
    items = items.filter((r) => {
      const hay = [
        r.name.zh, r.name.en, r.base, r.glass, ...(r.flavor || []), ...(r.tags || []),
      ].join(" ").toLowerCase();
      return hay.includes(state.query);
    });
  }

  if (!items.length) {
    grid.innerHTML = "";
    empty.hidden = false;
    empty.textContent = t("noResults");
    return;
  }
  empty.hidden = true;

  grid.innerHTML = items
    .map((r) => {
      const emoji = emojiFor(r);
      const typeLabel = t(r.type);
      const tags = (r.flavor || []).slice(0, 3).map((x) => `<span class="tag">${escapeHtml(x)}</span>`).join("");
      return `
      <article class="card" data-type="${r.type}" data-slug="${r.slug}">
        <div class="card-banner">
          <span class="card-emoji">${emoji}</span>
          <span class="card-type-pill">${escapeHtml(typeLabel)}</span>
        </div>
        <div class="card-body">
          <h3 class="card-name">${escapeHtml(nameOf(r.name))}</h3>
          <p class="card-sub">${escapeHtml(r.base)} · ${escapeHtml(r.glass)}${r.abv ? " · " + escapeHtml(r.abv) : ""}</p>
          ${r.blurb ? `<p class="card-blurb">${escapeHtml(r.blurb)}</p>` : ""}
          <div class="card-tags">${tags}</div>
        </div>
      </article>`;
    })
    .join("");

  $$(".card").forEach((card) =>
    card.addEventListener("click", () => openRecipe(card.dataset.slug))
  );
}

function emojiFor(r) {
  if (r.type === "mocktail") return "🍹";
  if ((r.flavor || []).includes("smoky")) return "🔥";
  if ((r.flavor || []).includes("coffee")) return "☕";
  if (r.type === "signature") return "✨";
  return "🍸";
}

/* ----------------------------- recipe detail --------------------------- */
async function openRecipe(slug) {
  $("#sheetContent").innerHTML = `<div style="padding:40px;text-align:center;color:var(--text-3)">${t("loading")}</div>`;
  $("#sheetOverlay").hidden = false;
  document.body.style.overflow = "hidden";
  try {
    const r = await fetchJSON(`/api/cocktails/${encodeURIComponent(slug)}`);
    renderSheet(r);
  } catch (e) {
    $("#sheetContent").innerHTML = `<div style="padding:40px;text-align:center">⚠️</div>`;
  }
}

function renderSheet(r) {
  const typeLabel = t(r.type);
  const ings = (r.ingredients || [])
    .map((i) => `<li class="ing-row"><span class="ing-amount">${escapeHtml(i.amount)}</span><span class="ing-item">${escapeHtml(i.item)}</span></li>`)
    .join("");
  const steps = (r.steps || [])
    .map((s) => `<li class="step"><div class="step-text">${inline(s)}</div></li>`)
    .join("");
  const variants = (r.variants || [])
    .map((v) => `<li>${inline(v)}</li>`)
    .join("");

  const meta = [
    r.base && metaPill(t("base"), r.base),
    r.glass && metaPill(t("glass"), r.glass),
    r.abv && metaPill(t("abv"), r.abv),
    r.difficulty && metaPill(t("difficulty"), r.difficulty),
  ].filter(Boolean).join("");

  $("#sheetContent").innerHTML = `
    <div class="sheet-hero" style="background:linear-gradient(135deg, ${heroColors(r.type)})">
      <span class="sheet-type">${escapeHtml(typeLabel)}${r.source ? " · " + escapeHtml(r.source) : ""}</span>
      <h2 class="sheet-name">${escapeHtml(nameOf(r.name))}</h2>
      <p class="sheet-sub">${r.name.zh && r.name.en ? (state.lang === "zh" ? r.name.en : r.name.zh) : ""}</p>
      <div class="sheet-meta">${meta}</div>
      ${r.mood ? `<p class="sheet-mood">“${escapeHtml(r.mood)}”</p>` : ""}
    </div>
    <div class="sheet-body">
      ${section("story", prose(r.story))}
      ${r.flavor_text ? section("flavor", `<div class="note-card">${inline(r.flavor_text)}</div>`) : ""}
      <div class="sheet-section">
        <h4 class="section-title">${t("ingredients")}</h4>
        <ul class="ing-list">${ings || '<li class="ing-row"><span class="ing-item">—</span></li>'}</ul>
      </div>
      ${steps ? `<div class="sheet-section"><h4 class="section-title">${t("steps")}</h4><ol class="steps">${steps}</ol></div>` : ""}
      ${r.notes ? section("notes", `<div class="note-card">${inline(r.notes)}</div>`) : ""}
      ${variants ? section("variants", `<ul class="variant-list">${variants}</ul>`) : ""}
    </div>`;
}

function heroColors(type) {
  return {
    classic: "var(--classic-1), var(--classic-2)",
    signature: "var(--signature-1), var(--signature-2)",
    mocktail: "var(--mocktail-1), var(--mocktail-2)",
  }[type];
}
function metaPill(label, val) {
  return `<span class="meta-pill">${escapeHtml(label)}: ${escapeHtml(val)}</span>`;
}
function section(key, inner) {
  return inner && inner.trim()
    ? `<div class="sheet-section"><h4 class="section-title">${t(key)}</h4><div class="prose">${inner}</div></div>`
    : "";
}

function closeSheet() {
  $("#sheetOverlay").hidden = true;
  document.body.style.overflow = "";
}

/* ----------------------------- chat ------------------------------------ */
function initChat(force) {
  if (state.chat.length && !force) return;
  const messages = $("#chatMessages");
  messages.innerHTML = "";
  if (force) state.chat = [];
  if (!state.chat.length) {
    addMessage("bartender", t("welcome"));
  } else {
    state.chat.forEach((m) => renderMessage(m));
  }
  if (state.info && !state.info.llm_configured) {
    let banner = $("#chatConfigBanner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "chatConfigBanner";
      banner.className = "chat-banner";
      $(".chat-messages").prepend(banner);
    }
    banner.textContent = t("configWarn");
  } else {
    const banner = $("#chatConfigBanner");
    if (banner) banner.remove();
  }
}

function renderQuickPrompts() {
  $("#quickPrompts").innerHTML = QUICK[state.lang]
    .map((q) => `<button class="quick-chip">${escapeHtml(q)}</button>`)
    .join("");
  $$("#quickPrompts .quick-chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      $("#chatInput").value = chip.textContent;
      autosize();
      sendChat();
    })
  );
}

function addMessage(role, text, recipe) {
  const msg = { role, text: text || "", recipe };
  state.chat.push(msg);
  renderMessage(msg);
  scrollChatToBottom();
  return msg;
}

function renderMessage(m) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${m.role}`;
  const avatar = m.role === "bartender" ? "🍸" : "🙂";
  const prose = stripJson(m.text);
  wrap.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">
      ${prose ? `<span class="prose">${escapeHtml(prose)}</span>` : ""}
    </div>`;
  const bubble = $(".msg-bubble", wrap);
  if (m.role === "bartender" && m.recipe) {
    bubble.appendChild(buildRecipeCard(m.recipe));
  }
  $("#chatMessages").appendChild(wrap);
  return wrap;
}

async function sendChat() {
  const input = $("#chatInput");
  const text = input.value.trim();
  if (!text || state.streaming) return;
  input.value = "";
  autosize();

  addMessage("user", text);

  // assistant placeholder
  state.streaming = true;
  setSendDisabled(true);
  const phWrap = renderTypingPlaceholder();

  const history = state.chat
    .filter((m) => m !== phWrap.__msg && m.text)
    .map((m) => ({ role: m.role, content: stripJson(m.text) }));

  let acc = "";
  await streamChat(
    history,
    (delta) => {
      if (!phWrap.__typingReplaced) {
        phWrap.__typingReplaced = true;
        const bubble = $(".msg-bubble", phWrap);
        bubble.innerHTML = `<span class="prose"></span>`;
      }
      acc += delta;
      $(".prose", phWrap).textContent = stripJson(acc);
      scrollChatToBottom();
    },
    () => {
      // finalize
      const recipe = extractRecipe(acc);
      const bubble = $(".msg-bubble", phWrap);
      bubble.innerHTML = "";
      const span = document.createElement("span");
      span.className = "prose";
      span.textContent = stripJson(acc);
      bubble.appendChild(span);
      if (recipe) bubble.appendChild(buildRecipeCard(recipe));
      // record into history
      const msg = { role: "bartender", text: acc, recipe: recipe || undefined };
      state.chat.push(msg);
      state.streaming = false;
      setSendDisabled(false);
      scrollChatToBottom();
    },
    (err) => {
      const bubble = $(".msg-bubble", phWrap);
      bubble.innerHTML = `<span class="prose" style="color:#c0392b">⚠️ ${escapeHtml(t("chatError"))}: ${escapeHtml(err.message)}</span>`;
      state.chat.push({ role: "bartender", text: `⚠️ ${t("chatError")}: ${err.message}` });
      state.streaming = false;
      setSendDisabled(false);
    }
  );
}

function renderTypingPlaceholder() {
  const wrap = document.createElement("div");
  wrap.className = "msg bartender";
  wrap.innerHTML = `
    <div class="msg-avatar">🍸</div>
    <div class="msg-bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
  $("#chatMessages").appendChild(wrap);
  scrollChatToBottom();
  wrap.__msg = { role: "bartender", text: "", _placeholder: true };
  return wrap;
}

function setSendDisabled(disabled) {
  $("#sendBtn").disabled = disabled;
}

function scrollChatToBottom() {
  const s = $("#chatScroll");
  if (s) s.scrollTop = s.scrollHeight;
}

/* SSE streaming over fetch */
async function streamChat(messages, onDelta, onDone, onError) {
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop();
      for (const evt of events) {
        const line = evt.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") return onDone();
        try {
          const obj = JSON.parse(payload);
          if (obj.error) throw new Error(obj.error);
          if (obj.delta) onDelta(obj.delta);
        } catch (e) {
          if (e.message && !e.message.includes("JSON")) throw e;
        }
      }
    }
    onDone();
  } catch (e) {
    onError(e);
  }
}

/* recipe extraction + card */
function extractRecipe(text) {
  const re = /```json\s*(\{[\s\S]*?\})\s*```/g;
  let m, last = null;
  while ((m = re.exec(text)) !== null) last = m[1];
  if (!last) return null;
  try {
    const data = JSON.parse(last);
    if (data && (data.ingredients || data.steps)) return data;
  } catch (e) {}
  return null;
}

function stripJson(text) {
  return (text || "").replace(/```json\s*\{[\s\S]*?\}\s*```/g, "").trim();
}

function buildRecipeCard(r) {
  const name = r.name && (r.name[state.lang] || r.name.en || r.name.zh)
    ? r.name : { zh: "", en: typeof r.name === "string" ? r.name : "" };
  const dispName = typeof r.name === "string" ? r.name : nameOf(r.name);
  const ings = (r.ingredients || [])
    .map((i) => `<div><b style="color:var(--accent)">${escapeHtml(i.amount || "")}</b> ${escapeHtml(i.item || "")}</div>`)
    .join("");
  const moodLine = r.mood ? `<div class="rcm-mood">“${escapeHtml(r.mood)}”</div>` : "";
  const card = document.createElement("div");
  card.className = "chat-recipe";
  card.innerHTML = `
    <div class="recipe-card-mini">
      <div class="rcm-banner">
        <div class="rcm-name">${escapeHtml(dispName)}</div>
        <div class="rcm-sub">${escapeHtml(r.base || "")}${r.glass ? " · " + escapeHtml(r.glass) : ""}${r.abv ? " · " + escapeHtml(r.abv) : ""}</div>
      </div>
      ${moodLine}
      <div class="rcm-body"><div class="rcm-ing">${ings}</div></div>
      <div class="rcm-actions">
        <button class="btn save-btn">${t("save")}</button>
      </div>
    </div>`;
  $(".save-btn", card).addEventListener("click", () => saveRecipe(r, card));
  return card;
}

async function saveRecipe(r, card) {
  const btn = $(".save-btn", card);
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "…";
  try {
    const payload = {
      name: typeof r.name === "string" ? { zh: "", en: r.name } : { zh: r.name.zh || "", en: r.name.en || "" },
      type: r.type || "signature",
      base: r.base || "",
      glass: r.glass || "",
      garnish: r.garnish || "",
      abv: r.abv || "",
      flavor: [],                                  // tags auto-derived on the server
      flavor_text: typeof r.flavor === "string" ? r.flavor : "",
      mood: r.mood || "",
      tags: r.tags || [],
      story: r.story || "",
      ingredients: r.ingredients || [],
      steps: r.steps || [],
      bartender_notes: r.bartender_notes || "",
      variants: r.variants || "",
    };
    const res = await fetchJSON("/api/recipes/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadRecipes();
    renderGrid();
    btn.textContent = "✓ " + t("saved");
    toast(`✓ ${res.slug}.md`);
  } catch (e) {
    btn.disabled = false;
    btn.textContent = original;
    toast("⚠️ " + e.message);
  }
}

/* ----------------------------- helpers --------------------------------- */
function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function inline(s) {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}
function prose(s) {
  return escapeHtml(s || "").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

let toastTimer;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 2600);
}
