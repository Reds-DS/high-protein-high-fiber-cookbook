# High-Protein High-Fiber Weight-Loss Cookbook — Recipe Guidelines (ground truth)

**Book:** *Super Easy & Complete High-Protein High-Fiber Cookbook for Weight Loss* — *100+ Quick, Delicious Low-Carb Recipes with Clear Macros to Burn Fat, Build Muscle, and Boost Metabolism — 60-Day Personalized Meal Plan and APP Included.*

**What this file is.** A working brief telling the recipe generator (and human editors) what makes a recipe *suitable* and *ideal* for this book's readers. Every nutrition/clinical claim is attributed to a public-health, clinical, or peer-reviewed authority (see **Sources**). The recipe-level per-serving numbers in §C are *derived working values* (a daily authority target divided across ~3 meals + 1–2 snacks) — flagged as derived, tuned during the diet-rules build, not treated as authority-stated thresholds. The structured distillation is `data/high_protein_high_fiber_guidelines.yaml`.

**Disclaimer.** This book is for general educational purposes only and is not individualized medical or nutritional advice. It does not diagnose, treat, or replace care from your physician or registered dietitian. Nutrition information is estimated using USDA data and may vary with ingredients, brands, and preparation. Consult a qualified healthcare professional before making significant dietary changes — especially with **chronic kidney disease** or other kidney concerns, if **pregnant or breastfeeding**, if taking **glucose-lowering (e.g., insulin/sulfonylureas) or blood-pressure medications**, or with a **history of an eating disorder**. Increase fiber gradually and drink plenty of water.

**Last reviewed:** 2026-07-08. **Re-check on next review:** the **DGA 2020-2025** is assumed here; a **2025-2030** edition released ~Jan 2026 leaves the three headline limits (added sugar / saturated fat / sodium) substantially unchanged — verify before print. Confirm the USDA FoodData Central nutrient IDs for **added sugars (1235), potassium (1092), vitamin D D2+D3 (1114)** against the live `nutrient.csv` before locking the nutrition-DB loader (they could not be fetched from a live public page during research).

---

## 1. Audience

**Primary:** general healthy US adults pursuing **fat loss with muscle preservation**, tired of hunger, bland "diet food," and manual macro math. Reader goals, straight from the cover: **lose fat, build/preserve muscle, stay full without hunger, and get the macros done for them.**

**Secondary frames:** people new to macro tracking; busy adults who want fast, simple recipes.

This is **not** a therapeutic/medical diet, **not** age-specific, and **not** medication-specific. It is a mainstream weight-loss cookbook whose engine is the **high-protein + high-fiber** combination.

### Why "high-protein + high-fiber" changes the picture

The positioning is evidence-driven, not cosmetic:

- **Protein preserves muscle in a deficit and is the most satiating macronutrient.** Above the 0.8 g/kg RDA (a deficiency floor), intakes around **1.2–1.6 g/kg/day** preserve lean mass and improve body composition during weight loss; **~25–30 g protein per meal** is the observed satiety and muscle-protein-synthesis threshold (below ~25 g/meal, satiety effects are minimal). (ISSN 2017; Leidy AJCN; Academy/DC/ACSM 2016.)
- **Fiber adds fullness and closes a real gap.** Fiber lowers dietary energy density and slows gastric emptying; **viscous/soluble fiber** (oats/β-glucan, legumes, psyllium, chia/flax, pectin fruits) has the strongest satiety signal. ~90%+ of US adults miss the fiber Adequate Intake, so a genuinely high-fiber book fills an underconsumed nutrient of public-health concern. (Academy of Nutrition & Dietetics 2015; soluble-fiber meta-analyses; IOM DRI; DGA.)
- **The protein + fiber combination is the "never starving" lever.** Together they suppress ghrelin and raise the satiety peptides GLP-1, PYY, and CCK, cutting hunger and food intake. (Steinert Physiol Rev; protein-appetite meta-analysis.)
- **Moderate low-carb (not keto) keeps carbs quality-forward.** Carbohydrate from whole/intact grains, legumes, vegetables, and fruit, with refined grains and added sugar minimized. Total calorie deficit and adherence — not carb level per se — drive durable weight loss; low-carb's early edge (water weight, appetite) attenuates over 6–12 months. (StatPearls; DIETFITS/meta-analyses; DGA.)

---

## 2. Nutrition foundations *(§A)*

### §A. General dietary frame

| # | Principle | Authority |
|---|---|---|
| A1 | **Protein for weight loss + muscle:** target **1.2–1.6 g/kg/day** in a deficit (RDA 0.8 = floor); ISSN 1.4–2.0 g/kg maintains muscle in exercisers, up to 2.3–3.1 g/kg only for lean trained dieters. | ISSN 2017; Academy/DC/ACSM 2016; Leidy AJCN |
| A2 | **Protein per meal:** ~**25–30 g** high-quality protein (≈0.25–0.4 g/kg, ~2–3 g leucine), every 3–4 h across ~3 meals + 1–2 snacks; breakfast especially is chronically under-protein. | ISSN 2017; Leidy AJCN |
| A3 | **Fiber:** aim high — FDA Daily Value **28 g**; IOM AI **14 g/1,000 kcal** (~38 g men, ~25 g women under 50). This book targets the **28–38 g/day** band. Increase gradually with fluids. | FDA DV; IOM DRI; Academy 2015; Mayo |
| A4 | **Carbohydrate — moderate low-carb + quality:** ~**26–35% of kcal** (~100–150 g total/day on a 1,500–1,800 kcal day), from whole grains, legumes, vegetables, fruit; minimize refined grains. Never keto. | StatPearls; NLA 2019; DGA |
| A5 | **Added sugars:** < **10% of calories** (FDA DV < 50 g/day). | DGA; FDA DV |
| A6 | **Saturated fat:** < **10% of calories** (FDA DV < 20 g/day); replace with unsaturated fats. | DGA; FDA DV |
| A7 | **Sodium:** < **2,300 mg/day**. | DGA; FDA DV |
| A8 | **Fish/omega-3:** ~**2 servings (≈3.5 oz cooked) of fatty fish per week**, ≥8 oz seafood/week. | AHA; DGA |
| A9 | **Weight loss is gradual:** ~**1–2 lb/week**; a 5–10% loss over ~6 months is a sound short-term goal; ~500 kcal/day deficit is an illustrative framing. Faster is not better (lean-mass risk). | CDC; NIDDK |

### §A2. What distinguishes *this* book

The deltas that make it a **high-protein high-fiber** weight-loss book rather than a generic reduced-calorie one:

- **Protein floor on every main is a headline, near-hard target** (≥30 g/serving), because that is the satiety + muscle threshold with margin — the book lives on "full, not starving" and "lose fat, not muscle."
- **Fiber floor on every main is a headline target** (≥8 g/serving), which also clears the FDA **"high fiber"** (≥5.6 g) content-claim threshold.
- **Net carbs featured as a convenience metric** alongside the full FDA panel (see §C).
- **Honest "boost metabolism" framing** (see §3) — the real, modest levers, not pseudoscience.

---

## 3. How the diet works — satiety, metabolism, and safety *(§B)*

**Satiety ("never starving").** Protein is the most satiating macronutrient; fiber lowers energy density and slows gastric emptying. Together they lower ghrelin and raise GLP-1/PYY/CCK, reducing hunger and food intake. Practical levers: ~25–30 g protein per meal and meaningful fiber per serving. (A high-protein/high-fiber preload reduced hunger vs placebo; the next-meal calorie reduction was a non-significant trend — frame as "keeps you full," not a guaranteed calorie cut.)

**"Boost metabolism" — responsibly.** Three real, modest levers exist, and the book must not overclaim:
- **Thermic effect of food (TEF):** protein burns ~**20–30%** of its calories in digestion vs ~5–10% (carb) and ~0–3% (fat). Real but modest — total-diet TEF is only ~10% of intake.
- **Muscle preservation:** protein + resistance training protect metabolically active muscle during weight loss, preventing the metabolic slowdown of losing it.
- **Appetite regulation:** protein + fiber curb hunger, aiding adherence.

**ALLOWED language:** "supports/helps maintain your metabolism," "protein has a higher thermic effect," "protein + strength training help protect calorie-burning muscle," "protein and fiber help you feel full." **BANNED:** "fat-burning foods," "melts/torches fat," "supercharge/spike your metabolism," named "metabolism-boosting" ingredients with big calorie-burn promises. (Metabolism-booster foods add only ~20–100 kcal/day.)

**Safety.** For healthy adults, protein up to ~**1.4–2.0 g/kg/day is not harmful** to kidney or bone. The key exception is **chronic kidney disease**, where protein is deliberately restricted (~0.55–0.60 g/kg/day) under clinician guidance — the book must never prescribe a CKD diet, only direct such readers to their clinician. **Increase fiber gradually** (~+5 g/day per week) with adequate fluids to avoid GI discomfort.

---

## 4. What this means for a *recipe* *(§C — the rules ground truth)*

Recipes are **fixed at 2 servings**; per-serving = one person's per-meal portion. Each constraint is tagged **`[hard]`** (reject/regenerate) or **`[soft]`** (a target; the diet-check warns). Per-serving numbers are **derived** (daily target ÷ meals) — starting points, tuned during the build. The protein and fiber floors on mains are near-hard editorially (the two headline nutrients).

**Macro envelope (per serving)**

| Nutrient | `main` (breakfast/lunch/dinner) | `snack` | `dessert` | Tag | Derived from |
|---|---|---|---|---|---|
| **Protein** | floor **≥ 30 g**, target 35 | **≥ 12 g** (aim 15–20) | **≥ 8 g** (aim 10–15) | `[soft]`, mains near-hard | A1–A2; 1.6 g/kg/day ÷ meals; MPS/satiety ~25–30 g |
| **Fiber** | floor **≥ 8 g**, target 10–12 | **≥ 3 g** (aim 4–5) | **≥ 3 g** | `[soft]`, mains near-hard | A3; ≥28 g/day ÷ meals; FDA "high fiber" ≥5.6 g |
| **Net carbs** | **≤ 30 g** | **≤ 15 g** | **≤ 15 g** | `[soft]` | A4; moderate low-carb (total − fiber) |
| **Total carbs** | **≤ 45 g** | **≤ 20 g** | **≤ 25 g** | `[soft]` | A4 |
| **Added sugar** | **≤ 6 g** | **≤ 5 g** | **≤ 10 g** | `[soft]`; **`[hard]`**: no SSB component, not a sugar-delivery vehicle | A5; <50 g/day & <10% kcal |
| **Saturated fat** | **≤ 6 g** | **≤ 3 g** | **≤ 5 g** | `[soft]`; **`[hard]`**: not built on processed/cured meat | A6; <20 g/day & <10% kcal |
| **Sodium** | **≤ 700 mg** | **≤ 350 mg** | **≤ 300 mg** | `[soft]` | A7; <2,300 mg/day ÷ meals |
| **Added culinary oil** | **≤ ~1 tbsp** unsaturated | less | — | `[soft]` | A6; unsaturated, in moderation |
| **Energy** | ~**350–500 kcal** | ~**150–250 kcal** | ~**150–250 kcal** | `[soft]` | A9; ~1,500–1,800 kcal/day plan |

**Composition & character**
- **Plate shape** `[soft]` — each `main` ≈ **½ non-starchy vegetables, ¼–⅓ lean protein, ≤¼ quality carbohydrate**.
- **Carbohydrate source** `[soft]` — whole/intact grains, legumes, vegetables, or whole fruit; **`[hard]`: not a refined-grain base** (white bread/rice/pasta).
- **Cooking** — **`[hard]`: not deep-fried, batter-and-fried, or breaded-and-fried.** `[soft]`: prefer bake/roast/grill/steam/sauté in minimal oil (no air fryer).
- **Quick & simple** `[soft]` — ≤~10 ingredients, ≤~30 min active, ≤~7 steps; one-pan/sheet-pan/no-cook formats welcome (see §7).

### Per-recipe nutrition panel *(what the pipeline computes for every recipe)*

Every recipe carries a **per-serving nutrition panel** — printed as "clear macros on every plate" (the book's headline promise) and feeding the diet-rule checks. Computed via **USDA FoodData Central** (Foundation + SR Legacy + FNDDS): the LLM picks the best-matching food per ingredient, then Python does the per-serving arithmetic — never free-form LLM estimation. The one exception is **added sugars**, which USDA does not carry for generic foods, so it is LLM-estimated from the added sweeteners.

**Hero "clear macros" (featured up front):** Calories · **Protein** · Total Carbs · **Net Carbs** · **Fiber** · Fat.

**Tier A — core** (computed, printed, drive the rules): calories `1008`, protein `1003`, total carbohydrate `1005`, dietary fiber `1079`, total fat `1004`, saturated fat `1258`, sodium `1093`, total sugars `2000`, added sugars *(LLM-estimated)*. **Net carbs** = `max(0, total carbs − fiber − sugar alcohols)` — a derived convenience metric.

**Tier B — extended** (full FDA panel): cholesterol `1253`, trans fat `1257`, potassium `1092`*, calcium `1087`, iron `1089`, vitamin D `1114`*. (`*` = verify the USDA ID before building the DB.)

**Tier C — internal/derived** (not printed): protein density (`protein_g/kcal×100`), saturated-fat % kcal.

> **On "net carbs":** it has **no legal FDA definition** and is **not endorsed by the ADA** — both count *total* carbohydrate. This book features net carbs as a clearly labeled convenience metric while always printing Total Carbohydrate + Dietary Fiber, and footnotes that readers on medication (e.g., diabetes) should count total carbs.

---

## 5. Concern → recipe-characteristic map *(§D)*

| Concern | What the recipe should do |
|---|---|
| **Hunger / "diet fatigue"** | ≥30 g protein + ≥8 g fiber per main; protein- and fiber-DENSE per calorie; bold flavor so it's repeatable |
| **Muscle loss while dieting** | ≥30 g protein per main from lean/complete sources; (front-matter) pair with resistance training 2–3×/week |
| **Carb crashes / cravings** | moderate net carbs from fiber-rich, low-glycemic sources; minimal added sugar; protein + fiber pairing |
| **"No time to cook"** | ≤~10 ingredients, ≤~30 min active, one-pan/sheet-pan/no-cook, meal-prep-friendly |
| **"Macro math is a headache"** | clear per-serving macros on every recipe (hero six up front) |
| **GI discomfort from more fiber** | increase fiber gradually; pair with fluids; favor well-tolerated viscous fibers |
| **Overclaiming metabolism** | honest framing only (§3) — no "fat-burning" language |

---

## 6. Foods — emphasize / limit / avoid

**Emphasize:** skinless poultry; fish & seafood incl. fatty fish (salmon, sardines, mackerel, trout, tuna); eggs & egg whites; nonfat/low-fat Greek yogurt, cottage cheese, low-fat dairy; tofu/tempeh/edamame; legumes (measured); non-starchy vegetables; berries & lower-sugar fruit; nuts & seeds incl. chia/ground flax; intact whole grains (oats, quinoa, barley, farro) in measured portions; unsaturated oils (olive, canola, avocado).

**Limit (small portions):** starchy vegetables & higher-sugar fruit (banana, mango, grapes, dried fruit); added sweeteners (count toward the added-sugar ceiling); full-fat dairy/butter/cream/full-fat cheese; red meat (lean cuts, modest).

**Avoid (don't build recipes on these):** sugar-sweetened beverages; refined-grain bases (white bread/rice/pasta); processed & cured meats (bacon, sausage, deli); deep-fried foods and heavy cream/cheese/butter sauces; ultra-processed snacks and pastries.

---

## 7. "Super Easy" — editorial constraints *(not a medical claim)*

From the book's positioning, kept separate from the nutrition rules:
- **≤ ~10 ingredients** (excluding salt, pepper, water, small oil).
- **≤ ~30 minutes active**, **≤ ~45 minutes total** (a few set-and-forget slow-cooker/oven recipes allowed).
- **≤ ~7 steps.**
- **Common home kitchen** (stovetop, oven, blender); **no air fryer**; no specialty gear.
- Favor **one-pan / sheet-pan / skillet / one-bowl / no-cook** and **meal-prep-friendly** formats — still written for **2 servings**. Bold flavor, real food; never bland "diet food."

---

## 8. Machine-readable storage

The structured spec is `data/high_protein_high_fiber_guidelines.yaml`, registered in `src/config.py` and loaded by `src/diet_rules/spec.py`. It carries the per-tier envelopes (`per_recipe_constraints.meal_categories`), the hard blocks, the 5 chapters (`recipe_categories`), the nutrition panel, and the pre-rendered `prompt_snippets.{ideation,drafting,critic}` injected into generation. Validate with `python <skill>/scripts/validate_spec.py data/high_protein_high_fiber_guidelines.yaml`.

---

## 9. Sources

1. **USDA & HHS.** *Dietary Guidelines for Americans, 2020-2025.* — https://www.dietaryguidelines.gov/ (added sugars <10% kcal; saturated fat <10% kcal; sodium <2,300 mg/day; fiber 14 g/1,000 kcal; ≥8 oz seafood/week; carbohydrate quality)
2. **FDA.** *Daily Value on the Nutrition and Supplement Facts Labels.* — https://www.fda.gov/food/nutrition-facts-label/daily-value-nutrition-and-supplement-facts-labels (fiber 28 g, protein 50 g, total carb 275 g, total fat 78 g, sat fat 20 g, added sugars 50 g, sodium 2,300 mg, cholesterol 300 mg, vitamin D 20 mcg, calcium 1,300 mg, iron 18 mg, potassium 4,700 mg)
3. **FDA / eCFR 21 CFR 101.9.** *Nutrition labeling of food* (mandatory panel; Total Carbohydrate; "net carbs" has no regulatory definition). — https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-101/subpart-A/section-101.9
4. **FDA / eCFR 21 CFR 101.54.** *Nutrient content claims* ("good source" 10-19% DV; "high" ≥20% DV → "high fiber" ≥5.6 g, "high protein" ≥10 g/serving). — https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-101/subpart-D/section-101.54
5. **IOM/NASEM.** *Dietary Reference Intakes — Protein* (RDA 0.8 g/kg/day; AMDR 10-35% energy). — https://www.ncbi.nlm.nih.gov/books/NBK208874/
6. **IOM/NASEM DRI — Fiber** (14 g/1,000 kcal; ~38 g men / 25 g women), via Linus Pauling Institute. — https://lpi.oregonstate.edu/mic/other-nutrients/fiber
7. **Jäger R, et al.** *ISSN Position Stand: Protein and Exercise.* J Int Soc Sports Nutr 2017. — https://pmc.ncbi.nlm.nih.gov/articles/PMC5477153/
8. **Academy of Nutrition & Dietetics, Dietitians of Canada, ACSM.** *Nutrition and Athletic Performance*, 2016. — https://pubmed.ncbi.nlm.nih.gov/26920240/
9. **Leidy HJ, et al.** *The role of protein in weight loss and maintenance.* Am J Clin Nutr. — https://ajcn.nutrition.org/article/S0002-9165(23)27427-4/fulltext
10. **Academy of Nutrition & Dietetics.** *Health Implications of Dietary Fiber*, 2015. — https://pubmed.ncbi.nlm.nih.gov/26514720/
11. **StatPearls (NIH/NCBI).** *Low-Carbohydrate Diet* (carb tiers; moderate 26-44% kcal; normal AMDR 45-65%). — https://www.ncbi.nlm.nih.gov/books/NBK537084/
12. **National Lipid Association** Nutrition & Lifestyle Task Force, 2019 (carb grams at 2,000 kcal). — https://www.sciencedirect.com/science/article/pii/S1933287419302673
13. **DIETFITS RCT + meta-analyses** (calories/adherence dominate; low-carb convergence). — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10808819/
14. **Halton TL, Hu FB.** *High protein diets, thermogenesis, satiety and weight loss: a critical review.* J Am Coll Nutr 2004 (TEF 20-30%/5-10%/0-3%). — https://www.ncbi.nlm.nih.gov/books/NBK70804/
15. **Steinert RE, et al.** *Ghrelin, CCK, GLP-1, and PYY.* Physiol Rev 2017; + protein-appetite meta-analysis (PubMed 32768415). — https://journals.physiology.org/doi/full/10.1152/physrev.00031.2014
16. **Soluble/viscous fibre & satiety:** SR & meta-analysis of RCTs (Foods 2019, PMC6352252); AJCN viscous-fiber weight effect. — https://pmc.ncbi.nlm.nih.gov/articles/PMC6352252/
17. **NKF KDOQI** *Nutrition in CKD*, 2020 (AJKD) — protein 0.55-0.60 g/kg/day in CKD under clinician guidance. — https://www.ajkd.org/article/S0272-6386(20)30726-5/fulltext
18. **CDC / NIH-NIDDK** — gradual weight loss ~1-2 lb/week; 5-10% over ~6 months. — https://www.cdc.gov/healthy-weight-growth/losing-weight/index.html
19. **USDA FoodData Central** (Foundation + SR Legacy + FNDDS; per-100 g; no added-sugars for generic foods). — https://fdc.nal.usda.gov/
20. **American Heart Association.** *Fish and Omega-3 Fatty Acids* (2 servings/week fatty fish). — https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/fats/fish-and-omega-3-fatty-acids
21. **Mayo Clinic.** *Healthy cooking basics* & *high-fiber foods* (methods; gradual fiber + fluids). — https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/basics/healthy-cooking/hlv-20049477

> **Access note:** a few publisher/government pages (some FDA, ADA, DGA URLs) returned access errors to the automated fetcher during research; those figures were cross-checked against a second authority (eCFR, PMC summaries, Linus Pauling Institute, StatPearls) and are well-established. Re-confirm exact wording against the primary documents, and verify USDA nutrient IDs 1235/1092/1114 against the live `nutrient.csv`, before final print/build.
