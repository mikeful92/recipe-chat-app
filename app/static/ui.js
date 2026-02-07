(() => {
  const forms = document.querySelectorAll("[data-loading-form]");
  if (!forms.length) {
    return;
  }

  forms.forEach((form) => {
    form.addEventListener("submit", () => {
      const submit = form.querySelector("button[type='submit']");
      if (!(submit instanceof HTMLButtonElement)) {
        return;
      }
      const label = submit.dataset.submitLabel ?? submit.textContent ?? "Working";
      submit.disabled = true;
      submit.setAttribute("aria-busy", "true");
      submit.textContent = `${label}...`;
    });
  });
})();
