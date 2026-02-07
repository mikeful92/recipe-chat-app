from pydantic import BaseModel, ConfigDict, Field


class RecipeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    healthy: bool = False
    quick_easy: bool = False
    notes: str | None = None


class RecipeIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    amount: str
    unit: str
    optional: bool = False


class RecipeStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    text: str
    timer_minutes: int | None = None


class CookMode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredients_checklist: list[str]
    step_cards: list[str]


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    servings: int
    time_minutes: int
    difficulty: str
    ingredients: list[RecipeIngredient]
    steps: list[RecipeStep]
    substitutions: list[str]
    cook_mode: CookMode
