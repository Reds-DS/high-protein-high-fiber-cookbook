"""Load / save the per-cookbook manifest (`cookbook.json`)."""
from pathlib import Path

from src.diet_rules import spec
from src.models.meal_plan import CookbookManifest

MANIFEST_FILENAME = "cookbook.json"


def manifest_path(cookbook_dir: Path) -> Path:
    return cookbook_dir / MANIFEST_FILENAME


def load(cookbook_dir: Path) -> CookbookManifest:
    """Load and validate `cookbook.json` from a cookbook folder."""
    path = manifest_path(cookbook_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {path}. "
            f"Run: init-manifest --book {cookbook_dir.name}"
        )
    return CookbookManifest.model_validate_json(path.read_text(encoding="utf-8"))


def save(manifest: CookbookManifest, cookbook_dir: Path) -> Path:
    """Write manifest as pretty JSON."""
    path = manifest_path(cookbook_dir)
    path.write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    return path


def default_for(
    cookbook_name: str,
    *,
    objective: str | None = None,
    daily_kcal: int | None = None,
    diet_tags: list[str] | None = None,
) -> CookbookManifest:
    """Sensible defaults for a new cookbook, overridable by caller."""
    tags = diet_tags or []
    guessed_objective = objective or _guess_objective(cookbook_name, tags)
    return CookbookManifest(
        name=cookbook_name,
        objective=guessed_objective,
        diet_tags=tags,
        servings_per_recipe=2,
        target_daily_kcal=daily_kcal or 1800,
        kcal_tolerance=200,
        max_repeat_window_days=7,
        meal_structure=["breakfast", "lunch", "snack", "dinner"],
        recipe_targets=spec.chapter_target_counts(),
    )


def target_recipe_counts(manifest: CookbookManifest) -> dict[str, int]:
    """Per-chapter target recipe counts for this cookbook: the YAML defaults
    (``data/high_protein_high_fiber_guidelines.yaml``) overridden by anything set in the manifest's
    ``recipe_targets``."""
    return {**spec.chapter_target_counts(), **manifest.recipe_targets}


def _guess_objective(cookbook_name: str, diet_tags: list[str]) -> str:
    """Produce a friendly default objective from the book name + tags."""
    name_lc = cookbook_name.lower()
    tags = {t.lower() for t in diet_tags}
    if (
        "protein" in name_lc or "fiber" in name_lc or "fibre" in name_lc
        or "hphf" in tags or "high-protein" in tags or "high-fiber" in tags
    ):
        return (
            "60-day high-protein, high-fiber weight-loss plan for general healthy adults — "
            "lose fat, preserve muscle, and stay full without hunger, with clear per-serving macros."
        )
    return f"Meal program based on {cookbook_name}."
