"""Smart substitution engine — two-tier ingredient substitution.

Tier A (rule-based, realtime, free): scores every ingredient pair from a
hand-authored flavor/function/physical profile, with absolute exclusions
encoding bartender hard rules (a base spirit can't be replaced by a juice,
etc.). Computed on every ``evaluate``; never persisted.

Tier B (LLM, cached): for pairs Tier A finds promising, an LLM judges
yes|conditional|no plus conditions / dosage / reason. Results are cached in
a matrix keyed by ingredient pair — *independent of current stock* — and
refreshed in the background **only when the ingredient/substitution/profile
data changes** (never on inventory-only reloads, never re-computing cached
pairs).

The query path (``find_smart_substitution``) merges the two: Tier-B cache
wins (and a cached ``no`` is a negative cache blocking Tier-A); without a
cached verdict, Tier-A's realtime score decides.

No new dependencies: cosine is hand-written; the LLM is the only external
service (project constraint).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import llm
from .config import settings

# --------------------------------------------------------------------------- #
# Paths & constants
# --------------------------------------------------------------------------- #
CELLAR_DIR = settings.data_dir / "cellar"
ING_FILE = CELLAR_DIR / "ingredients.yml"
SUB_FILE = CELLAR_DIR / "substitutions.yml"
PROFILES_FILE = CELLAR_DIR / "ingredient_profiles.yml"
MATRIX_FILE = CELLAR_DIR / "substitution_matrix.json"

FLAVOR_AXES = (
    "sweet", "sour", "bitter", "citrus", "fruity", "floral",
    "herbal", "spicy", "nutty", "coffee", "smoky", "vanilla", "caramel",
)
FUNCTIONS = (
    "sweetener", "flavoring", "acid", "base", "dilution",
    "bitter", "texture", "aromatic",
)

# Categories that never participate in substitution (decorative / incidental).
_NON_SUBSTITUTE_CATEGORIES = {"garnish", "pantry", "seasoning", "herb", "texture"}

# Structural categories may only be substituted within their whitelist —
# this is the "bartender hard rule" layer (a spirit stays a spirit, an acid
# stays an acid), no matter how similar the flavor.
_CATEGORY_WHITELIST: dict[str, set[str]] = {
    "base_spirit": {"base_spirit", "fortified_wine"},
    "citrus_juice": {"citrus_juice", "citrus"},
    "bitters": {"bitters"},
    "wine": {"wine", "fortified_wine"},
    "fortified_wine": {"fortified_wine", "wine"},
}

# Tier-A thresholds.
_RULE_CANDIDATE = 0.60   # min score to send a pair to Tier-B LLM judging
_RULE_STRONG = 0.75      # confident enough to propose pre-LLM (same family+function)
_RULE_PROPOSE = 0.55     # min score to propose at all in degraded (no-LLM) mode

_BATCH_SIZE = 12  # pairs per judge call (each call stays well under the LLM timeout)
_INFER_BATCH = 8  # profiles per infer call (keeps output well under token limits)
_CONCURRENCY = 2  # mild parallelism — balances speed against provider rate limits


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #
@dataclass
class IngredientProfile:
    ingredient_id: str
    family: str = ""
    flavor: dict[str, int] = field(default_factory=dict)
    function: set[str] = field(default_factory=set)
    abv: float = 0.0
    intensity: float = 1.0
    source: str = "manual"  # manual | llm

    def flavor_vec(self) -> list[float]:
        return [float(self.flavor.get(ax, 0)) for ax in FLAVOR_AXES]


@dataclass
class SmartSub:
    """A resolved smart substitution for one missing ingredient."""
    missing: str
    substitute: str
    confidence: str = "medium"       # high | medium | low
    impact: str = ""
    conditions: str = ""
    dosage_note: str = ""
    reason: str = ""
    source: str = "rule"             # rule | llm


# --------------------------------------------------------------------------- #
# Pure helpers (no state)
# --------------------------------------------------------------------------- #
def flavor_cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _category_compatible(missing_cat: str, sub_cat: str) -> bool:
    if missing_cat in _NON_SUBSTITUTE_CATEGORIES or sub_cat in _NON_SUBSTITUTE_CATEGORIES:
        return False
    allowed = _CATEGORY_WHITELIST.get(missing_cat)
    if allowed:
        return sub_cat in allowed
    return True


def rule_score(missing: IngredientProfile, sub: IngredientProfile,
               missing_cat: str, sub_cat: str) -> float:
    """0.0–1.0 similarity for using ``sub`` in place of ``missing``."""
    if not _category_compatible(missing_cat, sub_cat):
        return 0.0
    fam = 1.0 if (missing.family and missing.family == sub.family) else 0.0
    cos = flavor_cosine(missing.flavor_vec(), sub.flavor_vec())
    if missing.function or sub.function:
        union = missing.function | sub.function
        inter = missing.function & sub.function
        func = len(inter) / len(union) if union else 0.0
    else:
        func = 0.0
    score = 0.40 * fam + 0.30 * cos + 0.20 * func + 0.10  # category base 1.0 (passed)
    # Same family but very different physical profile (e.g. liqueur ↔ juice)
    # is the classic false-positive; dampen it so the LLM gets the final word.
    if missing.family and missing.family == sub.family:
        abv_gap = abs(missing.abv - sub.abv) / 60.0
        inten_gap = abs(missing.intensity - sub.intensity) / 2.0
        score -= max(0.0, abv_gap * 0.15 + inten_gap * 0.15)
    return max(0.0, score)


# --------------------------------------------------------------------------- #
# Atomic IO
# --------------------------------------------------------------------------- #
def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


def _fingerprint() -> str:
    """Hash of the *source* data that the matrix depends on.

    Deliberately excludes ``inventory.yml`` (stock changes must not trigger a
    refresh) and the product files themselves (matrix / profiles), so a
    refresh never re-triggers itself: products only change as a consequence
    of a source change, and one refresh run writes them atomically.
    """
    h = hashlib.sha1()
    for path in (ING_FILE, SUB_FILE, PROFILES_FILE):
        try:
            h.update(path.read_bytes())
        except OSError:
            h.update(b"")
    return h.hexdigest()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _profile_from_row(row: dict, source: str = "manual") -> IngredientProfile | None:
    if not isinstance(row, dict) or not row.get("id"):
        return None
    flavor = {str(k): int(v) for k, v in (row.get("flavor") or {}).items()
              if isinstance(v, (int, float))}
    function = {str(f) for f in (row.get("function") or []) if str(f) in FUNCTIONS}
    return IngredientProfile(
        ingredient_id=str(row["id"]).strip(),
        family=str(row.get("family") or "").strip(),
        flavor=flavor,
        function=function,
        abv=float(row.get("abv") or 0.0),
        intensity=float(row.get("intensity") or 1.0) or 1.0,
        source=str(row.get("source") or source).strip(),
    )


# --------------------------------------------------------------------------- #
# Engine (module-level singleton, mirroring kb / cellar)
# --------------------------------------------------------------------------- #
class SubEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._refreshing = False
        self._active_fingerprint = ""
        self._pending_fingerprint = ""
        self._cached_fingerprint = ""
        self.profiles: dict[str, IngredientProfile] = {}
        self.matrix: dict[str, dict[str, dict]] = {}
        self._load_profiles()
        self._load_matrix()

    # ---- loading ------------------------------------------------------- #
    def _load_profiles(self) -> None:
        self.profiles = {}
        if not PROFILES_FILE.exists():
            return
        data = yaml.safe_load(PROFILES_FILE.read_text(encoding="utf-8")) or {}
        rows = data.get("profiles", []) if isinstance(data, dict) else []
        for row in rows:
            prof = _profile_from_row(row)
            if prof:
                self.profiles[prof.ingredient_id] = prof

    def _load_matrix(self) -> None:
        data = _read_json(MATRIX_FILE, {"fingerprint": "", "matrix": {}})
        if isinstance(data, dict):
            self.matrix = data.get("matrix", {}) if isinstance(data.get("matrix"), dict) else {}
            self._cached_fingerprint = str(data.get("fingerprint", ""))

    # ---- query --------------------------------------------------------- #
    def _resolve(self, missing_id: str, cand: str, cellar) -> tuple[int, float, SmartSub] | None:
        """Resolve one (missing, candidate) pair to a ranked substitution, or None.

        Returns (rank, score, SmartSub) where lower rank is better; score is
        the Tier-A rule score used only as a tiebreaker.
        """
        mprof = self.profiles.get(missing_id)
        cprof = self.profiles.get(cand)
        if not mprof or not cprof:
            return None
        if missing_id not in cellar.ingredients or cand not in cellar.ingredients:
            return None
        mcat = cellar.ingredients[missing_id].category
        ccat = cellar.ingredients[cand].category

        tb = self.matrix.get(missing_id, {}).get(cand)
        if tb is not None:
            verdict = str(tb.get("verdict", "")).lower()
            conf = str(tb.get("confidence", "medium")).lower() or "medium"
            if verdict == "no":
                return None  # negative cache — Tier-A won't re-propose this
            if verdict == "yes":
                rank = 0 if conf == "high" else 3
            elif verdict == "conditional":
                rank = 1 if conf in ("high", "medium") else 5
            else:
                return None
            return rank, 0.0, SmartSub(
                missing=missing_id, substitute=cand, confidence=conf,
                impact=tb.get("conditions", "") or "",
                conditions=tb.get("conditions", "") or "",
                dosage_note=tb.get("dosage_note", "") or "",
                reason=tb.get("reason", "") or "",
                source="llm",
            )

        # Tier-A realtime
        score = rule_score(mprof, cprof, mcat, ccat)
        if settings.llm_configured:
            if score < _RULE_STRONG:
                return None  # weak match — wait for the LLM to judge
            return 2, score, SmartSub(
                missing=missing_id, substitute=cand, confidence="medium",
                reason=f"风味与功能相近（规则匹配 {score:.2f}）", source="rule",
            )
        # degraded mode (no LLM): propose on weaker matches too
        if score < _RULE_PROPOSE:
            return None
        rank = 2 if score >= _RULE_STRONG else 4
        conf = "medium" if score >= _RULE_STRONG else "low"
        return rank, score, SmartSub(
            missing=missing_id, substitute=cand, confidence=conf,
            reason=f"风味与功能相近（规则匹配 {score:.2f}）", source="rule",
        )

    def find_smart_substitution(self, missing_ids: list[str], cellar) -> SmartSub | None:
        """Best in-stock substitute across all missing ids, or None."""
        candidates = [iid for iid in cellar.ingredients if cellar.is_available(iid)]
        best_key: tuple[int, float] | None = None
        best_sub: SmartSub | None = None
        for mid in missing_ids:
            for cand in candidates:
                if cand == mid:
                    continue
                r = self._resolve(mid, cand, cellar)
                if r is None:
                    continue
                rank, score, sub = r
                key = (rank, -score)
                if best_key is None or key < best_key:
                    best_key = key
                    best_sub = sub
        return best_sub

    # ---- status -------------------------------------------------------- #
    def status(self) -> dict:
        if self._refreshing:
            state = "refreshing"
        elif self._cached_fingerprint:
            state = "ready"
        else:
            state = "stale"
        return {
            "state": state,
            "fingerprint": self._cached_fingerprint[:8],
            "pairs": sum(len(v) for v in self.matrix.values()),
            "llm_configured": settings.llm_configured,
        }

    # ---- background refresh -------------------------------------------- #
    def maybe_refresh(self, cellar) -> None:
        """Non-blocking. Spawns a daemon thread only if the data fingerprint
        changed since the last successful refresh."""
        fp = _fingerprint()
        with self._lock:
            if self._refreshing:
                # a refresh is running; queue a rerun only if data changed again
                if fp != self._active_fingerprint:
                    self._pending_fingerprint = fp
                return
            if fp == self._cached_fingerprint:
                return  # inventory-only reload, or no change
            self._refreshing = True
            self._active_fingerprint = fp
        snapshot = _cellar_snapshot(cellar)
        threading.Thread(
            target=self._refresh_worker, args=(snapshot,), daemon=True
        ).start()

    def _refresh_worker(self, snapshot: dict) -> None:
        try:
            asyncio.run(self._refresh_async(snapshot))
        except Exception:  # noqa: BLE001 — background, never raise into caller
            pass
        finally:
            rerun = ""
            with self._lock:
                self._refreshing = False
                if (self._pending_fingerprint
                        and self._pending_fingerprint != self._cached_fingerprint):
                    rerun = self._pending_fingerprint
                    self._pending_fingerprint = ""
            if rerun:
                from . import cellar as _cellar_mod  # local import; module is loaded by now
                self.maybe_refresh(_cellar_mod.cellar)

    async def _refresh_async(self, snapshot: dict) -> None:
        if not settings.llm_configured:
            return  # Tier-A handles the query path without an LLM
        from openai import AsyncOpenAI
        # A private client bound to *this* thread's event loop. The global
        # ``llm._client`` is bound to the uvicorn loop, so reusing it from the
        # background thread would cross loops; create and close one here.
        cli = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key or "not-configured",
            timeout=90.0,
        )
        refresh_model = settings.llm_refresh_model or settings.llm_model
        try:
            live = set(snapshot["ingredients"])

            # 1. infer profiles for any substitutable ingredient lacking one
            #    (skip garnish/pantry/seasoning etc. — they never substitute).
            #    Batched + parallel so no single call's JSON output gets truncated.
            todo_profiles = [
                i for i in live
                if i not in self.profiles
                and snapshot["ingredients"][i]["category"] not in _NON_SUBSTITUTE_CATEGORIES
            ]
            if todo_profiles:
                items = [{"id": i, **snapshot["ingredients"][i]} for i in todo_profiles]
                infer_batches = [items[i:i + _INFER_BATCH] for i in range(0, len(items), _INFER_BATCH)]
                sem_inf = asyncio.Semaphore(_CONCURRENCY)

                async def _infer_batch(batch):
                    async with sem_inf:
                        for attempt in range(3):
                            try:
                                return await llm.infer_profiles(batch, cli, model=refresh_model)
                            except Exception:
                                if attempt < 2:
                                    await asyncio.sleep(3 * (attempt + 1))
                                else:
                                    return []
                        return []

                for res in await asyncio.gather(
                    *(_infer_batch(b) for b in infer_batches), return_exceptions=True
                ):
                    if not isinstance(res, Exception):
                        self._merge_profiles(res)

            # 2. the set of pairs Tier-A thinks are worth judging
            needed = self._needed_pairs(snapshot)

            # 3. start from the live subset of the existing matrix (prune removed)
            new_matrix: dict[str, dict[str, dict]] = {}
            for a, subs in self.matrix.items():
                if a not in live:
                    continue
                kept = {b: v for b, v in subs.items() if b in live}
                if kept:
                    new_matrix[a] = kept

            # 4. incremental: judge only pairs not already cached, in parallel
            cached = {(a, b) for a, subs in new_matrix.items() for b in subs}
            todo = [pair for pair in needed if pair not in cached]
            batches = [todo[i:i + _BATCH_SIZE] for i in range(0, len(todo), _BATCH_SIZE)]
            sem = asyncio.Semaphore(_CONCURRENCY)

            async def _judge_batch(batch):
                async with sem:
                    payload = [
                        {"missing": _pair_view(a, snapshot, self.profiles),
                         "sub": _pair_view(b, snapshot, self.profiles)}
                        for (a, b) in batch
                    ]
                    for attempt in range(3):
                        try:
                            return await llm.judge_substitutions(payload, cli, model=refresh_model)
                        except Exception:
                            if attempt < 2:
                                await asyncio.sleep(3 * (attempt + 1))
                            else:
                                return []
                    return []

            for verdicts in await asyncio.gather(
                *(_judge_batch(b) for b in batches), return_exceptions=True
            ):
                if isinstance(verdicts, Exception):
                    continue
                for v in verdicts or []:
                    if not isinstance(v, dict):
                        continue
                    a = str(v.get("missing_id", "")).strip()
                    b = str(v.get("substitute_id", "")).strip()
                    if not a or not b or a not in live or b not in live:
                        continue
                    new_matrix.setdefault(a, {})[b] = {
                        "verdict": str(v.get("verdict", "conditional")).lower(),
                        "confidence": str(v.get("confidence", "medium")).lower() or "medium",
                        "conditions": str(v.get("conditions", "") or ""),
                        "dosage_note": str(v.get("dosage_note", "") or ""),
                        "reason": str(v.get("reason", "") or ""),
                    }

            # 5. persist atomically + swap in. Advance the cached fingerprint
            #    whenever we judged anything (so an inventory-only reload
            #    doesn't re-trigger a full refresh); only a total failure
            #    (rate-limited to zero) leaves it stale to retry next reload.
            fp = _fingerprint()
            new_total = sum(len(v) for v in new_matrix.values())
            yielded_ok = not needed or new_total > 0
            _atomic_write_json(MATRIX_FILE, {
                "fingerprint": fp if yielded_ok else self._cached_fingerprint,
                "updated_at": _now_iso(),
                "model": refresh_model,
                "matrix": new_matrix,
            })
            with self._lock:
                self.matrix = new_matrix
                if yielded_ok:
                    self._cached_fingerprint = fp
                self._active_fingerprint = fp
        finally:
            try:
                await cli.close()
            except Exception:  # noqa: BLE001
                pass

    def _needed_pairs(self, snapshot: dict) -> list[tuple[str, str]]:
        ings = snapshot["ingredients"]
        ids = [i for i in ings if ings[i]["category"] not in _NON_SUBSTITUTE_CATEGORIES]
        pairs: list[tuple[str, str]] = []
        for a in ids:
            ap = self.profiles.get(a)
            if not ap:
                continue
            for b in ids:
                if a == b:
                    continue
                bp = self.profiles.get(b)
                if not bp:
                    continue
                if rule_score(ap, bp, ings[a]["category"], ings[b]["category"]) >= _RULE_CANDIDATE:
                    pairs.append((a, b))
        return pairs

    def _merge_profiles(self, inferred: list) -> None:
        changed = False
        for row in inferred or []:
            prof = _profile_from_row(row, source="llm") if isinstance(row, dict) else None
            if prof and prof.ingredient_id not in self.profiles:
                self.profiles[prof.ingredient_id] = prof
                changed = True
        if changed:
            self._save_profiles()

    def _save_profiles(self) -> None:
        rows = []
        for pid, p in sorted(self.profiles.items()):
            rows.append({
                "id": pid,
                "family": p.family,
                "flavor": {k: p.flavor[k] for k in FLAVOR_AXES if p.flavor.get(k)},
                "function": sorted(p.function),
                "abv": p.abv,
                "intensity": p.intensity,
                "source": p.source,
            })
        _atomic_write_yaml(PROFILES_FILE, {"profiles": rows})


# --------------------------------------------------------------------------- #
# Snapshot / view helpers (decouple the engine from the Cellar class)
# --------------------------------------------------------------------------- #
def _cellar_snapshot(cellar) -> dict:
    return {
        "ingredients": {
            ing.id: {
                "category": ing.category,
                "zh": ing.zh,
                "en": ing.en,
                "label": ing.label,
                "aliases": list(ing.aliases),
            }
            for ing in cellar.ingredients.values()
        }
    }


def _pair_view(pid: str, snapshot: dict, profiles: dict[str, IngredientProfile]) -> dict:
    ing = snapshot["ingredients"].get(pid, {})
    p = profiles.get(pid)
    return {
        "id": pid,
        "zh": ing.get("zh", ""),
        "en": ing.get("en", ""),
        "category": ing.get("category", ""),
        "family": p.family if p else "",
        "flavor": {k: p.flavor[k] for k in FLAVOR_AXES if p and p.flavor.get(k)},
        "function": sorted(p.function) if p else [],
        "abv": p.abv if p else 0.0,
        "intensity": p.intensity if p else 1.0,
    }


engine = SubEngine()
