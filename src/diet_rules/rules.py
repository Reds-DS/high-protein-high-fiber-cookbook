"""High-protein high-fiber weight-loss diet rules.

Deterministic checks derived from ``data/high_protein_high_fiber_guidelines.yaml``
(parsed by :mod:`src.diet_rules.spec`).

Two kinds of rule:

  * **Hard-block rules** (structural, blocking) — catch *blatant* violations of
    the YAML's ``hard_blocks``: a recipe built on processed/cured meat, a
    sugar-sweetened beverage as an ingredient, deep-frying, an explicitly-refined-
    grain base, or a recipe that is essentially a sugar-delivery vehicle. They run
    pre- and post-nutrition. They are deliberately **conservative** (high quantity
    thresholds, narrow keyword lists): a false positive sends the draft back
    through Stage 2's correction loop, so we err toward leniency and let the
    prompt (which states the hard rules up front) plus the human review gate
    catch what slips through.

  * **Soft per-tier rules** (warnings, never blocking) — once nutrition is
    computed, check the recipe against its chapter's nutrient tier
    (``main`` / ``snack`` / ``dessert``): protein/fiber floors, net-carb / total-
    carb / sodium / saturated-fat / energy ceilings, and an added-sugar ceiling
    (preferring the LLM-estimated ``NutritionInfo.added_sugar_g``, falling back to
    an added-sweetener ingredient-gram proxy — ``NutritionInfo.sugar_g`` is *total*
    sugars, not *added*, so it can't substitute).

The keyword lists below match English ingredient/instruction text and are deliberately
conservative — the prompt (which states the hard rules up front) plus the human review
gate are the real backstops. Cf. ``src/cooking/quantity_checker.py`` and
``src/cooking/method_checker.py``, which carry similar keyword lists.
"""
from src.diet_rules.base_rule import BaseDietRule
from src.diet_rules.spec import NutrientEnvelope, load_spec
from src.models.diet import RuleResult
from src.models.nutrition import NutritionInfo
from src.models.recipe import Ingredient, RecipeDraft

# ── English keyword lists (best-effort) ─────────────────────

# Processed / cured meats — flag only when used as a substantial ingredient.
_PROCESSED_MEAT_KW = (
    "bacon", "sausage", "salami", "chorizo", "pepperoni", "prosciutto", "mortadella",
    "pastrami", "bologna", "hot dog", "frankfurter", "deli ham", "deli turkey",
    "corned beef", "spam", "guanciale", "speck", "kielbasa", "andouille",
)
_VEGGIE_FALSE_FRIENDS = ("vegan", "veggie ", "plant-based", "plant based", "tofu", "soy ", "seitan", "tempeh", "meatless")
_PROCESSED_MEAT_MIN_G = 60.0  # total for 2 servings (~30 g/serving) → a "base", not an accent

# Sugar-sweetened beverages — never an ingredient, at any quantity.
_SSB_KW = (
    "soda", "cola", "coca-cola", "pepsi", "sprite", "fanta", "mountain dew", "dr pepper",
    "lemonade", "iced tea", "sweet tea", "energy drink", "red bull", "monster energy",
    "gatorade", "powerade", "sports drink", "fruit punch", "kool-aid", "hi-c", "sunny d",
)
# Fruit juices / nectars — flag when more than a splash. (Not "lemon juice" / "lime juice" /
# "tomato juice", which are fine flavorings / bases.)
_JUICE_KW = (
    "orange juice", "apple juice", "grape juice", "pineapple juice", "fruit juice",
    "mango juice", "cranberry juice cocktail", "juice cocktail", "fruit nectar",
)
_JUICE_MIN_G = 30.0  # total for 2 servings

# Deep-frying — detected from the instruction text (titles like "oven fries" are fine).
_DEEP_FRY_KW = (
    "deep-fry", "deep fry", "deep-fried", "deep fried", "deep frying", "deep-frying",
    "bath of oil", "submerged in hot oil", "submerge in hot oil", "in a deep fryer",
)
_DEEP_FRY_OIL_KW = ("deep-frying oil", "deep frying oil", "oil for deep frying", "oil for deep-frying")

# Refined grains — flag only when the canonical/display name *explicitly* says so.
_REFINED_GRAIN_KW = (
    "white rice", "polished rice", "instant rice", "white pasta", "white bread",
    "white sandwich bread", "white flour", "refined flour", "bleached flour",
    "white all-purpose flour", "white bread flour", "white semolina",
)
_REFINED_GRAIN_MIN_G = 50.0  # total for 2 servings → the carbohydrate base

# Added sweeteners — for the sugar-vehicle hard block and the added-sugar proxy fallback.
_SWEETENER_KW = (
    "sugar", "honey", "maple syrup", "agave", "agave nectar", "corn syrup", "glucose syrup",
    "rice syrup", "rice malt syrup", "brown sugar", "cane sugar", "coconut sugar",
    "powdered sugar", "confectioners sugar", "confectioner's sugar", "molasses",
    "turbinado sugar", "demerara sugar",
)
_SWEETENER_FALSE_FRIENDS = (
    "no sugar", "no added sugar", "sugar-free", "sugar free", "unsweetened",
    "sugar snap", "sugar substitute", "sugar alcohol",
)
_SWEETENER_PRIMARY_MIN_G = 40.0  # total for 2 servings — below this it's a flavoring, not a "base"


def _ing_text(ing: Ingredient) -> str:
    return f"{ing.name} {ing.canonical_name}".lower()


def _has_kw(text: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in text for kw in keywords)


def _is_sweetener(ing: Ingredient) -> bool:
    n = _ing_text(ing)
    if _has_kw(n, _SWEETENER_FALSE_FRIENDS):
        return False
    return _has_kw(n, _SWEETENER_KW)


# ── hard-block rules (structural, blocking) ─────────────────

class NoProcessedCuredMeatBase(BaseDietRule):
    @property
    def name(self) -> str:
        return "hphf.no_processed_cured_meat_base"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        for ing in draft.ingredients:
            n = _ing_text(ing)
            if _has_kw(n, _VEGGIE_FALSE_FRIENDS):
                continue
            if _has_kw(n, _PROCESSED_MEAT_KW) and ing.quantity_g >= _PROCESSED_MEAT_MIN_G:
                return self._fail([
                    f"Recipe built on processed / cured meat: \"{ing.name}\" ({ing.quantity_g:g} g). "
                    f"Replace it with a lean protein (poultry, fish, eggs, legumes) or cut it to a small accent amount."
                ])
        return self._ok()


class NoSugarSweetenedBeverageComponent(BaseDietRule):
    @property
    def name(self) -> str:
        return "hphf.no_sugar_sweetened_beverage_component"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        for ing in draft.ingredients:
            n = _ing_text(ing)
            if _has_kw(n, _SSB_KW):
                return self._fail([
                    f"Sugar-sweetened beverage as an ingredient: \"{ing.name}\". No sweetened drink "
                    f"(soda, store-bought fruit juice, energy/sports drink…) belongs in the recipe."
                ])
            if _has_kw(n, _JUICE_KW) and ing.quantity_g >= _JUICE_MIN_G:
                return self._fail([
                    f"Fruit juice in a notable amount: \"{ing.name}\" ({ing.quantity_g:g} g). "
                    f"Use the whole fruit, or just a splash of juice as seasoning."
                ])
        return self._ok()


class NoAddedSugarPrimaryBase(BaseDietRule):
    """The recipe must not be essentially a sugar-delivery vehicle — added sugar (or another
    added sweetener) must not be the primary ingredient by weight. Conservative: only trips when
    a single added sweetener is the largest ingredient in the recipe (and above a floor). Desserts
    are held to this too, but their softer added-sugar ceiling is enforced by ``AddedSugarLimit``."""

    @property
    def name(self) -> str:
        return "hphf.no_added_sugar_primary_base"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        if not draft.ingredients:
            return self._ok()
        heaviest = max(draft.ingredients, key=lambda i: i.quantity_g)
        if _is_sweetener(heaviest) and heaviest.quantity_g >= _SWEETENER_PRIMARY_MIN_G:
            return self._fail([
                f"Added sweetener is the primary ingredient by weight: \"{heaviest.name}\" "
                f"({heaviest.quantity_g:g} g). The recipe reads as a sugar-delivery vehicle — build it "
                f"on a protein / vegetable / whole-grain base and use sweeteners only in a small amount."
            ])
        return self._ok()


class NoDeepFried(BaseDietRule):
    @property
    def name(self) -> str:
        return "hphf.no_deep_fried"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        for step in draft.instructions:
            if _has_kw(step.lower(), _DEEP_FRY_KW):
                return self._fail([
                    "The recipe involves deep-frying (a bath of oil). Use the oven, the stovetop with a "
                    "drizzle of oil, steaming, broiling, or poaching instead."
                ])
        for ing in draft.ingredients:
            if _has_kw(_ing_text(ing), _DEEP_FRY_OIL_KW):
                return self._fail([
                    "Ingredient \"deep-frying oil\": the recipe must not be deep-fried in a bath of oil."
                ])
        return self._ok()


class NoRefinedGrainBase(BaseDietRule):
    @property
    def name(self) -> str:
        return "hphf.no_refined_grain_base"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        for ing in draft.ingredients:
            if _has_kw(_ing_text(ing), _REFINED_GRAIN_KW) and ing.quantity_g >= _REFINED_GRAIN_MIN_G:
                return self._fail([
                    f"Refined-grain carbohydrate base: \"{ing.name}\" ({ing.quantity_g:g} g). Use a whole-grain "
                    f"version (brown rice, whole-wheat or legume pasta, whole-grain bread, whole-wheat semolina) "
                    f"or a base of legumes, vegetables, or fruit."
                ])
        return self._ok()


# ── soft per-tier rules (warnings) ──────────────────────────

class MealCategoryNutritionTargets(BaseDietRule):
    """Post-nutrition: warn (never block) when the recipe misses its chapter's tier targets."""

    def __init__(self, chapter: str) -> None:
        self.chapter = chapter
        self._env: NutrientEnvelope = load_spec().envelope_for_chapter(chapter)

    @property
    def name(self) -> str:
        return f"hphf.tier_targets[{self._env.tier}]"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        if nutrition is None:
            return self._ok()  # can't check until nutrition is computed
        env = self._env
        t = env.tier
        w: list[str] = []
        if env.protein_g_floor and nutrition.protein_g < env.protein_g_floor:
            w.append(f"protein {nutrition.protein_g:g} g/serving < floor {env.protein_g_floor:g} g (\"{t}\")")
        if env.fiber_g_floor and nutrition.fiber_g < env.fiber_g_floor:
            w.append(f"fiber {nutrition.fiber_g:g} g/serving < floor {env.fiber_g_floor:g} g (\"{t}\")")
        if env.net_carbs_g_max is not None and nutrition.net_carbs_g > env.net_carbs_g_max:
            w.append(f"net carbs {nutrition.net_carbs_g:g} g/serving > ceiling {env.net_carbs_g_max:g} g (\"{t}\")")
        if env.total_carbs_g_max is not None and nutrition.carbs_g > env.total_carbs_g_max:
            w.append(f"total carbs {nutrition.carbs_g:g} g/serving > ceiling {env.total_carbs_g_max:g} g (\"{t}\")")
        if env.sodium_mg_max is not None and nutrition.sodium_mg > env.sodium_mg_max:
            w.append(f"sodium {nutrition.sodium_mg:g} mg/serving > ceiling {env.sodium_mg_max:g} mg (\"{t}\")")
        if (
            env.saturated_fat_g_max is not None
            and nutrition.saturated_fat_g is not None
            and nutrition.saturated_fat_g > env.saturated_fat_g_max
        ):
            w.append(
                f"saturated fat {nutrition.saturated_fat_g:g} g/serving > ceiling "
                f"{env.saturated_fat_g_max:g} g (\"{t}\")"
            )
        if env.energy_kcal_min is not None and nutrition.calories_kcal < env.energy_kcal_min:
            w.append(f"{nutrition.calories_kcal:g} kcal/serving < low bound {env.energy_kcal_min:g} kcal (\"{t}\")")
        if env.energy_kcal_max is not None and nutrition.calories_kcal > env.energy_kcal_max:
            w.append(f"{nutrition.calories_kcal:g} kcal/serving > high bound {env.energy_kcal_max:g} kcal (\"{t}\")")
        return self._ok(warnings=w)


class AddedSugarLimit(BaseDietRule):
    """Added-sugar ceiling. Prefers the LLM-estimated ``NutritionInfo.added_sugar_g`` when
    available; otherwise falls back to a structural proxy (sum of added-sweetener ingredient
    grams) — ``NutritionInfo.sugar_g`` is *total* sugars, not *added*, so it can't substitute."""

    def __init__(self, chapter: str) -> None:
        self.chapter = chapter
        self._env: NutrientEnvelope = load_spec().envelope_for_chapter(chapter)

    @property
    def name(self) -> str:
        return f"hphf.added_sugar[{self._env.tier}]"

    def evaluate(self, draft: RecipeDraft, nutrition: NutritionInfo | None = None) -> RuleResult:
        cap = self._env.added_sugar_g_max
        if cap is None:
            return self._ok()
        if nutrition is not None and nutrition.added_sugar_g is not None:
            per_serving = nutrition.added_sugar_g
            note = ""
        else:
            total = 0.0
            for ing in draft.ingredients:
                if _is_sweetener(ing):
                    total += ing.quantity_g
            per_serving = total / 2.0  # recipe serves 2
            note = f" (estimated from sweetener grams: {total:g} g total)"
        if per_serving > cap:
            return self._ok(warnings=[
                f"added sugar ≈ {per_serving:g} g/serving{note} > ceiling {cap:g} g (\"{self._env.tier}\")"
            ])
        return self._ok()


# ── registry ────────────────────────────────────────────────

# Chapter-agnostic — stateless and reused across DietRuleEngine instances.
_HARD_BLOCK_RULES: tuple[BaseDietRule, ...] = (
    NoProcessedCuredMeatBase(),
    NoSugarSweetenedBeverageComponent(),
    NoAddedSugarPrimaryBase(),
    NoDeepFried(),
    NoRefinedGrainBase(),
)


def build_rules(chapter: str = "quick_easy_dinners") -> list[BaseDietRule]:
    """The high-protein high-fiber rule set for ``chapter``: the (chapter-agnostic) hard blocks
    plus the chapter's per-tier soft checks."""
    return [
        *_HARD_BLOCK_RULES,
        MealCategoryNutritionTargets(chapter),
        AddedSugarLimit(chapter),
    ]
