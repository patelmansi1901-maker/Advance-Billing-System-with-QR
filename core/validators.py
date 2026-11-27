"""
Shared field validation for BillFlow registration and profile forms.

Each validate_* function returns an error message string, or None when the
value is valid. Views call the matching normalize_* function first so the
saved value is clean (trimmed, single-spaced, digits only).
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


# Letters only, words separated by a single space, apostrophe or hyphen.
# Examples: "Mansi Patel", "Mary-Jane D'Souza".
FULL_NAME_PATTERN = re.compile(r"[A-Za-z]+(?:[ '\-][A-Za-z]+)*")

# Indian mobile numbers: 10 digits starting with 6, 7, 8 or 9.
MOBILE_PATTERN = re.compile(r"[6-9][0-9]{9}")

FULL_NAME_MIN_LENGTH = 3
FULL_NAME_MAX_LENGTH = 100

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
PASSWORD_SPECIAL_CHARACTERS = "!@#$%^&*()_+-=[]{};':\",.<>/?\\|`~"


# ---------------- FULL NAME ----------------

def normalize_full_name(value):
    """Trim the name and collapse repeated spaces into one."""
    return " ".join((value or "").split())


def validate_full_name(name):
    if not name:
        return "Full name is required."

    if len(name) < FULL_NAME_MIN_LENGTH:
        return (
            f"Full name must contain at least "
            f"{FULL_NAME_MIN_LENGTH} characters."
        )

    if len(name) > FULL_NAME_MAX_LENGTH:
        return (
            f"Full name cannot exceed "
            f"{FULL_NAME_MAX_LENGTH} characters."
        )

    if any(character.isdigit() for character in name):
        return "Full name cannot contain numbers."

    if not FULL_NAME_PATTERN.fullmatch(name):
        return (
            "Full name can contain only letters, with single spaces, "
            "apostrophes or hyphens between words."
        )

    if len(name.split(" ")) < 2:
        return "Please enter your first name and last name."

    return None


# ---------------- MOBILE NUMBER ----------------

def normalize_mobile(value):
    """Remove spaces and hyphens that users often type in phone numbers."""
    return re.sub(r"[\s\-]", "", value or "")


def validate_mobile(mobile):
    if not mobile:
        return "Mobile number is required."

    if not mobile.isdigit():
        return "Mobile number can contain digits only."

    if len(mobile) != 10:
        return "Mobile number must be exactly 10 digits."

    if not MOBILE_PATTERN.fullmatch(mobile):
        return "Mobile number must start with 6, 7, 8 or 9."

    if len(set(mobile)) == 1:
        return "Enter a valid mobile number."

    return None


# ---------------- PASSWORD ----------------

def password_rule_errors(password):
    """Return the list of password rules that are not satisfied."""
    missing = []

    if len(password) < PASSWORD_MIN_LENGTH:
        missing.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        missing.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        missing.append("one lowercase letter")
    if not re.search(r"[0-9]", password):
        missing.append("one number")
    if not any(ch in PASSWORD_SPECIAL_CHARACTERS for ch in password):
        missing.append("one special character")

    return missing


def validate_new_password(password, name="", email="", phone=""):
    if not password:
        return "Password is required."

    if len(password) > PASSWORD_MAX_LENGTH:
        return (
            f"Password cannot exceed {PASSWORD_MAX_LENGTH} characters."
        )

    if any(character.isspace() for character in password):
        return "Password cannot contain spaces."

    missing = password_rule_errors(password)
    if missing:
        return "Password must contain " + ", ".join(missing) + "."

    if phone and phone in password:
        return "Password cannot contain your mobile number."

    # Run Django's validators (common passwords, similarity to the
    # user's name or email, numeric-only) against an unsaved user.
    first_name, _, last_name = name.partition(" ")
    user = get_user_model()(
        username=email.split("@")[0] if email else "",
        email=email,
        first_name=first_name,
        last_name=last_name,
    )

    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return " ".join(exc.messages)

    return None


def validate_confirm_password(password, confirm_password):
    if not confirm_password:
        return "Please confirm your password."

    if password != confirm_password:
        return "Passwords do not match."

    return None
