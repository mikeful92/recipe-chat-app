(() => {
  const cards = Array.from(document.querySelectorAll("[data-step-card]"));
  const prevBtn = document.getElementById("prev-step");
  const nextBtn = document.getElementById("next-step");

  if (!cards.length || !prevBtn || !nextBtn) {
    return;
  }

  let index = 0;

  const render = () => {
    cards.forEach((card, i) => {
      card.classList.toggle("hidden", i !== index);
    });
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === cards.length - 1;
  };

  prevBtn.addEventListener("click", () => {
    if (index > 0) {
      index -= 1;
      render();
    }
  });

  nextBtn.addEventListener("click", () => {
    if (index < cards.length - 1) {
      index += 1;
      render();
    }
  });

  render();
})();
