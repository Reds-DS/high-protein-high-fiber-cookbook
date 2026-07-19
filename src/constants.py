"""Shared constants: meal-type keys, on-disk folder names, and book chapters.

Extracted from cli.py so code under src/planning/ can reuse them without
importing the Typer app.
"""

VALID_MEAL_TYPES: set[str] = {"breakfast", "lunch", "snack", "dinner", "dessert"}

MEAL_TYPE_FOLDERS: dict[str, str] = {
    "breakfast": "Breakfast",
    "lunch": "Lunch",
    "snack": "Snack",
    "dinner": "Dinner",
    "dessert": "Dessert",
}

MEAL_TYPE_LABELS: dict[str, str] = {
    "breakfast": "Breakfast",
    "lunch": "Lunch",
    "snack": "Snack",
    "dinner": "Dinner",
    "dessert": "Dessert",
}

# ---------------------------------------------------------------------------
# Book chapters / recipe-generation categories.
#
# Each chapter is both a section of the printed book and a generation target.
# It maps to one of the meal-type keys above so the meal planner can
# place its recipes, and to one nutrient tier in
# data/high_protein_high_fiber_guidelines.yaml -> per_recipe_constraints.meal_categories.
# Full per-chapter detail (intent, "character" brief, target recipe count)
# lives in that YAML under `recipe_categories`.
#
# Keep RECIPE_CHAPTERS in sync with the `RecipeChapter` Literal in
# src/models/recipe.py and the `recipe_categories:` keys in the YAML.
# ---------------------------------------------------------------------------
RECIPE_CHAPTERS: tuple[str, ...] = (
    "high_protein_breakfasts",
    "satisfying_lunches",
    "quick_easy_dinners",
    "protein_packed_snacks",
    "guilt_free_desserts",
)

# Dead code kept only to avoid drift — the LIVE chapter title flows from the
# YAML `recipe_categories.<slug>.book_title` via spec.load_spec(). Editing this
# map alone changes nothing the LLM sees.
RECIPE_CHAPTER_TITLES: dict[str, str] = {
    "high_protein_breakfasts": "High-Protein Breakfasts",
    "satisfying_lunches": "Satisfying Lunches",
    "quick_easy_dinners": "Quick & Easy Dinners",
    "protein_packed_snacks": "Protein-Packed Snacks",
    "guilt_free_desserts": "Guilt-Free Desserts",
}

# Planner meal-slot key(s) a chapter's recipes can occupy. Every HPHF chapter
# maps to exactly one slot.
RECIPE_CHAPTER_MEAL_TYPES: dict[str, tuple[str, ...]] = {
    "high_protein_breakfasts": ("breakfast",),
    "satisfying_lunches": ("lunch",),
    "quick_easy_dinners": ("dinner",),
    "protein_packed_snacks": ("snack",),
    "guilt_free_desserts": ("dessert",),
}

# Primary per-recipe nutrient tier (see the YAML `meal_categories`).
RECIPE_CHAPTER_NUTRIENT_TIER: dict[str, str] = {
    "high_protein_breakfasts": "main",
    "satisfying_lunches": "main",
    "quick_easy_dinners": "main",
    "protein_packed_snacks": "snack",
    "guilt_free_desserts": "dessert",
}

# Canonical chapter to assume when a planner meal-slot is given without an
# explicit chapter (the inverse of RECIPE_CHAPTER_MEAL_TYPES, one chapter per slot).
MEAL_TYPE_DEFAULT_CHAPTER: dict[str, str] = {
    "breakfast": "high_protein_breakfasts",
    "lunch": "satisfying_lunches",
    "snack": "protein_packed_snacks",
    "dinner": "quick_easy_dinners",
    "dessert": "guilt_free_desserts",
}
