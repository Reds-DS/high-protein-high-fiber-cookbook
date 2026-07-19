# Stage 1 — ideation. Produces the recipe IDEA only (no quantities, no nutrition).

SYSTEM_STATIC = """\
You are a professional recipe developer for "Super Easy & Complete High-Protein High-Fiber \
Cookbook for Weight Loss" — quick, delicious, moderate-low-carb recipes for general healthy US \
adults who want to lose fat, preserve or build muscle, and stay full without hunger. The book's \
promise is clear macros on every plate and real food, never bland "diet food." Right now you \
generate only the recipe IDEA, with no ingredient quantities.

NON-NEGOTIABLE RULES:
- Every recipe serves EXACTLY 2 people. Never propose another yield.
- "Super easy": short ingredient lists (about 10 or fewer), few steps (about 7 or fewer), about 30 \
  minutes active or less, common home equipment (oven, stovetop, blender, sheet pan; NO air fryer) \
  — nothing fussy or chef-y. Frozen and pre-cut produce, rotisserie chicken, and NO-SALT-ADDED \
  canned beans / lentils / salmon / tuna are FIRST-CLASS shortcuts, EQUAL to fresh — not concessions. \
  But cap canned/jarred items at about ONE (two max) per recipe and pair them with a fresh or frozen \
  anchor: stacking several canned/cured items blows the sodium ceiling. One-pan / sheet-pan / skillet \
  / one-bowl / no-cook and meal-prep-friendly formats are welcome.
- HIGH IN PROTEIN + HIGH IN FIBER by design (this is the book's engine): a MAIN delivers ≥30 g \
  protein and ≥8 g fiber per serving; a snack ≥12 g protein and ≥3 g fiber; a dessert ≥8 g \
  protein and ≥3 g fiber. Build on lean, complete, leucine-rich proteins — skinless poultry, \
  fish & seafood (fatty fish welcome; canned salmon / sardines / tuna too), eggs & egg whites, \
  Greek yogurt, cottage cheese, tofu / tempeh / edamame, lentils and beans — plus plenty of \
  non-starchy vegetables and fiber-rich, viscous/soluble sources (oats, chia / ground flax, \
  legumes, berries).
- MODERATE LOW-CARB (never keto) with QUALITY carbs: the carbohydrate component is a whole / \
  intact grain, legume, non-starchy vegetable, or whole fruit in a measured portion — NEVER a \
  refined-grain base (white bread / rice / pasta). Low in added sugar; no sugar-sweetened-beverage \
  components.
- Use unsaturated fats (olive, canola, avocado) sparingly; keep sodium and saturated fat modest. \
  NOT heavy, greasy, or deep-fried; NO air fryer. Bake / roast / grill / steam / saute in minimal oil.
- Bold flavor, real food. On mains, aim for a plate that is about half non-starchy vegetables, a \
  quarter to a third lean protein, and up to a quarter quality carbohydrate.
- VARIETY: don't default to the same protein family or the same acid every recipe — rotate across \
  poultry, fish/seafood, eggs, dairy, tofu/tempeh, and legumes, and vary the flavor direction from \
  the recipes that already exist (see the diversity notes below).
- TITLE: short (max 8-10 words), descriptive and appetizing — the reader should understand the dish \
  from the title alone. No long subtitle.
- INTRO: 1-2 sentences maximum, concise, and varied from recipe to recipe (texture, occasion, \
  simplicity, a nutrition benefit, an original angle, etc.).
- Keep any health framing HONEST — no "fat-burning", "melts / torches fat", or "boosts / \
  supercharges metabolism" language.
- This step is the IDEA only — generate NO ingredient quantities, names only.
"""


def build_system(diet_constraint_text: str, diversity_context: str = "") -> str:
    prompt = SYSTEM_STATIC
    if diet_constraint_text:
        prompt += f"\n\nDIET RULES:\n{diet_constraint_text}"
    if diversity_context:
        prompt += f"\n{diversity_context}"
    return prompt


# Keyed by the meal-type slot (see VALID_MEAL_TYPES in src/constants.py). The
# chapter brief (built in spec.chapter_brief) gives the deeper per-chapter
# direction; this block adds an explicit format-rotation pressure on top, so the
# LLM doesn't converge on a narrow vocabulary as a chapter fills up.
MEAL_FORMAT_GUIDANCE: dict[str, str] = {
    "breakfast": (
        "BREAKFAST FORMATS — VARIETY REQUIRED:\n"
        "Don't repeat the format that already dominates the existing recipes (e.g. another bowl of "
        "overnight oats, another egg scramble).\n"
        "High-protein breakfast format ideas — every recipe should anchor on a real "
        "protein (eggs / Greek yogurt / cottage cheese / canned fish / tofu), not pastry or sweetened cereal:\n"
        "• Eggs in many forms — baked eggs, frittata, scramble, omelet, shakshuka, egg cups / muffins\n"
        "• Loaded whole-grain toasts (cottage cheese + egg, smoked salmon, ricotta + berries, tuna)\n"
        "• Pancakes & griddle cakes (oat, cottage-cheese, banana-and-egg, grated-vegetable)\n"
        "• Savory or fruit muffins (vegetables, Greek yogurt, berries, whole-grain flour)\n"
        "• Overnight oats / baked oats (rolled oats, seeds, berries, Greek yogurt or cottage cheese stir-in)\n"
        "• Greek yogurt or skyr parfaits with fruit, seeds, and a whole-grain crunch\n"
        "• Cottage-cheese plates with fruit / smoked salmon / vegetables\n"
        "• Tofu scrambles with vegetables\n"
        "• Canned-fish plates (sardines / canned salmon on whole-grain toast, with greens)\n"
        "Pick a format DIFFERENT from the recipes that already exist."
    ),
    "lunch": (
        "LUNCH FORMATS — VARIETY REQUIRED:\n"
        "Don't repeat the format that already dominates the existing recipes (e.g. another grain bowl, "
        "another chicken-and-salad).\n"
        "Plate-method-shaped lunch format ideas — about half non-starchy vegetables, a quarter lean "
        "protein, up to a quarter whole-grain / legume / starchy-wholesome carb. Make-ahead-friendly:\n"
        "• Whole-grain or legume grain bowls (quinoa / farro / brown rice / barley + protein + vegetables)\n"
        "• Big protein salads (chicken, tuna, salmon, egg, chickpea, edamame, tofu, white-bean)\n"
        "• Chunky vegetable-and-bean or lentil soups; chilis\n"
        "• Stuffed vegetables (bell pepper, sweet potato, portobello, zucchini boats)\n"
        "• Whole-grain wraps and pita pockets (hummus, tuna, chicken, turkey, falafel)\n"
        "• Plate combos — a tray of cooked vegetables + canned salmon / sardines + a whole-grain side\n"
        "• Mason-jar or make-ahead bowls (layered for take-to-work)\n"
        "• Hearty open-faced toasts on dense whole-grain bread\n"
        "Pick a format DIFFERENT from the recipes that already exist."
    ),
    "snack": (
        "SNACK FORMATS — VARIETY REQUIRED:\n"
        "Don't repeat the format that already dominates the existing recipes (e.g. another roasted-chickpea snack).\n"
        "Protein-bearing mini-meal ideas (≥12 g protein, ≥3 g fiber per serving):\n"
        "• Cottage cheese or Greek yogurt cups with fruit, seeds, and nuts\n"
        "• Vegetable sticks with hummus or a seasoned Greek-yogurt dip\n"
        "• Hard-boiled eggs with fruit or a whole-grain cracker\n"
        "• Mini meatballs (turkey, chicken, lentil)\n"
        "• Crustless mini quiches / egg cups\n"
        "• Open-faced bites (whole-grain toast + tuna / cottage cheese / smoked salmon)\n"
        "• A measured portion of nuts with fruit\n"
        "• Edamame or roasted chickpeas / fava beans\n"
        "• Mini 'protein boxes' (a few cubes of low-fat cheese + olives + vegetables + nuts)\n"
        "Pick a format DIFFERENT from the recipes that already exist."
    ),
    "dinner": (
        "DINNER FORMATS — VARIETY REQUIRED:\n"
        "Don't repeat the format that already dominates the existing recipes (e.g. another sheet-pan, "
        "another stir-fry).\n"
        "Easy weeknight dinner format ideas — plate-method-shaped, super easy (about 10 ingredients "
        "or fewer, about 30 min active, about 7 steps), set-and-forget formats welcome:\n"
        "• Sheet-pan protein + vegetables (chicken thighs, fish, tofu, salmon)\n"
        "• One-pot / Dutch-oven stews and chilis (chicken + bean, turkey, lentil, white bean)\n"
        "• Skillet sautés and stir-fries (minimal oil — brush or spray, not pour)\n"
        "• Baked, broiled, or poached fish + a vegetable side\n"
        "• Slow-cooker / pressure-cooker braises (set-and-forget)\n"
        "• Lean meatballs / mini-loaves (turkey, chicken, lentil) with a vegetable side\n"
        "• One-skillet dinners (protein + vegetables + a whole grain or legume in one pan)\n"
        "• Stuffed vegetables (peppers, sweet potatoes, eggplant)\n"
        "• Traybakes (everything roasted together on one tray)\n"
        "Pick a format DIFFERENT from the recipes that already exist."
    ),
    "dessert": (
        "DESSERT FORMATS — VARIETY REQUIRED:\n"
        "Don't repeat the format that already dominates the existing recipes (e.g. another chocolate "
        "baked dish, another fruit crumble).\n"
        "Light, low-added-sugar (≤ ~10 g added sugar / serving), protein- or fiber-bearing dessert ideas:\n"
        "• Greek-yogurt barks, mousses, or 'nice cream'\n"
        "• Ricotta or cottage-cheese whips with fruit\n"
        "• Chia or berry puddings (chia + milk or yogurt + fruit)\n"
        "• Baked or grilled fruit (apples, pears, peaches, apricots) topped with Greek yogurt\n"
        "• Dark-chocolate-and-nut bites (≥70% cocoa)\n"
        "• Light custards or clafoutis (no white sugar, lean on fruit)\n"
        "• Small portion-controlled baked goods made with whole-grain flour, oat bran, or almond flour\n"
        "• Cookies (rolled oats, nuts, dark chocolate, minimal sweetener)\n"
        "Lean on whole fruit / fruit purée for sweetness; keep added sugar to a minimum.\n"
        "Pick a format DIFFERENT from the recipes that already exist."
    ),
}


def build_user(
    main_ingredient: str | None,
    cuisine_hint: str | None,
    exclusions: list[str],
    meal_type: str = "dinner",
    chapter_brief: str = "",
) -> str:
    parts = [
        "Generate an original recipe idea with the following constraints:",
        f"- Meal type: {meal_type}",
    ]
    if main_ingredient:
        parts.append(f"- Main ingredient: {main_ingredient}")
    if cuisine_hint:
        parts.append(f"- Desired cuisine style: {cuisine_hint}")
    if exclusions:
        parts.append(f"- Ingredients to exclude (allergens or preferences): {', '.join(exclusions)}")
    if chapter_brief:
        parts.append(f"\n{chapter_brief}")
    if meal_type in MEAL_FORMAT_GUIDANCE:
        parts.append(f"\n{MEAL_FORMAT_GUIDANCE[meal_type]}")
    parts.append(
        "\nRespond in JSON per the provided schema. Generate NO quantities — ingredient names only."
    )
    return "\n".join(parts)
