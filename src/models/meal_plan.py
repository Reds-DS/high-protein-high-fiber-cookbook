"""Pydantic models for the personalized meal-plan feature (default 60 days)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.models.nutrition import NutritionInfo


MealTypeKey = Literal["breakfast", "lunch", "snack", "dinner", "dessert"]
SexKey = Literal["M", "F"]
ActivityKey = Literal["sedentary", "light", "moderate", "active", "very_active"]


class CookbookManifest(BaseModel):
    """Per-cookbook configuration for the meal-plan feature."""
    name: str
    display_name: str | None = None
    objective: str
    diet_tags: list[str] = Field(default_factory=list)
    servings_per_recipe: int = 2
    target_daily_kcal: int = Field(default=1800, gt=0)
    kcal_tolerance: int = Field(default=200, ge=0)
    max_repeat_window_days: int = Field(default=7, ge=0)
    meal_structure: list[MealTypeKey] = Field(
        default_factory=lambda: ["breakfast", "lunch", "snack", "dinner"]
    )
    meal_share: dict[MealTypeKey, float] | None = None
    # Per-chapter target recipe counts, keyed by book-chapter slug (see RECIPE_CHAPTERS in
    # src/constants.py). Empty ⇒ use the defaults from data/high_protein_high_fiber_guidelines.yaml
    # (see src.planning.manifest.target_recipe_counts).
    recipe_targets: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_meal_share(self) -> "CookbookManifest":
        if self.meal_share is None:
            return self
        missing = [mt for mt in self.meal_structure if mt not in self.meal_share]
        if missing:
            raise ValueError(
                f"meal_share is missing entries for meal_structure types: {missing}"
            )
        total = sum(self.meal_share[mt] for mt in self.meal_structure)
        if not 0.99 <= total <= 1.01:
            raise ValueError(
                f"meal_share fractions must sum to ~1.0 across meal_structure "
                f"(got {total:.3f})"
            )
        return self


class UserProfile(BaseModel):
    """Per-user biometrics + goals used to personalize a meal plan.

    Sex and activity_level are required because Mifflin-St Jeor BMR diverges
    sharply by sex (~160 kcal/day) and TDEE without an activity factor is
    meaningless.

    The pace at which `weight_kg` should move toward `target_weight_kg` can be
    set two ways:
      - `target_date`: the planner derives `weekly_loss_kg` from time-to-target
        (the natural input — what the user really wants).
      - `weekly_loss_kg`: an explicit rate (used when no `target_date` is set).
    Sign of `weekly_loss_kg` must agree with `target_weight_kg − weight_kg`
    (positive = lose weight, negative = gain).
    """
    name: str
    sex: SexKey
    age: int = Field(gt=0, lt=120)
    height_cm: float = Field(gt=80, lt=250)
    weight_kg: float = Field(gt=25, lt=300)
    target_weight_kg: float = Field(gt=25, lt=300)
    activity_level: ActivityKey
    weekly_loss_kg: float | None = Field(default=None, ge=-1.0, le=1.0)
    target_date: date | None = None
    per_meal_kcal_cap_pct: float = Field(default=1.15, ge=1.0, le=2.0)

    @model_validator(mode="after")
    def _validate_pace(self) -> "UserProfile":
        if self.target_date is None and self.weekly_loss_kg is None:
            # Neither set → fall back to a maintenance default of 0.5 kg/week
            # in the natural direction implied by current vs target weight.
            direction = 1.0 if self.target_weight_kg <= self.weight_kg else -1.0
            object.__setattr__(self, "weekly_loss_kg", 0.5 * direction)
        if self.weekly_loss_kg is not None:
            implied = self.weight_kg - self.target_weight_kg  # +ve → lose, −ve → gain
            if implied != 0 and (implied > 0) != (self.weekly_loss_kg > 0) and self.weekly_loss_kg != 0:
                raise ValueError(
                    f"Inconsistent direction: weekly_loss_kg={self.weekly_loss_kg:+.2f} "
                    f"with current weight {self.weight_kg:.1f} kg → target "
                    f"{self.target_weight_kg:.1f} kg (implies {implied:+.1f} kg). "
                    f"weekly_loss_kg must be positive to lose weight, negative to gain."
                )
        return self


class PerMealTarget(BaseModel):
    kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fiber_g: float = Field(ge=0)


class PersonalizedTargets(BaseModel):
    daily_kcal: int = Field(gt=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fiber_g: float = Field(ge=0)
    per_meal: dict[MealTypeKey, PerMealTarget]
    bmr: float = Field(ge=0)
    tdee: float = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class Insights(BaseModel):
    """Personalized success-guide content for the meal-plan PDF intro page.

    Every field is derived from the user's profile + targets — nothing here
    is generic. Built once in `derive_insights` and rendered as-is by the PDF
    template / markdown formatter.
    """
    direction: Literal["lose", "gain", "maintain"]
    direction_label: str                           # "deficit" / "surplus" / "maintenance"
    direction_verb: str                            # "lose" / "gain" / "maintain"
    delta_kg: float                                # weight − target (signed; +ve = lose)
    weekly_loss_kg: float                          # resolved rate (signed)
    weeks_to_target: float = Field(ge=0)
    projected_target_date: date | None
    checkpoint_1_month_kg: float
    activity_factor: float = Field(gt=0)
    daily_deficit_kcal: int                        # signed; +ve = deficit
    water_l_per_day: float = Field(ge=0)
    daily_steps_target: int = Field(gt=0)
    protein_g_per_kg: float = Field(ge=0)
    protein_per_main_meal: int = Field(ge=0)
    bmr_drop_estimate: int                         # kcal/day BMR drop at target weight
    cookbook_diet_note: str
    initial_water_loss_caveat: bool


class MealSlot(BaseModel):
    """A single meal on a single day of the plan."""
    day: int = Field(ge=1)
    meal_type: MealTypeKey
    recipe_id: str
    recipe_title: str
    nutrition_per_serving: NutritionInfo


class DayPlan(BaseModel):
    day_number: int = Field(ge=1)
    slots: list[MealSlot]
    daily_totals: NutritionInfo


class CourseItemSource(BaseModel):
    day: int
    meal_type: MealTypeKey
    recipe_title: str
    quantity_g: float


class CourseItem(BaseModel):
    canonical_name: str
    display_name: str
    total_quantity_g: float = Field(ge=0)
    total_quantity_display: str
    category: str
    is_optional: bool = False
    source_recipes: list[CourseItemSource] = Field(default_factory=list)


class CourseList(BaseModel):
    cookbook_name: str
    plan_days: int
    label: str | None = None
    items_by_category: dict[str, list[CourseItem]] = Field(default_factory=dict)
    optional_items: list[CourseItem] = Field(default_factory=list)


class WeekSlice(BaseModel):
    """A 7-day slice of the meal plan (a short trailing remainder is folded into the last week)."""
    week_number: int = Field(ge=1)
    label: str
    day_numbers: list[int]
    days: list[DayPlan]
    avg_daily_nutrition: NutritionInfo
    course_list: CourseList


class MealPlan(BaseModel):
    cookbook_name: str
    manifest: CookbookManifest
    seed: int
    created_at: datetime = Field(default_factory=datetime.now)
    days: list[DayPlan]
    avg_daily_nutrition: NutritionInfo
    weeks: list[WeekSlice] | None = None
    user_profile: UserProfile | None = None
    targets: PersonalizedTargets | None = None
    insights: Insights | None = None
    generation_warnings: list[str] = Field(default_factory=list)
