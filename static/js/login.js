// Show / hide password buttons on the sign-in pages.
// Usage: <button type="button" class="toggle-password" data-target="password">Show</button>
document.addEventListener("DOMContentLoaded", function () {
    const buttons = document.querySelectorAll(".toggle-password[data-target]");

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            const passwordInput = document.getElementById(button.dataset.target);

            if (!passwordInput) return;

            const isHidden = passwordInput.type === "password";

            passwordInput.type = isHidden ? "text" : "password";
            button.textContent = isHidden ? "Hide" : "Show";
            button.setAttribute(
                "aria-label",
                isHidden ? "Hide password" : "Show password"
            );
        });
    });
});
