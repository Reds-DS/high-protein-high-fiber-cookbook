# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **spec-driven AI system that generates the recipes for one specific cookbook**: *"Super Easy &
Complete High-Protein High-Fiber Cookbook for Weight Loss."* It is not a general recipe app — every
rule, threshold, and prompt is tuned to that book. It also builds a 60-day personalized meal plan and
emits print/InDesign-ready output. (The engine was adapted from a prior GLP-1/over-50 cookbook; that
migration is complete, but occasional stale wording may still surface.)

## Commands

Python 3.12, managed with **`uv`**. Run everything through `uv run`.

```bash
uv sync                              # install deps (creates .venv)
uv run pytest -q                     # full test suite (no network/LLM — stubs only)
uv run pytest tests/test_recipe_pipeline.py::TestQuantityCheck::test_clean_default_draft_passes  # single test
uv run ruff check .                  # lint (line-length 100; select E,F,I,UP)
uv run mypy src                      # type-check (strict; note: pre-existing errors exist, not clean)
uv run python cli.py --help          # CLI entry point (Typer); all operator commands live here
```

**Windows gotcha:** the CLI prints rich `✓`/`⚠` glyphs. When stdout is piped/redirected (not a TTY),
cp1252 encoding makes them crash with `UnicodeEncodeError`. Prefix long/back-grounded runs with
`PYTHONIOENCODING=utf-8`. It renders fine in an interactive terminal.

### End-to-end operator workflow (order matters)

```bash
# 1. Build the nutrition DB (one-time). Needs the USDA FoodData Central "Full Download / All Foods"
#    CSV bundle unzipped into usda_source_data/ (either directly or in a FoodData_Central_csv_*/ subdir).
uv run python cli.py build-nutrition-db          # -> data/usda.db (+ FTS5), data/usda_alias.db

# 2. Set an API key in .env  (GOOGLE_API_KEY default provider, or ANTHROPIC_API_KEY)

# 3. Generate recipes into data/generated_recipes/<book>/<MealTypeFolder>/{Md,JSON,IMG,LOG}/
uv run python cli.py generate --chapter quick_easy_dinners            # one recipe
uv run python cli.py generate --distribution "20 high_protein_breakfasts, 24 satisfying_lunches, \
  26 quick_easy_dinners, 18 protein_packed_snacks, 14 guilt_free_desserts" --book default
#   --no-image skips Stage 7 (fast). --review pauses after ideation -> generate-resume <run_id>.

# 4. Images for already-saved recipes (no re-generation)
uv run python cli.py regenerate-missing-images --book default

# 5. Meal plan (AFTER recipes exist)
uv run python cli.py init-manifest --book default
uv run python cli.py meal-plan --book default --days 60

# 6. Export
uv run python cli.py export-recipes-pdf --book default    # also: export-book, recompute-nutrition
```

## The spec is the source of truth

`data/high_protein_high_fiber_guidelines.yaml` (companion prose: `docs/high_protein_high_fiber_guidelines.md`)
is loaded once, cached, by `src/diet_rules/spec.py` (`load_spec()`). It defines:

- **per-tier nutrient envelopes** (`per_recipe_constraints.meal_categories`: `main` / `snack` / `dessert`),
- **hard blocks** (no deep-fry / refined-grain base / sugar-sweetened-beverage / sugar-delivery-vehicle / cured-meat base),
- the **5 chapters** (`recipe_categories`), the nutrition panel, and
- **`prompt_snippets.{ideation, drafting, critic}`** — pre-rendered text **injected into the LLM prompts**
  via `DietRuleEngine.constraint_text()` / `spec.chapter_brief()`.

**To change what recipes look like, edit the YAML spec + the hard-coded role/style rules in
`src/llm/prompts/*.py` — the two are layered together at prompt-build time.** Don't scatter thresholds
into code.

### Chapters ↔ meal types ↔ nutrient tiers

Five of each, mapped in `src/constants.py`. Keep these in sync when adding/renaming a chapter:
`RECIPE_CHAPTERS`, `RECIPE_CHAPTER_MEAL_TYPES`, `RECIPE_CHAPTER_NUTRIENT_TIER`, `MEAL_TYPE_FOLDERS`,
the `recipe_categories:` keys in the YAML, and the `RecipeChapter` Literal in `src/models/recipe.py`.

| Chapter (slug) | Meal type | Tier |
|---|---|---|
| high_protein_breakfasts / satisfying_lunches / quick_easy_dinners | breakfast / lunch / dinner | `main` |
| protein_packed_snacks | snack | `snack` |
| guilt_free_desserts | dessert | `dessert` |

Every recipe is **fixed at 2 servings**; per-serving = one person's portion.

## Pipeline architecture

`src/recipe_pipeline/orchestrator.py` wires an 8-stage, LLM-per-stage pipeline with two retry loops.
Each stage is `stage_0X_*.py` and follows the same shape: a pure **`build_request()`** (returns
`system, user, max_tokens, thinking_budget`), a **`parse_response()`**, and a **`run()`**. Prompt text
lives in `src/llm/prompts/`; strict LLM output schemas in `src/llm/output_schemas.py`.

```
ideate_only():   Stage 1 ideation ── diversity/dedup retry loop (src/dedup/) ─┐
generate_from_brief():                                                        │
  ┌─ outer critic loop (x2) ──────────────────────────────────────────────┐  │
  │  ┌─ inner draft-correction loop (x2) ─┐                                │  │
  │  │ Stage 2 draft                       │                                │  │
  │  │ Stage 2b quantity plausibility      │ (cooking/quantity_checker.py)  │  │
  │  │ Stage 3a pre-nutrition diet check   │ (blocking hard-blocks only)    │  │
  │  └─────────────────────────────────────┘                                │  │
  │  Stage 4 nutrition (USDA lookup + arithmetic)                           │  │
  │  Stage 3b post-nutrition diet check (soft tier warnings)               │  │
  │  Stage 5 cooking checks (cooking/method_checker.py — advisory)          │  │
  │  Stage 5b critic (LLM, 12 dimensions; re-draft on major/critical)      │  │
  └────────────────────────────────────────────────────────────────────────┘  │
  Stage 6 format (LLM polishes prose only) → Stage 7 image (optional)          │
```

Diet **floors/ceilings are mostly SOFT** (produce warnings, recipe is kept). Only the **hard blocks**
and the quantity-plausibility gate are blocking.

## Key subsystems

- **LLM client** — `src/llm/client.py`. Provider abstraction: Google Gemini (default) or Anthropic.
  `create_message(system, user, max_tokens, thinking_budget)`. **Critical:** for Google,
  `max_output_tokens = max_tokens + thinking_budget`, and Gemini's dynamic *thinking* consumes that
  shared budget — a long JSON response (Stage 4 nutrition, Stage 5b critic) will **truncate** if
  `max_tokens` is too small. Size it generously and retry on parse failure. Model IDs are in
  `src/config.py` (`gemini-3.1-*-preview`); they are real/current for this project — do not "fix" them.

- **Nutrition** — `src/nutrition/usda_loader.py` builds `data/usda.db` (SQLite + FTS5 keyword search)
  from USDA FoodData Central CSVs, keeping only generic foods (foundation/SR-legacy/FNDDS). Stage 4
  (`stage_04_nutrition.py`): the **LLM picks the best `fdc_id`** per ingredient from a candidate
  shortlist (or returns a per-100g estimate when nothing matches); **Python does all per-serving
  arithmetic** (`value_per_100g × grams / 100`, summed, ÷2). Added sugars are always LLM-estimated
  (USDA has none for generic foods). An `alias` DB caches the LLM's pick per canonical name.
  *Coverage caveat:* if only the USDA "Foundation Foods" download is present (~469 foods), most
  ingredients fall back to LLM estimation and macros are low-confidence — the Full "All Foods" bundle
  (~13.7k foods) is the fix.

- **Diet rules** — `src/diet_rules/`. `engine.py` builds a **chapter-parameterized** rule list
  (`rules.py`) and validates a draft (+ optional nutrition) against the tier envelope and hard blocks.

- **Planning** — `src/planning/`. `meal_planner.build_plan(days=60, seed=…)` is deterministic and
  seedable; it selects from already-generated recipes per meal slot. `week_slicer.build_week_spans(days)`
  chunks any day-count into 7-day weeks (folding a short tail into the last week). `personalization.py`
  computes targets (Mifflin-St Jeor TDEE, bodyweight→protein). The meal plan is built **after** recipes
  exist and reads them from `data/generated_recipes/<book>/`.

- **Output** — `src/output/`. `formatter.py` (per-recipe Markdown/JSON), `csv_export.py` (InDesign
  text/CSV), `pdf/renderer.py` + Jinja templates. Output is written as **per-recipe files** under each
  meal-type folder — the book is not bound into a single PDF by default.

## Conventions & non-obvious rules

- `cook_time_min/max` count **active heat time only** (0 for a no-cook recipe); chilling/marinating/
  resting go in the separate `passive_time` field (e.g. `"Chill 30-45 min"`), never in cook time.
- Recipes must **not** use an air fryer (stovetop / oven / no-cook only). Oven temps are written in
  °F **and** °C; stovetop heat is a level word (medium-high…) + a sensory cue, never a numeric setpoint.
- Generated content, DBs, and the multi-GB `usda_source_data/` are git-ignored; `.env` (real keys) is
  git-ignored — only `.env.example` (placeholders) is tracked. **Exception:** the book
  `data/generated_recipes/recipes-cookbook-v1/` is deliberately tracked (see `.gitignore`) — it is the
  delivered cookbook, not scratch output. Other books (`test*`, future runs) stay ignored. Note this
  repo is public, so anything committed under that book is published.
- Tests run fully offline (LLM/USDA calls are not made); they exercise the deterministic layers
  (diet rules, quantity/cooking checks, spec loading, planner, personalization, formatters).
