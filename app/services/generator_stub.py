from uuid import NAMESPACE_URL, uuid5

from app.schemas.recipe import CookMode, Recipe, RecipeIngredient, RecipeRequest, RecipeStep


class StubRecipeGenerator:
    def generate(self, request: RecipeRequest) -> Recipe:
        title_theme = request.theme.strip() if request.theme else "Everyday"
        title = f"{title_theme} Recipe"

        ingredient_names = request.ingredients or ["water"]
        ingredients = [
            RecipeIngredient(name=name, amount="1", unit="item", optional=False)
            for name in ingredient_names
        ]

        steps = [
            RecipeStep(step=idx + 1, text=f"Prepare {name}.", timer_minutes=None)
            for idx, name in enumerate(ingredient_names)
        ]
        if not steps:
            steps = [RecipeStep(step=1, text="Combine ingredients and cook.", timer_minutes=10)]

        substitutions = [
            f"Use any available alternative for {name}." for name in ingredient_names[:2]
        ]

        cook_mode = CookMode(
            ingredients_checklist=ingredients,
            step_cards=[step.text for step in steps],
        )
        summary_ingredients = ", ".join(ingredient_names[:2])
        dish_summary = (
            f"A {title_theme.lower()} dish featuring {summary_ingredients} with straightforward prep."
        )

        raw_id = "|".join(
            [
                title_theme,
                ",".join(ingredient_names),
                str(request.healthy),
                str(request.quick_easy),
                request.notes or "",
            ]
        )

        return Recipe(
            id=str(uuid5(NAMESPACE_URL, raw_id)),
            title=title,
            servings=2,
            time_minutes=20 if request.quick_easy else 35,
            difficulty="easy" if request.quick_easy else "medium",
            dish_summary=dish_summary,
            ingredients=ingredients,
            steps=steps,
            substitutions=substitutions,
            cook_mode=cook_mode,
        )
