(() => {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;

      const shouldShow = input.type === "password";
      input.type = shouldShow ? "text" : "password";
      button.textContent = shouldShow ? "Hide" : "Show";
      button.setAttribute(
        "aria-label",
        shouldShow ? "Hide password" : "Show password",
      );
    });
  });

  document.querySelectorAll(".login-role-options").forEach((group) => {
    const options = [...group.querySelectorAll(".login-role-option")];

    options.forEach((option) => {
      option.addEventListener("change", () => {
        options.forEach((candidate) => {
          const input = candidate.querySelector("input");
          candidate.classList.toggle("is-selected", input?.checked === true);
        });
      });
    });
  });

  document.querySelectorAll("[data-dismiss-message]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest(".site-alert")?.remove();
    });
  });
})();
