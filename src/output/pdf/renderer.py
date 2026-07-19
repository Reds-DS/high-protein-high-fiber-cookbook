"""Render a MealPlan + CourseList to a professionally designed PDF.

Uses Jinja2 for templating and WeasyPrint for the HTML→PDF conversion.
The template + stylesheet live under ``assets/`` next to this module.
"""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from src.constants import MEAL_TYPE_LABELS
from src.models.meal_plan import MealPlan
from src.models.recipe import Recipe
from src.planning.personalization import ACTIVITY_LABELS, SEX_LABELS

# Month names — avoid depending on system locale inside Docker.
_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

# Recipe PNGs are 1024+ px and several MB each. In the PDF they render at
# ~9 mm (~35 px at 100 dpi) — so we downscale to a small JPEG once and cache.
_THUMB_SIZE = (160, 160)
_THUMB_QUALITY = 80
_THUMB_DIRNAME = ".thumbs"

# Larger thumbnails for recipe-book pages (~60 mm at 100 dpi).
_RECIPE_THUMB_SIZE = (400, 400)
_RECIPE_THUMB_DIRNAME = ".thumbs-recipe"


def render_to_pdf(
    plan: MealPlan,
    book_dir: Path,
    recipes_by_id: dict[str, Recipe],
) -> bytes:
    """Render the given plan (with per-week slices) into a single combined PDF.

    `book_dir` is the cookbook folder; it is used as the WeasyPrint base URL
    and to scope image-path validation. Course lists are pulled from
    `plan.weeks[i].course_list`.
    """
    from weasyprint import CSS, HTML  # imported lazily — heavy deps

    env = Environment(
        loader=PackageLoader("src.output.pdf", "assets"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("meal_plan.html.j2")

    context: dict[str, Any] = {
        "plan": plan,
        "manifest": plan.manifest,
        "meal_labels": MEAL_TYPE_LABELS,
        "activity_labels": ACTIVITY_LABELS,
        "sex_labels": SEX_LABELS,
        "generated_on": _format_date(plan.created_at),
        "image_urls": _build_image_map(plan, recipes_by_id, book_dir),
    }

    html_str = template.render(**context)

    css_text = (files("src.output.pdf.assets") / "meal_plan.css").read_text(encoding="utf-8")

    return HTML(string=html_str, base_url=str(book_dir)).write_pdf(
        stylesheets=[CSS(string=css_text, base_url=str(_assets_dir()))]
    )


# ── helpers ──────────────────────────────────────────────────────

def _assets_dir() -> Path:
    """Filesystem directory backing the assets package (for CSS base_url)."""
    return Path(str(files("src.output.pdf.assets"))).resolve()


def _format_date(dt) -> str:
    return f"{_MONTHS[dt.month]} {dt.day}, {dt.year}"


def _build_image_map(
    plan: MealPlan,
    recipes_by_id: dict[str, Recipe],
    book_dir: Path,
) -> dict[str, str | None]:
    """Resolve each plan recipe_id → cached-thumbnail URL (or None).

    Logs a warning naming any recipes used in the plan that have no usable
    image — useful for spotting which ones to regenerate.
    """
    from rich.console import Console
    book_root = book_dir.resolve()
    thumb_dir = book_root / "MealPlan" / _THUMB_DIRNAME
    thumb_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str | None] = {}
    missing_titles: list[str] = []
    for day in plan.days:
        for slot in day.slots:
            if slot.recipe_id in result:
                continue
            recipe = recipes_by_id.get(slot.recipe_id)
            url = _resolve_thumbnail(recipe, book_root, thumb_dir)
            result[slot.recipe_id] = url
            if url is None:
                missing_titles.append(slot.recipe_title)

    if missing_titles:
        console = Console()
        console.print(
            f"[yellow]Missing images for {len(missing_titles)} plan recipe(s) "
            f"(cells with no thumbnail):[/yellow]"
        )
        for t in missing_titles:
            console.print(f"[yellow]  - {t}[/yellow]")

    return result


def _resolve_thumbnail(
    recipe: Recipe | None,
    book_root: Path,
    thumb_dir: Path,
) -> str | None:
    """Return a file:// URL for a downscaled JPEG thumbnail (generate on miss)."""
    if recipe is None or not recipe.image_path:
        return None
    try:
        src = Path(recipe.image_path).resolve()
    except (OSError, ValueError):
        return None
    if not src.is_file():
        return None
    # Path-traversal guard — original image must live inside the cookbook.
    try:
        src.relative_to(book_root)
    except ValueError:
        return None

    thumb = thumb_dir / f"{recipe.id}.jpg"
    if not thumb.exists() or thumb.stat().st_mtime < src.stat().st_mtime:
        try:
            _make_thumbnail(src, thumb)
        except Exception:  # noqa: BLE001
            return None
    return thumb.as_uri()


def _make_thumbnail(src: Path, dst: Path, size: tuple[int, int] = _THUMB_SIZE) -> None:
    from PIL import Image

    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail(size, Image.Resampling.LANCZOS)
        im.save(dst, format="JPEG", quality=_THUMB_QUALITY, optimize=True)


# ── Recipe book PDF ────────────────────────────────────────────

def render_recipe_book_pdf(
    recipes: list[Recipe],
    book_dir: Path,
    section_title: str = "Desserts",
    book_name: str = "",
) -> bytes:
    """Render a list of recipes into a professionally designed PDF booklet."""
    from weasyprint import CSS, HTML

    env = Environment(
        loader=PackageLoader("src.output.pdf", "assets"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("recipe_book.html.j2")

    image_urls = _build_recipe_image_map(recipes, book_dir)

    context: dict[str, Any] = {
        "section_title": section_title,
        "book_name": book_name,
        "recipes": recipes,
        "image_urls": image_urls,
    }

    html_str = template.render(**context)
    css_text = (files("src.output.pdf.assets") / "recipe_book.css").read_text(encoding="utf-8")

    return HTML(string=html_str, base_url=str(book_dir)).write_pdf(
        stylesheets=[CSS(string=css_text, base_url=str(_assets_dir()))]
    )


def _build_recipe_image_map(
    recipes: list[Recipe],
    book_dir: Path,
) -> dict[str, str | None]:
    """Resolve each recipe.id → cached thumbnail URL for recipe-book pages."""
    from rich.console import Console

    book_root = book_dir.resolve()
    thumb_dir = book_root / "Export" / _RECIPE_THUMB_DIRNAME
    thumb_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str | None] = {}
    missing_titles: list[str] = []

    for recipe in recipes:
        url = _resolve_recipe_thumbnail(recipe, book_root, thumb_dir)
        result[recipe.id] = url
        if url is None:
            missing_titles.append(recipe.title)

    if missing_titles:
        console = Console()
        console.print(
            f"[yellow]Missing images for {len(missing_titles)} recipe(s):[/yellow]"
        )
        for t in missing_titles:
            console.print(f"[yellow]  - {t}[/yellow]")

    return result


def _resolve_recipe_thumbnail(
    recipe: Recipe,
    book_root: Path,
    thumb_dir: Path,
) -> str | None:
    """Like _resolve_thumbnail but with larger size for recipe-book pages."""
    if not recipe.image_path:
        return None
    try:
        src = Path(recipe.image_path).resolve()
    except (OSError, ValueError):
        return None
    if not src.is_file():
        return None
    try:
        src.relative_to(book_root)
    except ValueError:
        return None

    thumb = thumb_dir / f"{recipe.id}.jpg"
    if not thumb.exists() or thumb.stat().st_mtime < src.stat().st_mtime:
        try:
            _make_thumbnail(src, thumb, size=_RECIPE_THUMB_SIZE)
        except Exception:  # noqa: BLE001
            return None
    return thumb.as_uri()
