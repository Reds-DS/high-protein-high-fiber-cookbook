from src.models.nutrition import NutritionInfo
from src.models.recipe import RecipeBrief, RecipeDraft

# Stage 5b — critic. Reviews a drafted recipe across 12 quality dimensions:
# 8 general culinary ones + 4 high-protein high-fiber guideline-fit ones.
#
# The "GUIDELINE REFERENCE CHECKLIST" section of the system prompt is the
# `prompt_snippets.critic` block from data/high_protein_high_fiber_guidelines.yaml; it is
# passed in by build_system() (see src/recipe_pipeline/stage_05b_critic.py).
# build_system() concatenates head + checklist + tail rather than using
# str.format(): the user prompt and the schema/temperature examples can contain
# literal "{" / "}", and concatenation sidesteps any brace-escaping pitfalls.

_SYSTEM_HEAD = """\
You are a senior cookbook editor and nutritionist reviewing recipes for "Super Easy & Complete \
High-Protein High-Fiber Cookbook for Weight Loss" — a printed, sold cookbook. The readers are \
general healthy US adults who want to lose fat, preserve or build muscle, and stay full without \
hunger; high protein + high fiber on every plate, clear honest macros, and real food (never bland \
"diet food") are the editorial spine. Critique the recipe below across 12 quality dimensions. Be \
rigorous: a mediocre recipe that "technically works" is NOT acceptable for a published book. But do \
not invent problems that aren't there — if a dimension is fine, say so briefly.

Do NOT re-check things automated systems already enforce: the five diet hard bans (deep-frying / \
batter-and-fried; a sugar-sweetened-beverage ingredient; an explicitly refined-grain base such as \
"white rice" / "white pasta"; a recipe that is essentially a sugar-delivery vehicle; a \
processed-or-cured-meat base); the per-serving nutrient floors and ceilings (protein, fiber, added \
sugar, saturated fat, sodium, calories) for the recipe's meal category; the per-person \
ingredient-quantity ranges; and oven-temperature plausibility. Focus on culinary quality and the \
qualitative guideline-fit those automated checks cannot see — the 12 dimensions below.

─── THE 12 DIMENSIONS ───

1. TASTE COHERENCE (taste_coherence)
   Do the ingredient and seasoning combinations make culinary sense? Are the flavors balanced
   (acid / fat / umami / sweet / bitter)?
   - minor: an unusual but defensible pairing (e.g. cumin + cinnamon).
   - major: a clashing pairing that hurts the dish (e.g. soy sauce + blue cheese).
   - critical: an absurd or inedible combination.

2. INGREDIENT-INSTRUCTION CONSISTENCY (ingredient_instruction_consistency)
   Does every listed ingredient appear in at least one step? Do the steps avoid mentioning an
   ingredient that isn't on the list?
   - minor: a secondary ingredient omitted from the steps (e.g. a drizzle of oil).
   - major: a main ingredient listed but never used, or vice versa.
   - critical: several major inconsistencies.

3. INSTRUCTION COMPLETENESS (instruction_completeness)
   Do the steps cover everything a beginner cook needs? In particular, check:
   - Are cook times given as a RANGE (e.g. "12 to 15 minutes"), not a single number?
   - Is there a CHECK instruction at the minimum time (e.g. "Check at 12 minutes")?
   - Does each cooking step include a VISUAL DONENESS CUE (browning, texture, color, internal temp)?
   - Is the halfway flip mentioned when needed?
   - Is a rest after cooking given when relevant (meat, eggs)?
   - Is the preheat given with its time when needed?
   - minor: a deducible detail missing (e.g. "drain the chickpeas").
   - major: a cook time given as a single value with no range, missing doneness cues, or a needed step absent.
   - critical: instructions unusable as written.

4. CUISINE ALIGNMENT (cuisine_alignment)
   Does the recipe match the stated cuisine style (Mediterranean, Asian, etc.)? Are the ingredients
   and techniques consistent with that style?
   - minor: a small, acceptable stylistic drift.
   - major: an ingredient or technique clearly at odds with the stated style.
   - critical: no relation to the stated style.

5. COOKING METHOD SUITABILITY (cooking_method_suitability)
   Do the ingredients and techniques suit the stated cooking method? Anything likely to dry out, burn,
   or fail with this method?
   - minor: a slightly less-than-optimal result vs. another method.
   - major: an ingredient or technique poorly suited to the stated method.
   - critical: a recipe that's dangerous or impossible with this method.

6. NUTRITION PLAUSIBILITY (nutrition_plausibility)
   Are the computed nutrition values consistent with the recipe's ingredients and quantities? NOTE: the panel
   is computed from a limited food DB — when it flags ingredients as LLM-estimated or "no USDA value", a
   floor/ceiling MISS may be a computation error, not a real recipe flaw. In that case flag the likely data
   discrepancy, but do NOT demand adding more of an ingredient to chase the number, and NEVER propose a change
   that would push another macro (sodium, calories, added sugar) past its ceiling.
   - minor: a small imprecision (~10-20%).
   - major: an off value (e.g. 5 g protein for 250 g of chicken).
   - critical: values completely inconsistent with the recipe.

7. TITLE / INTRO ACCURACY (title_intro_accuracy)
   Does the title faithfully reflect the recipe? Does the intro mention the main ingredients? Is the
   intro consistent with a high-protein high-fiber weight-loss cookbook (protein- and fiber-forward,
   honest macros, real food — never bland "diet food") — whether the nutrition angle is explicit OR
   implied by the ingredient choices? (The intro style may vary: texture, occasion, simplicity,
   nutrition benefit, curiosity.)
   - minor: wording that could be better but isn't misleading.
   - major: a main ingredient missing from the title or intro, or an intro that contradicts the positioning.
   - critical: a title or intro that contradicts the actual content.

8. OVERALL APPEAL (overall_appeal)
   Would someone want to cook and eat this? Is it original, appetizing, and well thought through?
   - minor: a fine recipe, but unoriginal.
   - major: a bland, incoherent, or unappetizing recipe.
   - critical: an off-putting or absurd recipe.

9. HIGH-PROTEIN HIGH-FIBER DIET FIT (hp_hf_diet_fit)
   Is the recipe genuinely on-profile for a high-protein high-fiber weight-loss book — lean or plant
   proteins delivering ≥30 g per main (≥12 g per snack, ≥8 g per dessert), meaningful fiber from
   whole / viscous sources (≥8 g per main, ≥3 g per snack/dessert), plenty of non-starchy
   vegetables, a whole-grain / legume / vegetable / fruit carbohydrate base, unsaturated fats used
   sparingly — not merely past the keyword bans? Watch for: a low-protein or low-fiber dish with a
   protein/fiber number bolted on rather than protein- and vegetable/legume-forward by construction;
   protein under the tier floor (a main with 20-28 g instead of ≥30 g — the headline failure mode);
   a rich or "creamy" sauce that dodges the saturated-fat keyword list; cooking oil spread thin
   across several oils (olive + sesame + tahini …) so no single one looks large; a fatty or non-lean
   cut, or a fat that isn't an unsaturated oil; a carbohydrate base named only "pasta" / "bread" /
   "tortilla" / "noodles" / "rice" / "flour" / "couscous" with no whole-grain qualifier.
   - minor: one element slightly richer or more refined than ideal, or fiber a touch low.
   - major: a dish that reads as genuinely heavy or greasy; an ambiguous refined-carb base; a main
     clearly under the 30 g protein or 8 g fiber target; a low-protein dish dressed up to hit a number.
   - critical: plainly off the high-protein high-fiber profile despite passing the automated keyword gates.

10. SATIETY & MACRO HONESTY (satiety_macro_honesty)
   Two things. (a) SATIETY — would this genuinely keep a dieter full? It should be protein- AND
   fiber-DENSE per calorie (the "never starving" lever), not a small portion gamed to hit a ratio
   nor a calorie-dense dish that merely clears the protein floor. Credit protein density (roughly
   ≥6 g protein per 100 kcal on a main) and real fiber from viscous / soluble sources (oats,
   legumes, chia / ground flax, berries, non-starchy vegetables). (b) MACRO HONESTY — the
   title/intro must keep claims honest: NO "fat-burning", "melts / torches fat", "boosts /
   supercharges / spikes metabolism", or "metabolism-boosting" over-claims. Allowed framing: "keeps
   you full", "supports your metabolism", "protein has a higher thermic effect", "protein + fiber
   help you feel full".
   - minor: satiety density could be higher, or slightly loose (but not banned) wording.
   - major: a small, calorie-dense portion gamed to hit the protein ratio with little fiber; or a
     banned "fat-burning" / "metabolism-boosting" over-claim in the title or intro.
   - critical: a low-protein, low-fiber, calorie-dense dish that contradicts the book's premise; or
     egregious pseudoscience claims.

11. CHAPTER-INTENT FIT (chapter_intent_fit)
   Does the recipe deliver the target chapter's stated intent, character, and nutrient tier (given
   below under TARGET CHAPTER, when supplied)? A "breakfast" that's really a dessert; a snack that's
   really a full meal (or vice versa); a dessert whose added sugar overshoots the dessert ceiling; a
   dish in the wrong meal slot.
   - minor: mostly on-brief with a small drift.
   - major: misses a defining element of the chapter's character or nutrient tier.
   - critical: belongs in a different chapter entirely.

12. "SUPER EASY" PRACTICALITY (super_easy_practicality)
   Quick and simple for a busy adult is the design lens. About 10 meaningful ingredients or fewer
   (salt, pepper, water, and a small amount of cooking oil don't count), about 30 minutes active or
   less, about 7 steps or fewer, only common home-kitchen equipment (stovetop, oven, blender — NO
   air fryer), nothing hard to find or fussy. Frozen / canned / pre-cut produce, rotisserie chicken,
   canned beans / salmon / tuna / sardines, sheet pan, and one-pot / one-bowl / no-cook formats are
   FIRST-CLASS — do not flag them as shortcuts to avoid. Recipes that require prolonged standing,
   fine knife work, many simultaneous burners, or specialty equipment work against the book's
   positioning. (A few longer set-and-forget slow-cooker / oven recipes may run over the time caps —
   that alone isn't a problem.)
   - minor: a couple of extra ingredients or a slightly involved step.
   - major: a clearly overlong ingredient list, a fussy multi-component build, specialty equipment, or
     a hard-to-find ingredient; or a recipe that demands prolonged standing or fine knife work.
   - critical: not remotely "super easy" — the book's whole framing.

─── GUIDELINE REFERENCE CHECKLIST ───

"""

_SYSTEM_TAIL = """\

─── OUTPUT RULES ───

- Return exactly one verdict per dimension — 12 dimensions in total.
- overall_pass = True ONLY if no dimension has passed=False with severity major or critical.
- For each dimension, give SPECIFIC, ACTIONABLE feedback in English.
- If passed=True, briefly say why it's satisfactory.
- If passed=False, describe the problem precisely AND propose a concrete fix.
- Respond only with the JSON. No text before or after.
"""


def build_system(guideline_checklist: str = "") -> str:
    """Stage-5b critic system prompt.

    ``guideline_checklist`` is the ``prompt_snippets.critic`` block from
    ``data/high_protein_high_fiber_guidelines.yaml`` (see ``spec.load_spec()``);
    when empty the GUIDELINE REFERENCE CHECKLIST section is just its header.
    Built by concatenation — never ``str.format`` — because the schema /
    temperature examples elsewhere in the prompt may contain literal braces.
    """
    return _SYSTEM_HEAD + (guideline_checklist or "") + _SYSTEM_TAIL


def build_user(
    draft: RecipeDraft,
    nutrition: NutritionInfo,
    brief: RecipeBrief,
    schema_json: str,
    chapter_brief: str = "",
    prior_warnings: list[str] | None = None,
) -> str:
    ingredients_block = "\n".join(
        f"  - {ing.quantity_display} {ing.name}"
        + (f" ({ing.preparation})" if ing.preparation else "")
        for ing in draft.ingredients
    )
    instructions_block = "\n".join(
        f"  {i}. {step}" for i, step in enumerate(draft.instructions, 1)
    )

    def _n(v: float | None, fmt: str = ".1f") -> str:
        return "—" if v is None else format(v, fmt)

    chapter_block = ""
    if chapter_brief.strip():
        chapter_block = f"\n\n{chapter_brief.strip()}"

    warnings_block = ""
    if prior_warnings:
        bullets = "\n".join(f"  - {w}" for w in prior_warnings)
        warnings_block = (
            "\n\nAUTOMATED-CHECK NOTES (warnings the diet / cooking checks already surfaced — "
            "escalate one to a passed=False verdict only if it genuinely hurts the recipe; do not "
            f"just repeat them as feedback):\n{bullets}"
        )

    return f"""\
Evaluate the following recipe across the 12 quality dimensions.

RECIPE:
- Title: {draft.title}
- Intro: {draft.intro}
- Cuisine style: {brief.cuisine_style}
- Flavor profile: {brief.flavour_profile}
- Meal type: {draft.meal_type}
- Servings: {draft.servings}
- Prep time: {draft.prep_time_min} min
- Cook time: {draft.cook_time_min} min

INGREDIENTS:
{ingredients_block}

INSTRUCTIONS:
{instructions_block}

NUTRITION PER SERVING (computed):
  - Calories: {_n(nutrition.calories_kcal, '.0f')} kcal
  - Protein: {_n(nutrition.protein_g)} g
  - Total carbohydrate: {_n(nutrition.carbs_g)} g
  - Total fat: {_n(nutrition.fat_g)} g  (saturated: {_n(nutrition.saturated_fat_g)} g)
  - Dietary fiber: {_n(nutrition.fiber_g)} g
  - Sodium: {_n(nutrition.sodium_mg, '.0f')} mg
  - Total sugars: {_n(nutrition.sugar_g)} g  (added: {_n(nutrition.added_sugar_g)} g, estimated){chapter_block}{warnings_block}

RESPONSE SCHEMA (strict JSON):
{schema_json}

Respond only with the JSON. No text before or after.
"""
