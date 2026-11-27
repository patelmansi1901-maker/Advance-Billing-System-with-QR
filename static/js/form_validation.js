/*
 * BillFlow live form validation
 * ------------------------------------------------------------
 * Used by the Distributor Registration and Edit Profile pages.
 * The rules here mirror core/validators.py so the user sees the
 * same message in the browser that the server would return.
 *
 * Mark a form with  data-live-validate
 * Mark each input with  data-validate="full-name | email | mobile |
 *                                       password | confirm-password"
 * Put an error element after each input:  <p class="field-error" id="<input id>-error">
 */

(function () {
    "use strict";

    var FULL_NAME_PATTERN = /^[A-Za-z]+(?:[ '\-][A-Za-z]+)*$/;
    var EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    var MOBILE_PATTERN = /^[6-9][0-9]{9}$/;
    var SPECIAL_PATTERN = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/;

    var PASSWORD_RULES = {
        length: function (v) { return v.length >= 8; },
        upper: function (v) { return /[A-Z]/.test(v); },
        lower: function (v) { return /[a-z]/.test(v); },
        number: function (v) { return /[0-9]/.test(v); },
        special: function (v) { return SPECIAL_PATTERN.test(v); }
    };

    var RULE_TEXT = {
        length: "at least 8 characters",
        upper: "one uppercase letter",
        lower: "one lowercase letter",
        number: "one number",
        special: "one special character"
    };

    function collapseSpaces(value) {
        return value.trim().replace(/\s+/g, " ");
    }

    /* ---------- Individual field rules ---------- */

    function checkFullName(value) {
        if (!value) return "Full name is required.";
        if (value.length < 3) return "Full name must contain at least 3 characters.";
        if (value.length > 100) return "Full name cannot exceed 100 characters.";
        if (/[0-9]/.test(value)) return "Full name cannot contain numbers.";
        if (!FULL_NAME_PATTERN.test(value)) {
            return "Full name can contain only letters, with single spaces, apostrophes or hyphens between words.";
        }
        if (value.split(" ").length < 2) return "Please enter your first name and last name.";
        return "";
    }

    function checkEmail(value) {
        if (!value) return "Email address is required.";
        if (value.length > 254) return "Email address is too long.";
        if (!EMAIL_PATTERN.test(value)) return "Enter a valid email address.";
        return "";
    }

    function checkMobile(value) {
        if (!value) return "Mobile number is required.";
        if (!/^[0-9]+$/.test(value)) return "Mobile number can contain digits only.";
        if (value.length !== 10) return "Mobile number must be exactly 10 digits.";
        if (!MOBILE_PATTERN.test(value)) return "Mobile number must start with 6, 7, 8 or 9.";
        if (/^(\d)\1{9}$/.test(value)) return "Enter a valid mobile number.";
        return "";
    }

    function checkPassword(value, form) {
        if (!value) return "Password is required.";
        if (value.length > 64) return "Password cannot exceed 64 characters.";
        if (/\s/.test(value)) return "Password cannot contain spaces.";

        var missing = [];
        Object.keys(PASSWORD_RULES).forEach(function (rule) {
            if (!PASSWORD_RULES[rule](value)) missing.push(RULE_TEXT[rule]);
        });
        if (missing.length) return "Password must contain " + missing.join(", ") + ".";

        var mobile = form.querySelector('[data-validate="mobile"]');
        if (mobile && mobile.value.length === 10 && value.indexOf(mobile.value) !== -1) {
            return "Password cannot contain your mobile number.";
        }
        return "";
    }

    function checkConfirm(value, form, input) {
        var target = document.getElementById(input.dataset.match || "password");
        if (!value) return "Please confirm your password.";
        if (target && value !== target.value) return "Passwords do not match.";
        return "";
    }

    var CHECKS = {
        "full-name": checkFullName,
        "email": checkEmail,
        "mobile": checkMobile,
        "password": checkPassword,
        "confirm-password": checkConfirm
    };

    /* ---------- Showing results ---------- */

    function errorElementFor(input) {
        var el = document.getElementById(input.id + "-error");
        if (!el) {
            el = document.createElement("p");
            el.className = "field-error";
            el.id = input.id + "-error";
            input.insertAdjacentElement("afterend", el);
        }
        input.setAttribute("aria-describedby", el.id);
        return el;
    }

    function validateField(input, form) {
        var type = input.dataset.validate;
        var check = CHECKS[type];
        if (!check) return true;

        var message = check(input.value, form, input);
        var errorEl = errorElementFor(input);

        errorEl.textContent = message;
        errorEl.hidden = !message;
        input.classList.toggle("is-invalid", !!message);
        input.classList.toggle("is-valid", !message);
        input.setAttribute("aria-invalid", message ? "true" : "false");
        return !message;
    }

    function updatePasswordMeter(input) {
        var value = input.value;
        var rulesList = document.querySelector('[data-password-rules="' + input.id + '"]');
        var passed = 0;

        Object.keys(PASSWORD_RULES).forEach(function (rule) {
            var ok = PASSWORD_RULES[rule](value);
            if (ok) passed += 1;
            if (rulesList) {
                var item = rulesList.querySelector('[data-rule="' + rule + '"]');
                if (item) item.classList.toggle("met", ok);
            }
        });

        var bar = document.querySelector('[data-strength-bar="' + input.id + '"]');
        var label = document.querySelector('[data-strength-label="' + input.id + '"]');
        if (!bar) return;

        var levels = ["", "Very weak", "Weak", "Fair", "Good", "Strong"];
        var score = value ? passed : 0;

        bar.style.width = (score * 20) + "%";
        bar.dataset.level = String(score);
        if (label) label.textContent = value ? levels[score] : "";
    }

    /* ---------- Wiring ---------- */

    function setupForm(form) {
        var inputs = Array.prototype.slice.call(
            form.querySelectorAll("[data-validate]")
        );

        // JavaScript handles validation, so turn off the browser bubbles.
        form.noValidate = true;

        inputs.forEach(function (input) {
            var type = input.dataset.validate;

            // A server-side error already on the page counts as "touched".
            var existing = document.getElementById(input.id + "-error");
            if (existing && existing.textContent.trim()) {
                input.dataset.touched = "true";
                input.classList.add("is-invalid");
            }

            input.addEventListener("input", function () {
                if (type === "mobile") {
                    var digits = input.value.replace(/\D/g, "").slice(0, 10);
                    if (digits !== input.value) input.value = digits;
                }

                if (type === "password") {
                    updatePasswordMeter(input);
                    var confirm = form.querySelector('[data-validate="confirm-password"]');
                    if (confirm && confirm.dataset.touched) validateField(confirm, form);
                }

                if (input.dataset.touched) validateField(input, form);
            });

            input.addEventListener("blur", function () {
                if (type === "full-name") input.value = collapseSpaces(input.value);
                if (type === "email") input.value = input.value.trim();
                if (input.value || input.dataset.touched) {
                    input.dataset.touched = "true";
                    validateField(input, form);
                }
            });

            if (type === "password") updatePasswordMeter(input);
        });

        form.addEventListener("submit", function (event) {
            var firstInvalid = null;

            inputs.forEach(function (input) {
                if (input.dataset.validate === "full-name") {
                    input.value = collapseSpaces(input.value);
                }
                input.dataset.touched = "true";
                if (!validateField(input, form) && !firstInvalid) {
                    firstInvalid = input;
                }
            });

            if (firstInvalid) {
                event.preventDefault();
                firstInvalid.focus();
                return;
            }

            var button = form.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = true;
                button.dataset.originalText = button.textContent;
                button.textContent = "Please wait…";
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("form[data-live-validate]").forEach(setupForm);
    });

    // Re-enable the submit button if the user comes back with the Back button.
    window.addEventListener("pageshow", function () {
        document.querySelectorAll("form[data-live-validate] button[type='submit']")
            .forEach(function (button) {
                if (button.dataset.originalText) {
                    button.textContent = button.dataset.originalText;
                }
                button.disabled = false;
            });
    });
})();
