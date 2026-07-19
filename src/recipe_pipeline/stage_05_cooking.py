"""
Stage 5 — Cooking-logic & editorial validation (deterministic, no LLM).

Four advisory checks (warnings only — none blocks; the v2 air-fryer settings validator
was removed when the codebase was repurposed for the high-protein high-fiber book):

  * per-serving quantity plausibility — ``src/cooking/quantity_checker.py``;
  * cooking-process sanity (heavy/greasy preparation, implausible oven temperature) —
    ``src/cooking/method_checker.check_cooking_method``;
  * "super easy" overshoot (too many meaningful ingredients, too long) —
    ``src/cooking/method_checker.check_super_easy``;
  * ambiguous grain base (a carb base that doesn't say whether it's a whole grain) —
    ``src/cooking/method_checker.check_grain_base``.

All four feed the orchestrator's aggregate ``validation_warnings`` and the ``cooking`` log entry.
"""
from src.cooking.method_checker import check_cooking_method, check_grain_base, check_super_easy
from src.cooking.quantity_checker import check_quantities
from src.models.recipe import RecipeDraft


def run(draft: RecipeDraft) -> tuple[RecipeDraft, list[str], list[str]]:
    """Return (draft, warnings, corrections).

    `corrections` is always empty for now (kept for signature compatibility with the
    orchestrator); the draft is returned unchanged.
    """
    qty_result = check_quantities(draft)
    method_result = check_cooking_method(draft)
    easy_result = check_super_easy(draft)
    grain_result = check_grain_base(draft)
    warnings = [
        *qty_result.warnings,
        *method_result.warnings,
        *easy_result.warnings,
        *grain_result.warnings,
    ]
    return draft, warnings, []
