
document.addEventListener("DOMContentLoaded", function () {
    const buttons = document.querySelectorAll(".toggle-password");

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            const inputId = button.dataset.target;
            const passwordInput = document.getElementById(inputId);

            if (!passwordInput) return;

            const isHidden = passwordInput.type === "password";

            passwordInput.type = isHidden ? "text" : "password";
            button.textContent = isHidden ? "Hide" : "Show";
        });
    });
});
