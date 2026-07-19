"""Aggregate recipe ingredients across a meal plan into a course list."""
import json
import re
import unicodedata
from pathlib import Path

from rich.console import Console

from src.config import DATA_DIR
from src.models.meal_plan import (
    CourseItem,
    CourseItemSource,
    CourseList,
    MealPlan,
)
from src.models.recipe import Ingredient, Recipe

CATEGORY_FILE = DATA_DIR / "ingredient_categories.json"
UNCATEGORIZED = "Other"

_console = Console()


def build_course_list(
    plan: MealPlan,
    recipes_by_id: dict[str, Recipe],
    *,
    book_dir: Path | None = None,
    use_llm_aliases: bool = False,
) -> CourseList:
    """Collect ingredients across every slot; group, sum, categorise, format.

    When `use_llm_aliases=True` (and `book_dir` is given), an extra LLM-backed
    pass clusters look-alike rule-based keys and merges those that the LLM
    confirms are the same product. Decisions are cached in `<book>/aliases.db`
    so subsequent runs are deterministic + free.
    """
    main = _collect(plan, recipes_by_id, optional_bucket=False)
    optional = _collect(plan, recipes_by_id, optional_bucket=True)

    if use_llm_aliases and book_dir is not None:
        main = _resolve_aliases(main, book_dir, plan.manifest.objective, "main")
        optional = _resolve_aliases(optional, book_dir, plan.manifest.objective, "optional")

    category_map = _load_category_map()

    items_by_category: dict[str, list[CourseItem]] = {}
    for agg in main.values():
        item = agg.to_course_item(is_optional=False, category_map=category_map)
        items_by_category.setdefault(item.category, []).append(item)

    for cat in items_by_category:
        items_by_category[cat].sort(key=lambda i: i.display_name.lower())

    optional_items = [
        agg.to_course_item(is_optional=True, category_map=category_map)
        for agg in optional.values()
    ]
    optional_items.sort(key=lambda i: i.display_name.lower())

    return CourseList(
        cookbook_name=plan.cookbook_name,
        plan_days=len(plan.days),
        items_by_category=items_by_category,
        optional_items=optional_items,
    )


def _collect(
    plan: MealPlan,
    recipes_by_id: dict[str, Recipe],
    *,
    optional_bucket: bool,
) -> dict[str, "_Aggregate"]:
    """First-pass aggregation using only rule-based keys."""
    out: dict[str, _Aggregate] = {}
    for day in plan.days:
        for slot in day.slots:
            recipe = recipes_by_id.get(slot.recipe_id)
            if recipe is None:
                continue
            for ing in recipe.ingredients:
                if ing.is_optional != optional_bucket:
                    continue
                key = _agg_key(ing)
                agg = out.setdefault(
                    key,
                    _Aggregate(canonical_name=key, display_name=ing.name),
                )
                if _display_score(ing.name) < _display_score(agg.display_name):
                    agg.display_name = ing.name
                agg.total_g += float(ing.quantity_g)
                agg.sources.append(CourseItemSource(
                    day=slot.day,
                    meal_type=slot.meal_type,
                    recipe_title=slot.recipe_title,
                    quantity_g=float(ing.quantity_g),
                ))
    return out


def _resolve_aliases(
    buckets: dict[str, "_Aggregate"],
    book_dir: Path,
    cookbook_objective: str,
    label: str,
) -> dict[str, "_Aggregate"]:
    """LLM-backed merge pass over rule-based aggregation buckets.

    Caches every decision in `<book>/aliases.db`. Falls back gracefully (no
    error to caller) if the LLM call fails — the rule-based result is used.
    """
    from src.planning.alias_cache import AliasCache, jaccard_clusters

    cache = AliasCache(book_dir)
    raw_keys = list(buckets.keys())

    # 1. Pull cached decisions.
    remap: dict[str, str] = {}             # raw_key -> canonical_key
    cached_displays: dict[str, str] = {}   # canonical_key -> display
    for raw in raw_keys:
        hit = cache.get(raw)
        if hit:
            canonical_key, canonical_display = hit
            remap[raw] = canonical_key
            if canonical_display:
                cached_displays.setdefault(canonical_key, canonical_display)

    # 2. Cluster the unresolved keys.
    unresolved = [k for k in raw_keys if k not in remap]
    clusters = jaccard_clusters(unresolved, threshold=0.5)
    _console.print(
        f"[dim]  alias ({label}): {len(raw_keys)} keys, "
        f"{len(unresolved)} unresolved, {len(clusters)} clusters[/dim]"
    )

    # 3. Ask the LLM about the unresolved clusters (single batched call).
    if clusters:
        _console.print(f"[dim]  alias ({label}): LLM call on {len(clusters)} clusters...[/dim]")
        try:
            llm_remap, llm_displays = _llm_resolve_clusters(
                clusters, cookbook_objective, buckets,
            )
            _console.print(f"[dim]  alias ({label}): LLM OK, {len(llm_remap)} mappings[/dim]")
            remap.update(llm_remap)
            cached_displays.update(llm_displays)

            # Persist for next run.
            to_register: dict[str, tuple[str, str | None, str]] = {}
            for raw in {r for cluster in clusters for r in cluster}:
                canonical = remap.get(raw, raw)
                display = cached_displays.get(canonical)
                to_register[raw] = (canonical, display, "llm")
            cache.bulk_register(to_register)
        except Exception as e:  # noqa: BLE001
            _console.print(
                f"[yellow]LLM alias resolution ({label}) failed — "
                f"keeping the rule-based merge. Detail: {e!r}[/yellow]"
            )

    # 4. Identity remap for everything still untouched (rule-only).
    rule_register: dict[str, tuple[str, str | None, str]] = {}
    for raw in raw_keys:
        if raw not in remap:
            remap[raw] = raw
            rule_register[raw] = (raw, None, "rule")
    cache.bulk_register(rule_register)

    # 5. Re-bucket using the remap.
    merged: dict[str, _Aggregate] = {}
    for raw, agg in buckets.items():
        canonical_key = remap[raw]
        target = merged.get(canonical_key)
        if target is None:
            new_display = cached_displays.get(canonical_key, agg.display_name)
            target = _Aggregate(canonical_name=canonical_key, display_name=new_display)
            merged[canonical_key] = target
        # Prefer the cached/LLM-suggested display, otherwise reuse the
        # rule-based "best" name from the source aggregate.
        candidate = cached_displays.get(canonical_key, agg.display_name)
        if _display_score(candidate) < _display_score(target.display_name):
            target.display_name = candidate
        target.total_g += agg.total_g
        target.sources.extend(agg.sources)
    return merged


def _llm_resolve_clusters(
    clusters: list[list[str]],
    cookbook_objective: str,
    buckets: dict[str, "_Aggregate"],
) -> tuple[dict[str, str], dict[str, str]]:
    """Ask the LLM to split each cluster into product-level groups.

    Sends the *display names* (more readable for the LLM than the
    accent-folded keys) and reverse-maps the response back to keys.
    """
    import json as _json

    from src.config import settings
    from src.llm import client as llm
    from src.llm.output_schemas import AliasResolverOutput
    from src.llm.prompts import alias_resolver

    # Display name → raw key. If a display collides across keys, last wins —
    # the LLM is told to act on display names, so collisions are inherently merged.
    display_to_key: dict[str, str] = {}
    display_clusters: list[list[str]] = []
    for cluster in clusters:
        display_cluster: list[str] = []
        for raw_key in cluster:
            display = buckets[raw_key].display_name
            display_to_key[display] = raw_key
            display_cluster.append(display)
        display_clusters.append(sorted(set(display_cluster)))

    schema_json = _json.dumps(
        AliasResolverOutput.model_json_schema(),
        ensure_ascii=False,
        indent=2,
    )
    user = alias_resolver.build_user(display_clusters, cookbook_objective, schema_json)

    # Alias resolution is a name-matching task — Flash Lite is fast and accurate
    # enough; using Pro thinking on 30 clusters takes minutes and can time out.
    raw_response = llm.create_message_with_model(
        alias_resolver.SYSTEM,
        user,
        model=settings.image_prompt_model,
        max_tokens=4096,
        thinking_budget=2000,
    )
    parsed = AliasResolverOutput.model_validate_json(raw_response)

    # Build remap: every member's key → a synthetic canonical key derived from
    # the LLM's chosen canonical display (run it through _normalise_for_key
    # so it matches our naming convention; equal displays → equal keys).
    remap: dict[str, str] = {}
    displays: dict[str, str] = {}
    for group in parsed.groups:
        canonical_key = _normalise_for_key(group.canonical) or group.canonical.lower()
        displays[canonical_key] = group.canonical
        for member in group.members:
            raw_key = display_to_key.get(member)
            if raw_key is None:
                # LLM returned a name we didn't send — best-effort reverse lookup.
                raw_key = _normalise_for_key(member)
            remap[raw_key] = canonical_key
    return remap, displays


# ── Aggregation helper ──────────────────────────────────────────

class _Aggregate:
    __slots__ = ("canonical_name", "display_name", "total_g", "sources")

    def __init__(self, canonical_name: str, display_name: str) -> None:
        self.canonical_name = canonical_name
        self.display_name = display_name
        self.total_g = 0.0
        self.sources: list[CourseItemSource] = []

    def to_course_item(
        self,
        is_optional: bool,
        category_map: dict[str, list[str]],
    ) -> CourseItem:
        clean = _strip_qualifiers_from_display(self.display_name)
        return CourseItem(
            canonical_name=self.canonical_name,
            display_name=clean,
            total_quantity_g=round(self.total_g, 1),
            total_quantity_display=format_quantity(self.total_g),
            category=_categorize(self.canonical_name, category_map),
            is_optional=is_optional,
            source_recipes=self.sources,
        )


# ── Category map + matching ─────────────────────────────────────

_CATEGORY_MAP_CACHE: dict[str, list[str]] | None = None


def _load_category_map() -> dict[str, list[str]]:
    """Load `ingredient_categories.json` once; keywords are pre-normalised."""
    global _CATEGORY_MAP_CACHE
    if _CATEGORY_MAP_CACHE is not None:
        return _CATEGORY_MAP_CACHE

    if not CATEGORY_FILE.exists():
        _CATEGORY_MAP_CACHE = {}
        return _CATEGORY_MAP_CACHE

    raw = json.loads(CATEGORY_FILE.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for category, keywords in raw.get("categories", {}).items():
        out[category] = sorted(
            {_normalise(k) for k in keywords},
            key=lambda s: -len(s),  # longest first — avoids prefix collisions
        )
    _CATEGORY_MAP_CACHE = out
    return out


def _categorize(canonical_name: str, category_map: dict[str, list[str]]) -> str:
    haystack = _normalise(canonical_name)
    if not haystack:
        return UNCATEGORIZED
    for category, keywords in category_map.items():
        for kw in keywords:
            if kw and kw in haystack:
                return category
    return UNCATEGORIZED


def _agg_key(ing: Ingredient) -> str:
    """Normalised key for shopping-list aggregation.

    Uses the user-facing `name` (e.g. "plain yogurt") rather than the USDA
    `canonical_name` (e.g. "Yogurt, plain, whole milk") because the canonical
    is far too granular for grocery shopping — several USDA entries map to the
    same item on a shopping list.

    Normalisation merges case / underscore / plural variants:
      "lemon_juice" + "Lemon juice"      → "lemon juice"
      "red onions" + "red onion"         → "red onion"
    """
    base = ing.name.strip() or ing.canonical_name.strip()
    return _normalise_for_key(base)


def _normalise_for_key(text: str) -> str:
    """NFD accent-fold + lowercase + punctuation→space + plural strip + drop qualifiers.

    Drops cooking-state, packaging, and quality tokens
    ("cooked", "raw", "canned", "whole-grain", "0%", "ground"…) and key-only
    markers ("plain", "organic") so visually-similar groceries collapse to one
    item. Colour tokens (white/red/black/green/yellow) stay — they identify
    the variety.

    Special collapses:
      - leading "slices of" / "slice of" stripped
      - "powdered" alias to "powder" ("garlic powdered" + "garlic powder" merge)
      - "lemon zest <anything>" truncated to "lemon zest"
    """
    folded = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    folded = folded.lower()
    folded = re.sub(r"\b\d+\s*%", " ", folded)         # "0%", "20 %" → ""
    folded = re.sub(r"[_\-'`’]", " ", folded)
    folded = " ".join(folded.split())
    folded = _strip_prefix(folded)

    words = [_singularise(w) for w in folded.split()]
    words = [_KEY_ALIASES.get(w, w) for w in words]
    head = [w for w in words
            if w not in _STRIP_BOTH and w not in _STRIP_KEY_ONLY]
    if not head:
        head = words

    # Collapse "lemon zest *" → "lemon zest"
    if head[:2] == ["lemon", "zest"]:
        head = ["lemon", "zest"]

    return " ".join(head)


def _strip_prefix(folded_lc: str) -> str:
    """Remove leading 'slices of' / 'slice of' (already accent-folded, lc)."""
    for prefix in ("slices of ", "slice of "):
        if folded_lc.startswith(prefix):
            return folded_lc[len(prefix):]
    return folded_lc


def _singularise(word: str) -> str:
    """Drop a trailing -s on words long enough that it's safe.

    Most English nouns in this domain just add -s for plural ("onions" →
    "onion", "tomatoes" → "tomatoe" — close enough for merging, "eggs" →
    "egg"). Length guard keeps short tokens like "oat" intact; the -es →
    -e residue is harmless since both spellings normalise the same way.
    """
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


# Tokens stripped from BOTH key and display.
# Stored in their singularised, accent-folded form (that's what _normalise_for_key produces).
# Colour tokens (white/red/black/green/yellow) are intentionally absent — they identify variety.
_STRIP_BOTH: frozenset[str] = frozenset({
    # cooking state
    "raw",
    "cooked", "uncooked", "precooked",
    "boiled", "roasted", "baked", "grilled", "steamed", "sauteed",
    # packaging / preservation
    "and", "of", "in", "the",
    "can", "canned",
    "jar", "jarred",
    "bottle", "bottled",
    "frozen",
    "fresh",
    "dry", "dried", "dehydrated",
    "drain", "drained",
    "spray",            # "olive oil spray"
    # quality / processing
    "wholegrain", "wholewheat",
    "lowfat", "lite", "light", "reduced",
    "skinles", "skinnles", "boneles",  # "skinless" / "boneless" minus the -s
    "ground",
    "cracked", "crushed",
    "refined", "unrefined",
    "iodized", "iodised",
    "virgin",
    "extra",
    "sweet",
    "sea",              # "sea salt"
    "fine", "coarse",   # "fine salt", "coarse salt"
    # variety qualifiers that don't change what you buy
    "small", "large", "big",
    "long", "round", "short",
    "baby",
})

# Tokens stripped from KEY ONLY (kept in display so user sees the quality marker).
# These collapse the merge but leave the badge visible.
_STRIP_KEY_ONLY: frozenset[str] = frozenset({
    "plain", "unsweetened",
    "organic",
})

# Token aliases applied during key normalisation AND display rebuild —
# powdered ⇌ powder lets "Garlic powdered" and "Garlic powder" share a key.
_KEY_ALIASES: dict[str, str] = {
    "powdered": "powder",
}
_DISPLAY_ALIASES: dict[str, str] = dict(_KEY_ALIASES)


def _is_strip_both_word(word: str) -> bool:
    """Check if a single word is a 'strip from display' qualifier."""
    folded = "".join(
        ch for ch in unicodedata.normalize("NFD", word.lower())
        if unicodedata.category(ch) != "Mn"
    )
    folded = re.sub(r"[_\-'`’]", " ", folded).strip()
    if not folded:
        return False
    return _singularise(folded) in _STRIP_BOTH


def _display_score(name: str) -> tuple[int, int]:
    """Lower is better: (qualifier-token count, total length).

    Counts only _STRIP_BOTH qualifiers (so 'plain tomato puree' beats
    'tomato puree' — both have zero strip-both qualifiers, longer wins
    because we want to keep the 'plain' marker visible)."""
    tokens = name.split()
    quals = sum(1 for t in tokens if _is_strip_both_word(t))
    # We want to KEEP nature/bio in display, so prefer the variant
    # that includes them (longer name, fewer tokens to strip later).
    return (quals, -len(name))


_PREFIX_DISPLAY_RE = re.compile(r"^\s*[Ss]lices?\s+[Oo]f\s+")
_PERCENT_DISPLAY_RE = re.compile(r"\s*\b\d+\s*%")


def _strip_qualifiers_from_display(name: str) -> str:
    """Clean a display name: strip prefix, percentages, qualifier words, apply aliases.

    Preserves casing of the kept words. Falls back to the original name if
    every word would be stripped.
    """
    prefix_stripped = _PREFIX_DISPLAY_RE.sub("", name) != name
    name = _PREFIX_DISPLAY_RE.sub("", name)
    name = _PERCENT_DISPLAY_RE.sub("", name)
    out: list[str] = []
    for w in name.split():
        if _is_strip_both_word(w):
            continue
        alias = _DISPLAY_ALIASES.get(w.lower())
        if alias:
            out.append(alias.capitalize() if w[:1].isupper() else alias)
        else:
            out.append(w)

    if not out:
        return name

    # If we stripped a prefix and the new first word is lowercase, capitalise it
    # so "slices of rye bread" → "Rye bread".
    if prefix_stripped and out[0][:1].islower():
        out[0] = out[0][0].upper() + out[0][1:]

    # Special: "Lemon zest <anything>" → "Lemon zest"
    if len(out) >= 2 and [w.lower() for w in out[:2]] == ["lemon", "zest"]:
        out = out[:2]

    return " ".join(out)


def _normalise(text: str) -> str:
    """Lighter normaliser used for category keyword matching."""
    folded = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join(folded.lower().split())


# ── Quantity formatting ─────────────────────────────────────────

def format_quantity(grams: float) -> str:
    """Render a total quantity in grocery-friendly units."""
    if grams <= 0:
        return "0 g"
    if grams >= 1000:
        kg = grams / 1000
        return f"{kg:.1f} kg".replace(".0 kg", " kg")
    if grams >= 100:
        rounded = int(round(grams / 10.0) * 10)
        return f"{rounded} g"
    rounded = int(round(grams / 5.0) * 5)
    if rounded == 0:
        rounded = 5
    return f"{rounded} g"
