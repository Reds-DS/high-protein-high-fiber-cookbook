"""Integration-style tests for pipeline stages — no LLM or API calls."""
import pytest
from pydantic import ValidationError

from src.cooking.method_checker import check_everyday_ingredients, check_grain_base, check_super_easy
from src.cooking.quantity_checker import _classify, build_correction_prompt, check_quantities
from src.diet_rules import spec
from src.llm.output_schemas import CriticDimensionVerdict, CriticOutput
from src.llm.prompts import critic as critic_prompts
from src.models.nutrition import NutritionInfo
from src.models.recipe import Ingredient, RecipeBrief, RecipeDraft
from src.recipe_pipeline import stage_03_diet_check, stage_05b_critic


def _make_draft(**overrides) -> RecipeDraft:
    base: dict = dict(
        title="Roast chicken with vegetables",
        intro="A simple, filling plate.",
        meal_type="dinner",
        servings=2,
        prep_time_min=10,
        cook_time_min=20,
        cook_time_max_min=25,
        ingredients=[
            Ingredient(
                name="chicken breast", canonical_name="chicken breast",
                quantity_g=300, quantity_display="300 g",
                nutrition_source="missing",
            ),
            Ingredient(
                name="zucchini", canonical_name="zucchini",
                quantity_g=250, quantity_display="250 g",
                nutrition_source="missing",
            ),
        ],
        instructions=["Prep the ingredients.", "Cook.", "Serve."],
    )
    base.update(overrides)
    return RecipeDraft(**base)


def _nutrition(**overrides) -> NutritionInfo:
    base: dict = dict(
        calories_kcal=420, protein_g=28, carbs_g=30, fat_g=14, fiber_g=6,
        sodium_mg=300, sugar_g=5, source="llm_usda", confidence="high",
    )
    base.update(overrides)
    return NutritionInfo(**base)


class TestDietCheckStage:
    """The high-protein high-fiber diet engine (src/diet_rules/): structural hard blocks (run pre- and
    post-nutrition) plus, once nutrition is attached, per-chapter nutrient-tier warnings.
    A plain chicken-and-zucchini draft trips no hard block, so it passes."""

    def test_pre_nutrition_passes_clean_draft(self):
        report = stage_03_diet_check.run_pre_nutrition(_make_draft())
        assert report.overall_passed
        assert report.blocking_violations == []

    def test_post_nutrition_passes_clean_draft(self):
        report = stage_03_diet_check.run_post_nutrition(_make_draft())
        assert report.overall_passed
        assert report.blocking_violations == []

    def test_processed_meat_base_is_blocked(self):
        draft = _make_draft(ingredients=[
            Ingredient(name="smoked bacon", canonical_name="bacon", quantity_g=200,
                       quantity_display="200 g", nutrition_source="missing"),
            Ingredient(name="onion", canonical_name="onion", quantity_g=120,
                       quantity_display="120 g", nutrition_source="missing"),
        ])
        report = stage_03_diet_check.run_pre_nutrition(draft)
        assert not report.overall_passed
        assert report.blocking_violations  # non-empty

    def test_low_protein_warns_post_nutrition(self):
        # the default chapter maps to the `main` tier → protein floor 30 g/serving
        # (the ~25-30 g per-meal muscle-protein-synthesis + satiety threshold, with margin)
        report = stage_03_diet_check.run_post_nutrition(
            _make_draft(), _nutrition(protein_g=8)
        )
        assert report.overall_passed  # soft target → a warning, not a blocker
        assert any("protein" in w.lower() for w in report.warnings)

    def test_high_saturated_fat_warns_post_nutrition(self):
        # `main` tier saturated_fat_g_max = 6 g/serving
        report = stage_03_diet_check.run_post_nutrition(
            _make_draft(), _nutrition(saturated_fat_g=12)
        )
        assert report.overall_passed  # soft
        assert any("saturated fat" in w.lower() for w in report.warnings)

    def test_high_added_sugar_warns_for_dessert(self):
        # `dessert` tier added_sugar_g_max = 10 g/serving
        draft = _make_draft(chapter="guilt_free_desserts", meal_type="dessert")
        report = stage_03_diet_check.run_post_nutrition(draft, _nutrition(added_sugar_g=20))
        assert report.overall_passed  # soft
        assert any("added sugar" in w.lower() for w in report.warnings)

    def test_added_sugar_proxy_from_sweetener_when_not_computed(self):
        # No computed added_sugar_g → fall back to the added-sweetener ingredient-gram proxy.
        draft = _make_draft(
            chapter="guilt_free_desserts", meal_type="dessert",
            ingredients=[
                Ingredient(name="rolled oats", canonical_name="rolled oats", quantity_g=120,
                           quantity_display="120 g", nutrition_source="missing"),
                Ingredient(name="sugar", canonical_name="sugar", quantity_g=80,
                           quantity_display="80 g", nutrition_source="missing"),
            ],
        )
        report = stage_03_diet_check.run_post_nutrition(draft, _nutrition(added_sugar_g=None))
        # 80 g sweetener / 2 servings = 40 g/serving > 10 g ceiling.
        assert report.overall_passed
        assert any("estimated from sweetener" in w.lower() for w in report.warnings)

    def test_correction_prompt_is_a_string(self):
        report = stage_03_diet_check.run_pre_nutrition(_make_draft())
        prompt = stage_03_diet_check.build_correction_prompt(report)
        assert isinstance(prompt, str)
        assert "Required corrections" in prompt


class TestServingsConstraint:
    def test_servings_always_2(self):
        assert _make_draft().servings == 2

    def test_cannot_set_servings_to_4(self):
        """The Literal[2] type prevents setting servings to any other value."""
        with pytest.raises(Exception):
            _make_draft(servings=4)


# ---------------------------------------------------------------------------
# Guideline-fit critic (Stage 5b) — schema, prompt builders, parsing
# ---------------------------------------------------------------------------

_NEW_CRITIC_DIMENSIONS = (
    "hp_hf_diet_fit", "satiety_macro_honesty", "chapter_intent_fit", "super_easy_practicality",
)


def _brief(**overrides) -> RecipeBrief:
    base: dict = dict(
        title_candidate="Roast chicken with vegetables",
        main_ingredient="chicken breast",
        cuisine_style="classic American",
        technique="roasting",
        flavour_profile="savory, lemony",
        ingredients_sketch=["chicken breast", "zucchini", "lemon", "olive oil"],
        unique_angle="one-pan weeknight dinner",
        forbidden_items=[],
        meal_type="dinner",
        chapter="quick_easy_dinners",
    )
    base.update(overrides)
    return RecipeBrief(**base)


def _dims(n: int, *, one_failing_major: bool = False) -> list[CriticDimensionVerdict]:
    out: list[CriticDimensionVerdict] = []
    for i in range(n):
        if one_failing_major and i == 0:
            out.append(CriticDimensionVerdict(
                dimension="hp_hf_diet_fit", passed=False, severity="major",
                feedback="The sauce reads as rich/creamy despite dodging the keyword list.",
            ))
        else:
            out.append(CriticDimensionVerdict(
                dimension=f"dim_{i}", passed=True, severity="minor", feedback="Fine.",
            ))
    return out


class TestGuidelineSpec:
    def test_prompt_snippets_has_critic_and_no_dead_key(self):
        s = spec.load_spec()
        assert s.prompt_snippets.get("critic", "").strip()
        assert "diet_check_summary" not in s.prompt_snippets
        assert sorted(s.prompt_snippets) == ["critic", "drafting", "ideation"]

    def test_schema_version_is_current(self):
        # Bump this when the YAML schema_version changes. Current: 1
        # (the high-protein high-fiber spec was authored fresh at schema_version 1 —
        # see data/high_protein_high_fiber_guidelines.yaml meta.schema_version).
        assert spec.load_spec().schema_version == 1


class TestCriticPromptBuilders:
    def test_build_system_includes_12_dimensions_and_checklist(self):
        checklist = spec.load_spec().prompt_snippets["critic"]
        built = critic_prompts.build_system(checklist)
        assert "12" in built
        for name in _NEW_CRITIC_DIMENSIONS:
            assert name in built
        # The checklist is concatenated verbatim — a representative line should appear.
        assert "hp_hf_fit" in built
        # No unfilled template placeholder (build_system uses concatenation, not str.format).
        assert "{" not in built

    def test_build_system_works_without_checklist(self):
        built = critic_prompts.build_system()
        assert "THE 12 DIMENSIONS" in built
        assert "OUTPUT RULES" in built

    def test_build_user_includes_chapter_brief_and_prior_warnings(self):
        draft = _make_draft()
        nutrition = _nutrition()
        user = critic_prompts.build_user(
            draft, nutrition, _brief(), schema_json="{}",
            chapter_brief="TARGET CHAPTER: Super Simple Weeknight Dinners (made up).",
            prior_warnings=["protein below the meal-category floor", "carb base looks ambiguous"],
        )
        assert "TARGET CHAPTER: Super Simple Weeknight Dinners (made up)." in user
        assert "protein below the meal-category floor" in user
        assert "carb base looks ambiguous" in user
        assert "AUTOMATED-CHECK NOTES" in user

    def test_build_user_omits_blocks_when_empty(self):
        user = critic_prompts.build_user(_make_draft(), _nutrition(), _brief(), schema_json="{}")
        assert "TARGET CHAPTER" not in user
        assert "AUTOMATED-CHECK NOTES" not in user


class TestCriticOutputSchema:
    @pytest.mark.parametrize("n", [8, 12, 14])
    def test_accepts_8_to_14_dimensions(self, n):
        out = CriticOutput(overall_pass=True, dimensions=_dims(n), summary="ok")
        assert len(out.dimensions) == n

    @pytest.mark.parametrize("n", [7, 15])
    def test_rejects_out_of_range_dimension_counts(self, n):
        with pytest.raises(ValidationError):
            CriticOutput(overall_pass=True, dimensions=_dims(n), summary="ok")


class TestCriticParseResponse:
    def test_twelve_dims_one_major_failure_is_blocking(self):
        out = CriticOutput(
            overall_pass=False, dimensions=_dims(12, one_failing_major=True), summary="needs work",
        )
        result = stage_05b_critic.parse_response(out.model_dump_json())
        assert result.passed is False
        assert len(result.blocking_feedback) == 1
        assert "hp_hf_diet_fit" in result.blocking_feedback[0]

    def test_all_passing_dims_is_not_blocking(self):
        out = CriticOutput(overall_pass=True, dimensions=_dims(12), summary="great")
        result = stage_05b_critic.parse_response(out.model_dump_json())
        assert result.passed is True
        assert result.blocking_feedback == []

    def test_minor_only_failure_is_a_warning_not_blocking(self):
        dims = _dims(12)
        dims[3] = CriticDimensionVerdict(
            dimension="overall_appeal", passed=False, severity="minor", feedback="A touch plain.",
        )
        out = CriticOutput(overall_pass=True, dimensions=dims, summary="fine, minor nit")
        result = stage_05b_critic.parse_response(out.model_dump_json())
        assert result.passed is True
        assert result.blocking_feedback == []
        assert any("overall_appeal" in w for w in result.warnings)


class TestCriticBuildRequest:
    def test_user_prompt_carries_the_target_chapter_title(self):
        book_title = spec.load_spec().category("protein_packed_snacks").book_title
        system, user, max_tokens, thinking_budget = stage_05b_critic.build_request(
            _make_draft(chapter="protein_packed_snacks", meal_type="snack"),
            _nutrition(),
            _brief(chapter="protein_packed_snacks", meal_type="snack"),
            chapter="protein_packed_snacks",
        )
        assert book_title in user
        assert "12" in system
        assert max_tokens == 6144 and thinking_budget == 4000


# ---------------------------------------------------------------------------
# Deterministic Stage-5 advisory checks (super-easy overshoot, ambiguous grain base)
# ---------------------------------------------------------------------------

def _ing(name: str, grams: float) -> Ingredient:
    return Ingredient(
        name=name, canonical_name=name, quantity_g=grams,
        quantity_display=f"{grams:g} g", nutrition_source="missing",
    )


class TestSuperEasyCheck:
    def test_long_ingredient_list_warns(self):
        many = [_ing(f"vegetable {i}", 40) for i in range(14)]
        warnings = check_super_easy(_make_draft(ingredients=many)).warnings
        assert any("ingredient" in w.lower() for w in warnings)

    def test_freebies_and_small_oil_do_not_count(self):
        # 12 "meaningful" + salt + pepper + water + 5 g oil = 16 listed, 12 meaningful → no warning.
        ings = [_ing(f"vegetable {i}", 40) for i in range(12)]
        ings += [_ing("salt", 3), _ing("black pepper", 1), _ing("water", 60), _ing("olive oil", 5)]
        assert check_super_easy(_make_draft(ingredients=ings)).warnings == []

    def test_long_prep_time_warns(self):
        warnings = check_super_easy(_make_draft(prep_time_min=40)).warnings
        assert any("active time" in w.lower() for w in warnings)

    def test_long_total_time_warns_but_set_and_forget_is_exempt(self):
        long_draft = _make_draft(prep_time_min=15, cook_time_min=55, cook_time_max_min=65)
        assert check_super_easy(long_draft).warnings  # 15 + 65 = 80 min, no set-and-forget cue
        slow = _make_draft(
            prep_time_min=15, cook_time_min=180, cook_time_max_min=240,
            instructions=["Brown the meat.", "Transfer to the slow cooker and cook on low.", "Serve."],
        )
        assert not any("total time" in w.lower() for w in check_super_easy(slow).warnings)

    def test_clean_small_draft_has_no_warnings(self):
        assert check_super_easy(_make_draft()).warnings == []


class TestEverydayIngredientsCheck:
    @pytest.mark.parametrize("name", [
        "nutritional yeast", "coconut aminos", "psyllium husk", "vital wheat gluten",
        "seitan", "teff flour", "powdered peanut butter",
    ])
    def test_specialty_ingredient_flagged(self, name):
        draft = _make_draft(ingredients=[_ing(name, 20), _ing("chicken breast", 300)])
        warnings = check_everyday_ingredients(draft).warnings
        assert warnings and name.split()[0] in warnings[0].lower()

    def test_common_ingredients_pass(self):
        # chicken + zucchini (the default draft) are supermarket staples
        assert check_everyday_ingredients(_make_draft()).warnings == []


class TestGrainBaseCheck:
    def test_bare_pasta_warns(self):
        draft = _make_draft(ingredients=[_ing("pasta", 120), _ing("tomato", 200)])
        warnings = check_grain_base(draft).warnings
        assert len(warnings) == 1
        assert "whole grain" in warnings[0].lower()

    @pytest.mark.parametrize("name", ["whole-wheat pasta", "brown rice", "100% whole-grain tortilla"])
    def test_qualified_grain_base_is_fine(self, name):
        draft = _make_draft(ingredients=[_ing(name, 120), _ing("tomato", 200)])
        assert check_grain_base(draft).warnings == []

    def test_small_amount_below_floor_is_ignored(self):
        # 30 g total (<50 g) → a garnish, not a carb base.
        draft = _make_draft(ingredients=[_ing("pasta", 30), _ing("chicken breast", 300)])
        assert check_grain_base(draft).warnings == []

    def test_non_grain_ingredient_does_not_match(self):
        assert check_grain_base(_make_draft()).warnings == []  # chicken + zucchini


# ---------------------------------------------------------------------------
# Stage-2b quantity plausibility — tier-keyed bounds + classification
# ---------------------------------------------------------------------------

class TestQuantityClassify:
    @pytest.mark.parametrize("name", [
        "large eggs", "egg whites", "plain greek yogurt", "low-fat cottage cheese",
        "halibut fillet", "canned cannellini beans", "edamame", "ground chicken",
    ])
    def test_protein_sources_classify_as_protein(self, name):
        assert _classify(_ing(name, 100)) == "protein"

    def test_eggplant_is_not_protein(self):
        # The word-boundary fix: "egg" must not match inside "eggplant".
        assert _classify(_ing("eggplant", 200)) is None

    def test_fats_classify_as_oil(self):
        assert _classify(_ing("extra-virgin olive oil", 14)) == "oil"
        assert _classify(_ing("natural peanut butter", 30)) == "oil"  # fat-dominant → oil, not protein

    def test_salty_condiments_classify_as_salt(self):
        assert _classify(_ing("low-sodium soy sauce", 30)) == "salt"
        assert _classify(_ing("kosher salt", 4)) == "salt"

    def test_plain_vegetable_classifies_as_none(self):
        assert _classify(_ing("zucchini", 200)) is None

    def test_no_salt_added_items_are_not_salt(self):
        # "no-salt-added" / "salt-free" ingredients must not be misread as a salt source (the word
        # "salt" is only a negation) — else the sodium-conscious naming trips the flat salt cap.
        assert _classify(_ing("no-salt-added diced tomatoes", 200)) is None
        assert _classify(_ing("salt-free roasted red peppers", 80)) is None
        assert _classify(_ing("no-salt-added black beans", 150)) == "protein"  # beans match first
        # real salt sources still classify
        assert _classify(_ing("table salt", 5)) == "salt"
        assert _classify(_ing("low-sodium soy sauce", 30)) == "salt"


class TestQuantityCheck:
    def test_clean_default_draft_passes(self):
        result = check_quantities(_make_draft())  # 550 g total, chapter "dinner" → "main" tier
        assert result.passed is True
        assert result.warnings == []

    def test_snack_tier_uses_smaller_bounds_than_main(self):
        # 420 g total → 210 g/person: fine for the `snack` tier, but below the `main` floor.
        ings = [_ing("salmon fillet", 220), _ing("asparagus", 200)]
        snack = check_quantities(_make_draft(chapter="protein_packed_snacks", meal_type="snack", ingredients=ings))
        assert snack.passed is True
        as_main = check_quantities(_make_draft(chapter="quick_easy_dinners", meal_type="dinner", ingredients=ings))
        assert as_main.passed is False
        assert any("too low" in w.lower() for w in as_main.warnings)

    def test_four_person_recipe_is_flagged(self):
        draft = _make_draft(chapter="quick_easy_dinners", ingredients=[_ing("chicken breast", 2000), _ing("rice", 400)])
        result = check_quantities(draft)
        assert result.passed is False
        assert any("4 people" in w for w in result.warnings)

    def test_dairy_heavy_breakfast_does_not_false_positive_on_protein(self):
        ings = [_ing("plain greek yogurt", 300), _ing("cottage cheese", 150), _ing("blueberries", 100)]
        result = check_quantities(_make_draft(chapter="high_protein_breakfasts", meal_type="breakfast", ingredients=ings))
        assert result.passed is True
        assert not any("protein" in w.lower() for w in result.warnings)

    def test_excess_protein_is_flagged(self):
        draft = _make_draft(chapter="quick_easy_dinners", ingredients=[_ing("chicken breast", 900), _ing("broccoli", 200)])
        result = check_quantities(draft)
        assert result.passed is False
        assert any("suspect protein amount" in w.lower() for w in result.warnings)

    def test_high_oil_is_flagged(self):
        draft = _make_draft(ingredients=[_ing("chicken breast", 300), _ing("zucchini", 250), _ing("olive oil", 50)])
        result = check_quantities(draft)
        assert result.passed is False
        assert any("high oil" in w.lower() for w in result.warnings)

    def test_high_salt_is_flagged(self):
        draft = _make_draft(ingredients=[_ing("chicken breast", 300), _ing("zucchini", 250), _ing("table salt", 12)])
        result = check_quantities(draft)
        assert result.passed is False
        assert any("high salt" in w.lower() for w in result.warnings)

    def test_correction_prompt_mentions_two_servings(self):
        result = check_quantities(_make_draft(ingredients=[_ing("chicken breast", 200), _ing("broccoli", 50)]))
        prompt = build_correction_prompt(result)
        assert isinstance(prompt, str)
        assert "2 servings" in prompt
