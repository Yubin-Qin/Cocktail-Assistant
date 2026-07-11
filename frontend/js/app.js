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
    availabilityAll: "全部库存状态", availableNow: "现在可调", substitutableNow: "可替代可调", missingKey: "缺关键材料",
    searchPh: "按名字、基酒、风味搜索…",
    composerPh: "和调酒师聊聊你的故事、心情，或问个调酒问题…",
    welcome: "晚上好 🌆 我是你的调酒师。想喝点什么？可以告诉我今晚的故事和心情，我来为你量身定制一杯；也可以问我任何关于调酒的问题。",
    save: "💾 存为 .md", saved: "已保存", viewInMenu: "在菜单中查看",
    viewDetails: "查看详情",
    ingredients: "配方 Ingredients", steps: "步骤 Steps",
    story: "故事 Story", notes: "调酒师笔记 Bartender Notes", variants: "变体 Variations",
    flavor: "风味", mood: "情绪",
    configWarn: "LLM 尚未配置，请在 .env 设置 LLM_API_KEY 后重启服务。",
    noResults: "没有找到匹配的配方", loading: "加载中…",
    base: "基酒", glass: "杯型", abv: "酒精度", difficulty: "难度",
    chatError: "出错了，请稍后重试",
    settings: "设置", llmHint: "OpenAI 兼容接口。修改会保存到 .env 并立即生效；密钥仅保存在本地服务器。",
    baseUrl: "接口地址", apiKey: "API 密钥", model: "模型",
    test: "测试", save: "保存", testing: "测试中…",
    testOk: "✓ 连接成功", testFail: "✗ 测试失败",
    cfgSaved: "✓ 已保存并生效", keySet: "已设置，输入新值以更换", keyEmpty: "尚未设置密钥",
    preparing: "正在生成特调……",
    memoryTitle: "调酒师记忆", memoryHint: "调酒师会记住你们聊过的内容（喝过什么、偏好、故事）。保存的特调会留下设计对话，直到你删除该特调。",
    clearMemory: "清空记忆", clearMemoryConfirm: "确定清空调酒师的所有记忆吗？已保存的特调配方不会被删除，但它们的设计对话会被清除。",
    memoryCleared: "✓ 记忆已清空",
    deleteSig: "删除这款特调", deleteConfirm: "确定删除这杯特调吗？配方和它的设计对话都会被移除（经典/无酒精配方不可删除）。",
    deleted: "✓ 已删除",
    cellarTitle: "我的酒库", cellarHint: "酒库会影响经典鸡尾酒筛选，也会约束调酒师设计特调。杯子不算库存；冰块和水默认可用。",
    cellarSearchPh: "搜索材料…", cellarSaved: "✓ 酒库已更新",
    addIngredient: "添加", addIngredientPh: "添加材料，如 接骨木花利口酒",
    ingredientAdded: "✓ 已加入酒库",
    ingredientDeleted: "✓ 已删除",
    delete: "删除",
    catAll: "全部",
    cellarAddPh: "搜索 / 添加材料…",
    catLiqueur: "利口酒", catBaseSpirit: "基酒", catBitter: "苦味利口酒", catFortified: "加强葡萄酒",
    catBitters: "苦精", catSweetener: "甜味材料", catCitrus: "柑橘", catJuice: "果汁",
    catMixer: "软饮/气泡", catHerb: "香草", catGarnish: "装饰",
    inStock: "有", lowStock: "少量", missingStock: "没有", ignoredStock: "忽略",
    availability: "可调性", available: "可调", substitutable: "可替代", missing: "缺材料", unknown: "待确认",
    substitute: "替代",
    subConditions: "适用条件", subDosage: "用量调整", subReason: "理由",
    subSourceManual: "手工", subSourceRule: "规则", subSourceLLM: "AI",
    confHigh: "高置信", confMedium: "中", confLow: "低",
    subMatrixRefreshing: "替代知识后台刷新中…", subMatrixReady: "替代知识就绪", subMatrixStale: "替代知识待生成（配置 LLM 后自动构建）",
    refreshSubstitutes: "替代品检索", subRefreshStarted: "✓ 已开始检索", subRefreshAlreadyRunning: "正在检索，请稍候…",
  },
  en: {
    appTitle: "Cocktail",
    recipes: "Recipes", bartender: "Bartender",
    recipesTitle: "Cocktail Recipes",
    recipesSub: "Classics, signatures & mocktails — tap any card for the full method.",
    all: "All", classic: "Classic", signature: "Signature", mocktail: "Mocktail",
    availabilityAll: "All stock states", availableNow: "Available now", substitutableNow: "With substitute", missingKey: "Missing key",
    searchPh: "Search by name, base, flavor…",
    composerPh: "Tell the bartender your story, mood, or ask a question…",
    welcome: "Good evening 🌆 I'm your bartender. What are you in the mood for? Tell me your story or mood tonight and I'll craft something just for you — or ask me anything about cocktails.",
    save: "💾 Save as .md", saved: "Saved", viewInMenu: "View in menu",
    viewDetails: "Details",
    ingredients: "Ingredients", steps: "Steps",
    story: "Story", notes: "Bartender Notes", variants: "Variations",
    flavor: "Flavor", mood: "Mood",
    configWarn: "LLM is not configured. Set LLM_API_KEY in .env and restart.",
    noResults: "No matching recipes", loading: "Loading…",
    base: "Base", glass: "Glass", abv: "ABV", difficulty: "Difficulty",
    chatError: "Something went wrong, please retry",
    settings: "Settings", llmHint: "OpenAI-compatible. Changes save to .env and take effect immediately. The key is stored locally only.",
    baseUrl: "Base URL", apiKey: "API Key", model: "Model",
    test: "Test", save: "Save", testing: "Testing…",
    testOk: "✓ Connected", testFail: "✗ Test failed",
    cfgSaved: "✓ Saved & active", keySet: "set — enter a new value to change", keyEmpty: "No key set",
    preparing: "Generating the recipe…",
    memoryTitle: "Bartender memory", memoryHint: "The bartender remembers what you've talked about (what you've had, preferences, stories). Saved signatures keep their design conversation until you delete that signature.",
    clearMemory: "Clear memory", clearMemoryConfirm: "Clear all bartender memory? Saved signatures won't be deleted, but their design conversations will be erased.",
    memoryCleared: "✓ Memory cleared",
    deleteSig: "Delete this signature", deleteConfirm: "Delete this signature? The recipe and its design conversation will be removed (classics/mocktails can't be deleted here).",
    deleted: "✓ Deleted",
    cellarTitle: "My cellar", cellarHint: "Your cellar powers recipe availability filters and constrains the bartender's custom designs. Glassware is not inventory; ice and water are assumed available.",
    cellarSearchPh: "Search ingredients…", cellarSaved: "✓ Cellar updated",
    addIngredient: "Add", addIngredientPh: "Add ingredient, e.g. Elderflower liqueur",
    ingredientAdded: "✓ Added to cellar",
    ingredientDeleted: "✓ Deleted",
    delete: "Delete",
    catAll: "All",
    cellarAddPh: "Search / add ingredient…",
    catLiqueur: "Liqueur", catBaseSpirit: "Base spirit", catBitter: "Bitter liqueur", catFortified: "Fortified wine",
    catBitters: "Bitters", catSweetener: "Sweetener", catCitrus: "Citrus", catJuice: "Juice",
    catMixer: "Mixer", catHerb: "Herb", catGarnish: "Garnish",
    inStock: "Have", lowStock: "Low", missingStock: "Missing", ignoredStock: "Ignore",
    availability: "Availability", available: "Available", substitutable: "Substitute", missing: "Missing", unknown: "Check",
    substitute: "Substitute",
    subConditions: "Works when", subDosage: "Dosage", subReason: "Why",
    subSourceManual: "manual", subSourceRule: "rule", subSourceLLM: "AI",
    confHigh: "high", confMedium: "medium", confLow: "low",
    subMatrixRefreshing: "Substitution knowledge refreshing…", subMatrixReady: "Substitution knowledge ready", subMatrixStale: "Substitution knowledge pending (builds automatically once LLM is configured)",
    refreshSubstitutes: "Refresh substitutes", subRefreshStarted: "✓ Refresh started", subRefreshAlreadyRunning: "Already refreshing…",
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

const QUICK_POOL = {
  zh: {
    flavors: ["清爽一点", "不太甜", "苦甜", "微酸", "花香", "草本", "烟熏", "低酒精", "烈一点", "适合餐前", "适合夜晚", "有气泡"],
    feelings: ["有点累", "很开心", "有点烦", "有点热", "有点冷", "有点焦虑", "很放松", "想庆祝", "没什么胃口", "想安静一点"],
    bases: ["琴酒", "威士忌", "朗姆", "伏特加", "龙舌兰", "接骨木花利口酒", "咖啡利口酒", "无酒精基底"],
    scenes: ["看电影", "晚饭后", "朋友来家里", "周末下午", "睡前小酌", "餐前开胃", "夏天晚上", "一个人安静喝"],
  },
  en: {
    flavors: ["fresh", "not too sweet", "bittersweet", "slightly sour", "floral", "herbal", "smoky", "low ABV", "strong", "aperitif-style", "nightcap-ish", "sparkling"],
    feelings: ["I'm tired", "I want to celebrate", "I want to relax", "I want something bright", "I want a ritual", "I want to sip slowly", "I don't want to get drunk", "I want something unusual", "it's hot today", "it's cold tonight"],
    bases: ["gin", "whisky", "rum", "vodka", "tequila", "elderflower liqueur", "coffee liqueur", "zero-proof"],
    scenes: ["movie night", "after dinner", "friends at home", "weekend afternoon", "a quiet nightcap", "before dinner", "a summer evening", "drinking alone quietly"],
  },
};

const QUICK_SENTENCE_TEMPLATES = {
  zh: [
    "给我来一杯{flavor}的",
    "今天{feeling}，有什么推荐",
    "用{base}给我做一杯",
    "适合{scene}的酒有什么",
    "我想喝一杯{flavor}的特调",
    "基于我的酒库，做一杯{flavor}的酒",
    "今天{feeling}，想喝点{flavor}的酒",
    "{scene}，来一杯什么好",
    "用{base}做一杯简单的酒",
    "给我一杯适合{scene}的特调",
  ],
  en: [
    "Make me something {flavor}",
    "{feeling}. What do you recommend?",
    "Build me a drink with {base}",
    "What works for {scene}?",
    "I want a {flavor} signature",
    "Use my cellar for something {flavor}",
    "{feeling}, something {flavor}",
    "What should I drink for {scene}?",
    "Make a simple {base} drink",
    "A signature for {scene}",
  ],
};

const RECENT_HISTORY_LIMIT = 10;

const CAT_ORDER = [
  "base_spirit", "fortified_wine", "wine", "bitter_liqueur", "liqueur", "bitters",
  "citrus", "citrus_juice", "juice", "sweetener", "mixer", "herb", "produce",
  "coffee", "texture", "garnish", "seasoning", "pantry",
];
const CAT_EN = {
  base_spirit: "Base spirit", fortified_wine: "Fortified wine", wine: "Wine",
  bitter_liqueur: "Bitter liqueur", liqueur: "Liqueur", bitters: "Bitters",
  citrus: "Citrus", citrus_juice: "Citrus juice", juice: "Juice",
  sweetener: "Sweetener", mixer: "Mixer", herb: "Herb", produce: "Produce",
  coffee: "Coffee", texture: "Texture", garnish: "Garnish",
  seasoning: "Seasoning", pantry: "Pantry",
};
const catEnLabel = (cat) => CAT_EN[cat] || cat;

const DELETE_ICON = '<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><path d="M3.8 3.8 L12.2 12.2 M12.2 3.8 L3.8 12.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>';

let confirmingBtn = null;

function resetDeleteBtn(btn) {
  if (!btn) return;
  btn.classList.remove("confirm");
  btn.innerHTML = DELETE_ICON;
  if (btn._delTimer) { clearTimeout(btn._delTimer); btn._delTimer = null; }
}

function setConfirmDelete(btn) {
  if (confirmingBtn && confirmingBtn !== btn) resetDeleteBtn(confirmingBtn);
  confirmingBtn = btn;
  btn.classList.add("confirm");
  btn.textContent = t("delete");
  btn._delTimer = setTimeout(() => {
    resetDeleteBtn(btn);
    if (confirmingBtn === btn) confirmingBtn = null;
  }, 5000);
}

/* ----------------------------- state ----------------------------------- */
const state = {
  lang: localStorage.getItem("cocktail.lang") || "zh",
  view: "recipes",
  filter: "all",
  availabilityFilter: "all",
  query: "",
  recipes: [],
  info: null,
  cellar: null,
  cellarQuery: "",
  cellarCategoryFilter: "all",
  settingsPane: "settings",
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
  document.body.dataset.view = state.view;
  applyLang();
  bindChrome();
  bindSettings();
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
  // recipe type filters
  $$("#filterChips .chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      $$("#filterChips .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.filter = chip.dataset.filter;
      renderGrid();
    })
  );
  // availability filters
  $$("#availabilityChips .chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      $$("#availabilityChips .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.availabilityFilter = chip.dataset.availability;
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
    if (e.key !== "Escape") return;
    if (!$("#settingsOverlay").hidden) closeSettings();
    else closeSheet();
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
  renderCellar();
  renderQuickPrompts();
  initChat(true);
}

/* ----------------------------- views ----------------------------------- */
function switchView(view) {
  state.view = view;
  document.body.dataset.view = view;
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
  if (state.availabilityFilter !== "all") {
    items = items.filter((r) => r.availability && r.availability.status === state.availabilityFilter);
  }
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
      const av = availabilityBadge(r.availability);
      const tags = (r.flavor || []).slice(0, 3).map((x) => `<span class="tag">${escapeHtml(x)}</span>`).join("");
      return `
      <article class="card" data-type="${r.type}" data-slug="${r.slug}">
        <div class="card-banner">
          <span class="card-emoji">${emoji}</span>
          <span class="card-type-pill">${escapeHtml(typeLabel)}</span>
        </div>
        <div class="card-body">
          ${av}
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

function availabilityBadge(av) {
  if (!av) return "";
  const label = t(av.status);
  return `<span class="availability-badge ${escapeHtml(av.status)}">${escapeHtml(label)}</span>`;
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
  const availability = renderAvailabilityPanel(r.availability);

  $("#sheetContent").innerHTML = `
    <div class="sheet-hero" style="background:linear-gradient(135deg, ${heroColors(r.type)})">
      <span class="sheet-type">${escapeHtml(typeLabel)}${r.source ? " · " + escapeHtml(r.source) : ""}</span>
      <h2 class="sheet-name">${escapeHtml(nameOf(r.name))}</h2>
      <p class="sheet-sub">${r.name.zh && r.name.en ? (state.lang === "zh" ? r.name.en : r.name.zh) : ""}</p>
      <div class="sheet-meta">${meta}</div>
      ${r.mood ? `<p class="sheet-mood">“${escapeHtml(r.mood)}”</p>` : ""}
    </div>
    <div class="sheet-body">
      ${availability}
      ${section("story", prose(r.story))}
      ${r.flavor_text ? section("flavor", `<div class="note-card">${inline(r.flavor_text)}</div>`) : ""}
      <div class="sheet-section">
        <h4 class="section-title">${t("ingredients")}</h4>
        <ul class="ing-list">${ings || '<li class="ing-row"><span class="ing-item">—</span></li>'}</ul>
      </div>
      ${steps ? `<div class="sheet-section"><h4 class="section-title">${t("steps")}</h4><ol class="steps">${steps}</ol></div>` : ""}
      ${r.notes ? section("notes", `<div class="note-card">${inline(r.notes)}</div>`) : ""}
      ${variants ? section("variants", `<ul class="variant-list">${variants}</ul>`) : ""}
      ${r.type === "signature" && r.slug
        ? `<div class="sheet-delete"><button class="btn danger" id="deleteSigBtn">${t("deleteSig")}</button></div>`
        : ""}
    </div>`;

  const delBtn = $("#deleteSigBtn");
  if (delBtn) {
    delBtn.addEventListener("click", () => deleteSignature(r.slug));
  }
}

function renderAvailabilityPanel(av) {
  if (!av) return "";
  const SRC = { manual: "subSourceManual", rule: "subSourceRule", llm: "subSourceLLM" };
  const CONF = { high: "confHigh", medium: "confMedium", low: "confLow" };
  const details = (av.details || []).map((d) => {
    let sub = "";
    if (d.status === "substitutable") {
      const tags = [];
      if (d.substitute_source && SRC[d.substitute_source]) tags.push(t(SRC[d.substitute_source]));
      if (d.substitute_confidence && CONF[d.substitute_confidence]) tags.push(t(CONF[d.substitute_confidence]));
      const tagHtml = tags.length
        ? " " + tags.map((s) => `<span class="sub-tag" style="font-size:.72em;padding:1px 6px;border-radius:8px;background:var(--bg-2);color:var(--text-2)">${escapeHtml(s)}</span>`).join("")
        : "";
      const bits = [];
      if (d.substitute_conditions) bits.push(`<b>${t("subConditions")}:</b> ${escapeHtml(d.substitute_conditions)}`);
      if (d.substitute_dosage) bits.push(`<b>${t("subDosage")}:</b> ${escapeHtml(d.substitute_dosage)}`);
      const extra = bits.length ? `<div class="availability-sub-detail" style="font-size:.82em;color:var(--text-2);margin-top:2px">${bits.join("<br>")}</div>` : "";
      const reason = d.substitute_reason ? `<div class="availability-sub-reason" style="font-size:.78em;color:var(--text-3);margin-top:2px">${escapeHtml(d.substitute_reason)}</div>` : "";
      sub = `<div class="availability-sub">${t("substitute")}: <b>${escapeHtml(d.substitute_name || "")}</b>${tagHtml}</div>${extra}${reason}`;
    }
    return `
      <li class="availability-row ${escapeHtml(d.status)}">
        <span>${availabilityIcon(d.status)}</span>
        <div>
          <strong>${escapeHtml(d.name || d.raw_item)}</strong>
          <em>${escapeHtml(d.amount || "")}${d.required ? "" : " · optional"}</em>
          ${sub}
        </div>
      </li>`;
  }).join("");
  return `
    <div class="availability-panel ${escapeHtml(av.status)}">
      <div class="availability-head">
        <span class="availability-badge ${escapeHtml(av.status)}">${escapeHtml(t(av.status))}</span>
        <strong>${escapeHtml(t("availability"))}</strong>
      </div>
      <p>${escapeHtml(av.summary || "")}</p>
      <ul>${details}</ul>
    </div>`;
}

function availabilityIcon(status) {
  return { available: "✓", substitutable: "~", missing: "!", unknown: "?" }[status] || "?";
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

async function deleteSignature(slug) {
  if (!confirm(t("deleteConfirm"))) return;
  try {
    await fetchJSON(`/api/cocktails/${encodeURIComponent(slug)}`, { method: "DELETE" });
    await loadRecipes();
    renderGrid();
    closeSheet();
    toast(t("deleted"));
  } catch (e) {
    toast("⚠️ " + e.message);
  }
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
  refreshChatBanner();
}

function refreshChatBanner() {
  const configured = state.info && state.info.llm_configured;
  const existing = $("#chatConfigBanner");
  if (configured) {
    if (existing) existing.remove();
    return;
  }
  let banner = existing;
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "chatConfigBanner";
    banner.className = "chat-banner";
    $(".chat-messages").prepend(banner);
  }
  banner.textContent = t("configWarn");
}

/* ----------------------------- settings -------------------------------- */
function bindSettings() {
  $("#settingsBtn").addEventListener("click", openSettings);
  $("#settingsClose").addEventListener("click", closeSettings);
  $("#settingsOverlay").addEventListener("click", (e) => {
    if (e.target.id === "settingsOverlay") closeSettings();
  });
  $("#saveCfgBtn").addEventListener("click", saveSettings);
  $("#testBtn").addEventListener("click", testLLM);
  $("#clearMemoryBtn").addEventListener("click", clearMemory);
  $("#addIngredientName").addEventListener("input", (e) => {
    state.cellarQuery = e.target.value.toLowerCase().trim();
    renderCellar();
  });
  $("#addIngredientCategory").addEventListener("change", (e) => {
    state.cellarCategoryFilter = e.target.value;
    renderCellar();
  });
  $("#addIngredientBtn").addEventListener("click", addIngredient);
  $("#addIngredientName").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addIngredient();
    }
  });
  $$(".settings-nav-btn").forEach((btn) =>
    btn.addEventListener("click", () => switchSettingsPane(btn.dataset.pane))
  );
  $("#refreshSubsBtn").addEventListener("click", refreshSubs);
  document.addEventListener("click", () => {
    if (confirmingBtn) { resetDeleteBtn(confirmingBtn); confirmingBtn = null; }
  });
}

async function openSettings() {
  switchSettingsPane("settings");
  $("#settingsOverlay").hidden = false;
  document.body.style.overflow = "hidden";
  $("#testResult").hidden = true;
  $("#cfgApiKey").value = "";
  try {
    const cfg = await fetchJSON("/api/llm/config");
    $("#cfgBaseUrl").value = cfg.base_url || "";
    $("#cfgModel").value = cfg.model || "";
    updateKeyHint(cfg.has_key, cfg.key_hint);
  } catch (e) {
    /* ignore — fields stay editable */
  }
  loadMemoryPreview();
  loadCellar();
}

async function loadMemoryPreview() {
  try {
    const m = await fetchJSON("/api/memory");
    const el = $("#memoryPreview");
    const text = (m.rolling || "").trim();
    el.textContent = text || (state.lang === "zh" ? "（暂无记忆）" : "(no memory yet)");
  } catch (e) {
    /* ignore */
  }
}

async function clearMemory() {
  if (!confirm(t("clearMemoryConfirm"))) return;
  const btn = $("#clearMemoryBtn");
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "…";
  try {
    await fetchJSON("/api/memory/clear", { method: "POST" });
    await loadMemoryPreview();
    toast(t("memoryCleared"));
  } catch (e) {
    toast("⚠️ " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
}

async function loadCellar() {
  try {
    state.cellar = await fetchJSON("/api/cellar");
    renderCellar();
  } catch (e) {
    $("#cellarList").innerHTML = `<div class="settings-hint">⚠️ ${escapeHtml(e.message)}</div>`;
  }
}

function renderCellar() {
  const list = $("#cellarList");
  if (!state.cellar || !list) return;
  const q = state.cellarQuery;
  const cat = state.cellarCategoryFilter || "all";
  const items = (state.cellar.items || []).filter((item) => {
    if (item.category === "pantry") return false; // 冰块/水默认可用,不在酒柜管理
    const matchQ = !q || [item.zh, item.en, item.category, item.id].join(" ").toLowerCase().includes(q);
    const matchCat = cat === "all" || item.category === cat;
    return matchQ && matchCat;
  });
  renderMatrixStatus(state.cellar.matrix_status);
  if (!items.length) {
    list.innerHTML = `<div class="settings-hint">${t("noResults")}</div>`;
    return;
  }
  const groups = {};
  for (const it of items) (groups[it.category] ||= []).push(it);
  const orderedCats = [...CAT_ORDER, ...Object.keys(groups).filter((c) => !CAT_ORDER.includes(c))];
  let html = "";
  for (const c of orderedCats) {
    if (!groups[c]) continue;
    html += `<div class="cellar-group"><div class="cellar-group-head"><span>${escapeHtml(catEnLabel(c))}</span></div>`;
    html += groups[c].map(renderCellarItem).join("");
    html += `</div>`;
  }
  list.innerHTML = html;
  $$(".cellar-status button", list).forEach((btn) =>
    btn.addEventListener("click", () => updateInventory(btn.closest(".cellar-item").dataset.id, btn.dataset.status))
  );
  $$(".cellar-delete", list).forEach((btn) =>
    btn.addEventListener("click", (ev) => onDeleteClick(btn, ev))
  );
}

function renderCellarItem(item) {
  const line2 = [item.en, item.note].filter(Boolean).join(" · ");
  const meta = line2
    ? `${escapeHtml(line2)}, ${escapeHtml(catEnLabel(item.category))}`
    : escapeHtml(catEnLabel(item.category));
  return `
    <div class="cellar-item" data-id="${escapeHtml(item.id)}">
      <button class="cellar-delete" type="button" aria-label="${t("delete")}">${DELETE_ICON}</button>
      <div class="cellar-main">
        <strong>${escapeHtml(item.zh || item.en || item.id)}</strong>
        <span>${meta}</span>
      </div>
      <div class="cellar-status" role="group" aria-label="${escapeHtml(item.zh || item.en || item.id)}">
        ${cellarStatusButton(item, "in_stock", t("inStock"))}
        ${cellarStatusButton(item, "low", t("lowStock"))}
        ${cellarStatusButton(item, "missing", t("missingStock"))}
        ${cellarStatusButton(item, "ignored", t("ignoredStock"))}
      </div>
    </div>`;
}

function onDeleteClick(btn, ev) {
  // Stop propagation: the click must NOT reach the document handler (which
  // resets the confirming button). We can't rely on e.target.closest there
  // because toggling the button's content detaches the SVG <path> that was
  // clicked, breaking ancestor lookup.
  ev.stopPropagation();
  if (btn === confirmingBtn) {
    const id = btn.closest(".cellar-item").dataset.id;
    confirmingBtn = null;
    resetDeleteBtn(btn);
    deleteIngredient(id);
  } else {
    setConfirmDelete(btn);
  }
}

async function deleteIngredient(id) {
  try {
    await fetchJSON(`/api/cellar/ingredients/${encodeURIComponent(id)}`, { method: "DELETE" });
    state.cellar = await fetchJSON("/api/cellar");
    await loadRecipes();
    renderGrid();
    renderCellar();
    toast(t("ingredientDeleted"));
  } catch (e) {
    toast("⚠️ " + e.message);
  }
}

function renderMatrixStatus(ms) {
  const el = $("#cellarMatrixStatus");
  if (!el) return;
  if (!ms) { el.innerHTML = ""; return; }
  let label;
  if (ms.state === "refreshing") label = t("subMatrixRefreshing");
  else if (ms.state === "ready") label = `${t("subMatrixReady")} · ${ms.pairs}${ms.dirty ? " · 待更新" : ""}`;
  else label = t("subMatrixStale");
  const color = ms.state === "ready" ? (ms.dirty ? "#f0a020" : "var(--accent)") : ms.state === "refreshing" ? "#f0a020" : "var(--text-3)";
  el.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-3)"><span style="width:7px;height:7px;border-radius:50%;background:${color}"></span>${escapeHtml(label)}</span>`;
}

function switchSettingsPane(pane) {
  state.settingsPane = pane;
  $$(".settings-nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.pane === pane));
  $$(".pane").forEach((p) => { p.hidden = p.dataset.pane !== pane; });
  const title = $("#settingsTitle");
  if (title) title.textContent = t(pane === "cellar" ? "cellarTitle" : "settings");
  if (pane === "cellar") loadCellar();
}

async function refreshSubs() {
  const btn = $("#refreshSubsBtn");
  if (!btn || btn.disabled) return;
  const orig = btn.textContent;
  btn.disabled = true; btn.textContent = "…";
  try {
    const r = await fetchJSON("/api/cellar/refresh", { method: "POST" });
    if (!r.started) { toast(t("subRefreshAlreadyRunning")); }
    else { toast(t("subRefreshStarted")); pollMatrixStatus(); }
  } catch (e) { toast("⚠️ " + e.message); }
  finally { btn.disabled = false; btn.textContent = orig; }
}

function pollMatrixStatus() {
  let n = 0;
  const timer = setInterval(async () => {
    n += 1;
    try {
      state.cellar = await fetchJSON("/api/cellar");
      renderMatrixStatus(state.cellar.matrix_status);
    } catch (e) { /* ignore */ }
    const ms = state.cellar && state.cellar.matrix_status;
    if ((ms && ms.state !== "refreshing") || n > 60) clearInterval(timer);
  }, 2000);
}

function cellarStatusButton(item, status, label) {
  return `<button class="${item.status === status ? "active" : ""}" data-status="${status}">${escapeHtml(label)}</button>`;
}

async function updateInventory(ingredientId, status) {
  try {
    state.cellar = await fetchJSON("/api/cellar/inventory", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ingredient_id: ingredientId, status }),
    });
    await loadRecipes();
    renderGrid();
    renderCellar();
    toast(t("cellarSaved"));
  } catch (e) {
    toast("⚠️ " + e.message);
  }
}

async function addIngredient() {
  const input = $("#addIngredientName");
  const btn = $("#addIngredientBtn");
  const name = input.value.trim();
  if (!name) return;
  const sel = $("#addIngredientCategory").value;
  const category = sel && sel !== "all" ? sel : "liqueur";
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "…";
  try {
    state.cellar = await fetchJSON("/api/cellar/ingredients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, category, status: "in_stock" }),
    });
    input.value = "";
    state.cellarQuery = "";
    state.cellarCategoryFilter = "all";
    $("#addIngredientCategory").value = "all";
    await loadRecipes();
    renderGrid();
    renderCellar();
    toast(t("ingredientAdded"));
  } catch (e) {
    toast("⚠️ " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

function updateKeyHint(hasKey, hint) {
  const ph = $("#cfgApiKey");
  const hintEl = $("#cfgKeyHint");
  if (hasKey) {
    ph.placeholder = t("keySet");
    hintEl.textContent = `${state.lang === "zh" ? "当前密钥" : "Current key"}: ${hint}`;
  } else {
    ph.placeholder = "sk-...";
    hintEl.textContent = t("keyEmpty");
  }
}

function closeSettings() {
  $("#settingsOverlay").hidden = true;
  if ($("#sheetOverlay").hidden) document.body.style.overflow = "";
}

async function saveSettings() {
  const body = {
    base_url: $("#cfgBaseUrl").value.trim() || null,
    model: $("#cfgModel").value.trim() || null,
    api_key: $("#cfgApiKey").value || null, // empty keeps the existing key
  };
  const btn = $("#saveCfgBtn");
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "…";
  try {
    const r = await fetchJSON("/api/llm/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (state.info) state.info.llm_configured = r.has_key;
    $("#cfgApiKey").value = "";
    updateKeyHint(r.has_key, r.key_hint);
    refreshChatBanner();
    toast(t("cfgSaved"));
  } catch (e) {
    toast("⚠️ " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
}

async function testLLM() {
  const result = $("#testResult");
  const btn = $("#testBtn");
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = t("testing");
  result.hidden = false;
  result.className = "test-result";
  result.textContent = t("testing");
  try {
    const r = await fetchJSON("/api/llm/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_url: $("#cfgBaseUrl").value.trim() || null,
        api_key: $("#cfgApiKey").value || null,
        model: $("#cfgModel").value.trim() || null,
      }),
    });
    if (r.ok) {
      result.className = "test-result ok";
      result.textContent =
        `${t("testOk")} · ${r.model} · ${r.latency_ms}ms` + (r.reply ? ` · "${r.reply}"` : "");
    } else {
      result.className = "test-result err";
      result.textContent = `${t("testFail")}: ${r.error || ""}` + (r.latency_ms ? ` (${r.latency_ms}ms)` : "");
    }
  } catch (e) {
    result.className = "test-result err";
    result.textContent = `${t("testFail")}: ${e.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
}

function renderQuickPrompts() {
  const prompts = assistantOptionPrompts();
  const choices = prompts.length ? prompts : randomQuickPrompts();
  $("#quickPrompts").innerHTML = choices
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

function assistantOptionPrompts() {
  const last = [...state.chat].reverse().find((m) => m.role === "bartender" && m.text && !isWelcomeMessage(m));
  if (!last) return [];
  const lines = stripJsonForDisplay(last.text).split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
  const out = [];
  for (const line of lines) {
    const m = line.match(/^(?:[-*•]|\d+[.)]|[A-Da-d][.)]|方向[一二三四四五六七八]?[:：]?)\s*(.+)$/);
    if (!m) continue;
    const short = shortenOption(m[1]);
    if (short && !out.includes(short)) out.push(short);
  }
  return out.length >= 2 ? out.slice(0, 4) : [];
}

function shortenOption(text) {
  let s = String(text || "")
    .replace(/\*\*/g, "")
    .replace(/^["“'‘]|["”'’]$/g, "")
    .trim();
  s = s.split(/[，,。.!！?？；;：:(（]/)[0].trim();
  s = s.replace(/^(选|要|来点|来杯|一杯)/, "").trim();
  const chars = Array.from(s);
  if (!s || chars.length > 8) return "";
  return s;
}

function randomQuickPrompts() {
  const data = QUICK_POOL[state.lang];
  const templates = QUICK_SENTENCE_TEMPLATES[state.lang];
  const pool = [];
  for (const tmpl of templates) {
    const keys = [...tmpl.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);
    if (!keys.length) continue;
    const primary = keys[0];
    const values = data[primary + "s"] || data[primary] || [];
    for (const value of values) {
      pool.push(fillQuickTemplate(tmpl, primary, value, data));
    }
  }
  const shuffled = [...new Set(pool)].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 4);
}

function fillQuickTemplate(tmpl, primaryKey, primaryValue, data) {
  return tmpl.replace(/\{(\w+)\}/g, (_, key) => {
    if (key === primaryKey) return primaryValue;
    const values = data[key + "s"] || data[key] || [""];
    return values[Math.floor(Math.random() * values.length)] || "";
  });
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
  const prose = compactChatText(stripJson(m.text));
  wrap.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">
      ${prose ? `<span class="chat-prose">${escapeHtml(prose)}</span>` : ""}
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

  const payload = buildChatPayload();

  let acc = "";
  await streamChat(
    payload,
    (delta) => {
      acc += delta;
      const prose = compactChatText(stripJsonForDisplay(acc));
      updateStreamingBubble(phWrap, prose, hasJsonBlock(acc));
      scrollChatToBottom();
    },
    () => {
      // finalize
      const recipe = extractRecipe(acc);
      const bubble = $(".msg-bubble", phWrap);
      updateStreamingBubble(phWrap, compactChatText(stripJson(acc)), false);
      if (recipe) bubble.appendChild(buildRecipeCard(recipe));
      // record into history
      const msg = { role: "bartender", text: acc, recipe: recipe || undefined };
      state.chat.push(msg);
      state.streaming = false;
      setSendDisabled(false);
      renderQuickPrompts();
      scrollChatToBottom();
    },
    (err) => {
      const bubble = $(".msg-bubble", phWrap);
      bubble.innerHTML = `<span class="chat-prose" style="color:#c0392b">⚠️ ${escapeHtml(t("chatError"))}: ${escapeHtml(err.message)}</span>`;
      state.chat.push({ role: "bartender", text: `⚠️ ${t("chatError")}: ${err.message}` });
      state.streaming = false;
      setSendDisabled(false);
      renderQuickPrompts();
    }
  );
}

function buildChatPayload() {
  const entries = state.chat
    .filter((m) => m.text && !m._placeholder && !isWelcomeMessage(m))
    .map((m) => ({
      role: m.role === "bartender" ? "assistant" : "user",
      content: compactChatText(stripJson(m.text)),
    }))
    .filter((m) => (m.role === "user" || m.role === "assistant") && m.content);
  const recent = entries.slice(-RECENT_HISTORY_LIMIT);
  const older = entries.slice(0, -RECENT_HISTORY_LIMIT);
  return {
    messages: recent,
    context_summary: summarizeOlderContext(older),
  };
}

function summarizeOlderContext(older) {
  if (!older.length) return "";
  const userBits = older
    .filter((m) => m.role === "user")
    .slice(-5)
    .map((m) => truncateText(m.content, 80));
  const assistantBits = older
    .filter((m) => m.role === "assistant")
    .slice(-3)
    .map((m) => truncateText(m.content, 80));
  const parts = [];
  if (userBits.length) parts.push(`较早的客人表达：${userBits.join("；")}`);
  if (assistantBits.length) parts.push(`已聊过的方向：${assistantBits.join("；")}`);
  return parts.join("\n");
}

function truncateText(text, max) {
  const chars = Array.from(String(text || "").replace(/\s+/g, " ").trim());
  return chars.length > max ? chars.slice(0, max).join("") + "…" : chars.join("");
}

function isWelcomeMessage(m) {
  const text = m.text || "";
  return m.role === "bartender" && (text.includes("我是你的调酒师") || text.includes("I'm your bartender"));
}

function updateStreamingBubble(wrap, prose, generating) {
  const bubble = $(".msg-bubble", wrap);
  let textEl = $(".chat-prose", bubble);
  if (!textEl) {
    bubble.innerHTML = "";
    textEl = document.createElement("span");
    textEl.className = "chat-prose";
    bubble.appendChild(textEl);
  }
  textEl.textContent = prose || "";
  let preparing = $(".preparing", bubble);
  if (generating && !preparing) {
    preparing = document.createElement("span");
    preparing.className = "preparing";
    preparing.textContent = t("preparing");
    bubble.appendChild(preparing);
  } else if (!generating && preparing) {
    preparing.remove();
  }
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
async function streamChat(payload, onDelta, onDone, onError) {
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
  const candidates = [];
  const fenceRe = /```(?:json)?\s*([\s\S]*?)```/gi;
  let m;
  while ((m = fenceRe.exec(text || "")) !== null) {
    const block = m[1].trim();
    if (block.startsWith("{")) candidates.push(block);
  }
  const rawStart = findRecipePayloadStart(text);
  if (rawStart >= 0) {
    const raw = balancedJsonSlice((text || "").slice(rawStart));
    if (raw) candidates.push(raw);
  }
  for (const raw of candidates.reverse()) {
    try {
      const data = JSON.parse(raw);
      if (data && (data.ingredients || data.steps)) return data;
    } catch (e) {}
  }
  return null;
}

function stripJson(text) {
  text = text || "";
  return text
    .replace(/```(?:json)?\s*\{[\s\S]*?\}\s*```/gi, "")
    .replace(rawRecipeJsonRe(), "")
    .trim();
}

function stripJsonForDisplay(text) {
  text = text || "";
  const start = findRecipePayloadStart(text);
  if (start >= 0) return stripJson(text.slice(0, start)).trim();
  return stripJson(text).trim();
}

function compactChatText(text) {
  return String(text || "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter((line, idx, arr) => line || (idx > 0 && arr[idx - 1]))
    .join("\n")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

function hasJsonBlock(text) {
  return findRecipePayloadStart(text) >= 0;
}

function findRecipePayloadStart(text) {
  text = text || "";
  const fenced = text.search(/```(?:json)?\s*[\r\n]*\{/i);
  const raw = text.search(/(^|\n)\s*\{\s*["']name["']\s*:/i);
  const starts = [fenced, raw].filter((x) => x >= 0);
  return starts.length ? Math.min(...starts) : -1;
}

function balancedJsonSlice(text) {
  const start = (text || "").indexOf("{");
  if (start < 0) return "";
  let depth = 0;
  let inString = false;
  let quote = "";
  let escaped = false;
  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === quote) inString = false;
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      continue;
    }
    if (ch === "{") depth += 1;
    if (ch === "}") {
      depth -= 1;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return "";
}

function rawRecipeJsonRe() {
  return /(^|\n)\s*\{\s*["']name["'][\s\S]*?\}\s*$/i;
}

function buildRecipeCard(r) {
  const name = r.name && (r.name[state.lang] || r.name.en || r.name.zh)
    ? r.name : { zh: "", en: typeof r.name === "string" ? r.name : "" };
  const dispName = typeof r.name === "string" ? r.name : nameOf(r.name);
  const ings = (r.ingredients || [])
    .map((i) => `<div><b style="color:var(--accent)">${escapeHtml(i.amount || "")}</b> ${escapeHtml(i.item || "")}</div>`)
    .join("");
  const stepsPreview = (r.steps || []).slice(0, 2)
    .map((s) => `<li>${escapeHtml(String(s).replace(/^\s*\d+[.)]\s*/, ""))}</li>`)
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
      <div class="rcm-body">
        ${r.story ? `<div class="rcm-story">${escapeHtml(r.story)}</div>` : ""}
        <div class="rcm-ing">${ings}</div>
        ${stepsPreview ? `<ol class="rcm-steps">${stepsPreview}</ol>` : ""}
      </div>
      <div class="rcm-actions">
        <button class="btn ghost detail-btn">${t("viewDetails")}</button>
        <button class="btn save-btn">${t("save")}</button>
      </div>
    </div>`;
  $(".detail-btn", card).addEventListener("click", () => openGeneratedRecipe(r));
  $(".save-btn", card).addEventListener("click", () => saveRecipe(r, card));
  return card;
}

function openGeneratedRecipe(r) {
  $("#sheetOverlay").hidden = false;
  document.body.style.overflow = "hidden";
  renderSheet(recipeFromGenerated(r));
}

function recipeFromGenerated(r) {
  const name = typeof r.name === "string" ? { zh: "", en: r.name } : { zh: r.name?.zh || "", en: r.name?.en || "" };
  return {
    slug: "",
    name,
    type: "signature",
    source: "generated",
    base: r.base || "",
    glass: r.glass || "",
    garnish: r.garnish || "",
    abv: r.abv || "",
    difficulty: "medium",
    flavor: Array.isArray(r.tags) ? r.tags : [],
    tags: Array.isArray(r.tags) ? r.tags : [],
    story: r.story || "",
    flavor_text: typeof r.flavor === "string" ? r.flavor : "",
    mood: r.mood || "",
    ingredients: r.ingredients || [],
    steps: (r.steps || []).map((s) => String(s).replace(/^\s*\d+[.)]\s*/, "")),
    notes: r.bartender_notes || r.notes || "",
    variants: parseVariants(r.variants),
    body_markdown: "",
  };
}

function parseVariants(value) {
  if (Array.isArray(value)) return value.map(String);
  return String(value || "")
    .split(/\r?\n/)
    .map((v) => v.replace(/^\s*[-*•]\s*/, "").trim())
    .filter(Boolean);
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
      conversation: state.chat.slice(-20).map((m) => ({ role: m.role, content: stripJson(m.text) })),
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
