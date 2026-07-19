"""Stage 5 — cooking-process & editorial sanity checks (advisory only).

Warnings only (never blocking), run alongside the per-serving quantity plausibility in
``quantity_checker.py``:

  * **Heavy / greasy preparation** (``check_cooking_method``) — a softer net below the
    ``no_deep_fried`` diet hard block: cooking *in* a lot of fat (duck fat, lard, "plenty of
    oil", an oil bath…), which is heavier than the book's light-cooking stance even when it
    isn't strictly deep-frying.
  * **Implausible oven temperature** (``check_cooking_method``) — a Celsius value hotter than a
    home oven ever runs is almost always an °F value mislabeled as °C (the draft prompt asks for
    both, e.g. "375°F / 190°C", so the °F figures are expected — only the °C one matters here).
  * **"Super easy" overshoot** (``check_super_easy``) — a soft companion to the editorial
    ``easy_recipe_constraints`` in ``data/high_protein_high_fiber_guidelines.yaml``: too many meaningful
    ingredients, or too long. Thresholds sit *above* the editorial 10/30/45 targets so this only
    fires on a clear overshoot; the LLM critic handles the grey zone. (The function name and the
    book's outward-facing wording are both "Super Easy".)
  * **Ambiguous grain base** (``check_grain_base``) — a soft companion to the ``no_refined_grain_base``
    diet hard block (which only trips on an *explicitly* refined name like "white rice"): a
    carbohydrate base named only "pasta" / "rice" / "bread" / … with no whole-grain qualifier.

The keyword lists are intentionally conservative — they catch blatant cases, not subtle ones.
"""
import re
from dataclasses import dataclass, field

from src.cooking.quantity_checker import _OIL_KEYWORDS
from src.diet_rules.rules import _REFINED_GRAIN_MIN_G
from src.models.recipe import RecipeDraft

# Cooking *in* a substantial amount of fat — heavier than the diet rules already block.
_HEAVY_COOKING_KW: tuple[str, ...] = (
    "duck fat", "goose fat", "bacon grease", "lard ",
    "plenty of oil", "generous amount of oil", "lots of oil", "copious oil",
    "cover with oil", "oil to cover", "submerge in oil", "submerged in oil",
    "bath of oil", "oil bath", "deep fryer", "deep-fryer",
)

# A home oven / broiler tops out around ~290 °C; anything above this with a °C label is
# almost certainly an °F figure mislabeled (350 / 400 / 425 °F → "°C").
_MAX_PLAUSIBLE_OVEN_C = 290
_CELSIUS_RE = re.compile(r"(\d{2,4})\s*°\s*C\b")

# ── "Super easy" thresholds (above the editorial 10 / 30 / 45 so we only flag a clear overshoot) ──
_MAX_MEANINGFUL_INGREDIENTS = 12
_MAX_PREP_MIN = 35
_MAX_TOTAL_MIN = 60
# Ingredient names that don't count toward the "meaningful ingredient" tally (a small cooking-oil
# amount is also excluded — see _OIL_MAX_FREE_G below).
_FREEBIE_INGREDIENT_KW: tuple[str, ...] = ("salt", "pepper", "black pepper", "water", "cooking spray")
_OIL_MAX_FREE_G = 20.0  # a small drizzle of oil — not "meaningful"
# Set-and-forget cues: a recipe with one of these in its steps is allowed to run long.
_SET_AND_FORGET_RE = re.compile(
    r"slow cooker|crock|overnight|refrigerate[^.]*hour|bake[^.]*hour", re.IGNORECASE
)

# ── Ambiguous grain base ──
_BASE_GRAIN_KW: tuple[str, ...] = (
    "pasta", "noodle", "noodles", "bread", "tortilla", "couscous", "rice", "flour",
    "bun", "wrap", "pita",
)
_WHOLE_GRAIN_QUALIFIER_KW: tuple[str, ...] = (
    "whole", "whole-wheat", "wholewheat", "whole-grain", "wholegrain", "brown", "wild",
    "multigrain", "multi-grain", "rye", "oat", "quinoa", "buckwheat", "spelt", "farro",
    "barley", "bulgur", "sprouted",
)


# Health-food / specialty items a typical US shopper can't reliably find at a mainstream supermarket
# (Walmart / Kroger / Target). Conservative + advisory only — the ideation/draft prompts steer away
# and the LLM critic catches nuanced cases; this is a deterministic backstop. Extend as needed.
_HARD_TO_FIND_KW: tuple[str, ...] = (
    "nutritional yeast",
    "coconut aminos", "liquid aminos",
    "psyllium husk", "psyllium",
    "vital wheat gluten", "seitan",
    "lupin flour", "lupini", "teff", "cassava flour", "tigernut", "green banana flour",
    "powdered peanut butter", "peanut butter powder", "pb2",
)


@dataclass
class CookingMethodResult:
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:  # advisory only — Stage 5 never blocks on this
        return not self.warnings


def check_cooking_method(draft: RecipeDraft) -> CookingMethodResult:
    """Inspect the instructions for a heavy/greasy preparation or an implausible oven temperature."""
    warnings: list[str] = []

    for step in draft.instructions:
        low = step.lower()
        hit = next((kw for kw in _HEAVY_COOKING_KW if kw in low), None)
        if hit:
            warnings.append(
                f"Possibly heavy / greasy preparation (\"{hit.strip()}\") — favor a lighter method "
                f"(oven, steaming, stovetop with a drizzle of oil, broiling, poaching)."
            )
            break

    for m in _CELSIUS_RE.finditer(" ".join(draft.instructions)):
        val = int(m.group(1))
        if val > _MAX_PLAUSIBLE_OVEN_C:
            warnings.append(
                f"Suspect temperature: {val}°C — a home oven rarely exceeds ~260°C. "
                f"Check the °C / °F conversion (every temperature should appear in both units)."
            )
            break

    return CookingMethodResult(warnings=warnings)


def _is_meaningful_ingredient(name: str, quantity_g: float) -> bool:
    low = name.lower()
    if any(kw in low for kw in _FREEBIE_INGREDIENT_KW):
        return False
    if any(kw in low for kw in _OIL_KEYWORDS) and quantity_g <= _OIL_MAX_FREE_G:
        return False
    return True


def check_super_easy(draft: RecipeDraft) -> CookingMethodResult:
    """Flag a clear overshoot of the editorial "super simple" caps (≈10 ingredients / 30 min active /
    45 min total — see ``easy_recipe_constraints`` in ``data/high_protein_high_fiber_guidelines.yaml``)."""
    warnings: list[str] = []

    meaningful = sum(
        1 for ing in draft.ingredients
        if _is_meaningful_ingredient(ing.canonical_name or ing.name, ing.quantity_g)
    )
    if meaningful > _MAX_MEANINGFUL_INGREDIENTS:
        warnings.append(
            f"Long ingredient list: {meaningful} meaningful ingredients (the book aims for about 10 "
            f"or fewer — salt, pepper, water, and a small amount of cooking oil don't count). Consider "
            f"trimming or consolidating."
        )

    if draft.prep_time_min > _MAX_PREP_MIN:
        warnings.append(
            f"Long active time: {draft.prep_time_min} min hands-on (the book aims for about 30 min "
            f"or less). Consider a simpler prep."
        )

    total_min = draft.prep_time_min + (draft.cook_time_max_min or draft.cook_time_min)
    if total_min > _MAX_TOTAL_MIN and not _SET_AND_FORGET_RE.search(" ".join(draft.instructions)):
        warnings.append(
            f"Long total time: ~{total_min} min start to finish (the book aims for about 45 min or "
            f"less, unless it's a set-and-forget slow-cooker / oven recipe). Consider shortening it."
        )

    return CookingMethodResult(warnings=warnings)


def check_grain_base(draft: RecipeDraft) -> CookingMethodResult:
    """Flag a carbohydrate base whose name doesn't say whether it's a whole grain. Soft companion to
    the ``no_refined_grain_base`` hard block, which only trips on an explicitly refined name."""
    warnings: list[str] = []

    for ing in draft.ingredients:
        name = (ing.canonical_name or ing.name).lower()
        if not any(re.search(rf"\b{re.escape(kw)}\b", name) for kw in _BASE_GRAIN_KW):
            continue
        if any(kw in name for kw in _WHOLE_GRAIN_QUALIFIER_KW):
            continue
        if ing.quantity_g < _REFINED_GRAIN_MIN_G:
            continue
        warnings.append(
            f"Carb base \"{ing.name}\" ({ing.quantity_g:g} g) doesn't say whether it's a whole grain "
            f"— the book wants whole/intact grains. Specify e.g. \"brown rice\" / \"100% whole-wheat "
            f"pasta\" / \"whole-grain tortilla\", or swap it."
        )

    return CookingMethodResult(warnings=warnings)


def check_everyday_ingredients(draft: RecipeDraft) -> CookingMethodResult:
    """Flag ingredients a typical US shopper can't easily find at a mainstream supermarket
    (health-food / specialty items). Advisory only — a deterministic backstop for the common
    offenders; the prompts steer away and the LLM critic handles the nuanced cases."""
    hits = [
        ing.name
        for ing in draft.ingredients
        if any(kw in (ing.name or "").lower() for kw in _HARD_TO_FIND_KW)
    ]
    if not hits:
        return CookingMethodResult(warnings=[])
    return CookingMethodResult(warnings=[
        f"Hard-to-find ingredient(s): {', '.join(hits)} — health-food / specialty items many US "
        f"shoppers can't easily source. Swap for a mainstream-supermarket staple (e.g. grated "
        f"parmesan for nutritional yeast; soy sauce for aminos; natural peanut butter for the powder)."
    ])
