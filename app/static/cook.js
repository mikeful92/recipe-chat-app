(() => {
  const root = document.querySelector("[data-cook-mode]");
  const cards = Array.from(document.querySelectorAll("[data-step-card]"));
  const ingredientChecks = Array.from(
    document.querySelectorAll("[data-ingredient-index]"),
  );
  const prevBtn = document.getElementById("prev-step");
  const nextBtn = document.getElementById("next-step");
  const stepCounter = document.getElementById("step-counter");

  if (!root || !cards.length || !prevBtn || !nextBtn) {
    return;
  }

  const recipeId = root.dataset.recipeId;
  if (!recipeId) {
    return;
  }

  const ingredientKey = `cook:${recipeId}:ingredients`;
  const stepKey = `cook:${recipeId}:step`;
  let index = 0;

  const saveStep = () => {
    localStorage.setItem(stepKey, String(index));
  };

  const saveIngredients = () => {
    const checkedIndexes = ingredientChecks
      .filter((input) => input.checked)
      .map((input) => Number(input.dataset.ingredientIndex))
      .filter((value) => Number.isInteger(value));
    localStorage.setItem(ingredientKey, JSON.stringify(checkedIndexes));
  };

  const render = () => {
    cards.forEach((card, i) => {
      card.classList.toggle("hidden", i !== index);
    });
    if (stepCounter) {
      stepCounter.textContent = `Step ${index + 1} of ${cards.length}`;
    }
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === cards.length - 1;
  };

  const rawStep = Number(localStorage.getItem(stepKey));
  if (Number.isInteger(rawStep) && rawStep >= 0 && rawStep < cards.length) {
    index = rawStep;
  }

  try {
    const rawIngredients = localStorage.getItem(ingredientKey);
    if (rawIngredients) {
      const savedIndexes = JSON.parse(rawIngredients);
      if (Array.isArray(savedIndexes)) {
        ingredientChecks.forEach((input) => {
          const i = Number(input.dataset.ingredientIndex);
          input.checked = savedIndexes.includes(i);
        });
      }
    }
  } catch (_error) {
    localStorage.removeItem(ingredientKey);
  }

  prevBtn.addEventListener("click", () => {
    if (index > 0) {
      index -= 1;
      saveStep();
      render();
    }
  });

  nextBtn.addEventListener("click", () => {
    if (index < cards.length - 1) {
      index += 1;
      saveStep();
      render();
    }
  });

  ingredientChecks.forEach((input) => {
    input.addEventListener("change", saveIngredients);
  });

  saveStep();
  render();
})();
