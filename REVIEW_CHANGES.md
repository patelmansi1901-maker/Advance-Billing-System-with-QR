# Review Changes – BillFlow (Advanced Billing System with QR)

This file explains every change made for the review comments, where the
code lives, and how it works, so you can explain it in your next review.

Review comments:

1. Register page validation changes – mobile number, full name, password
2. Remove the admin-panel link from user pages
3. Improve the UI across the whole website
4. Add a link to the distributor register page

---

## 1. Register page validation (`/distributor-register/`)

All rules live in **one place**: `core/validators.py`.
The register view and the Edit Profile view both import from it, so the
rules can never drift apart.

| Field | Rules |
|---|---|
| Full name | Required · 3–100 characters · letters only · single space, `'` or `-` between words · no numbers · **first + last name** required · extra spaces are removed before saving (`"  Mansi   Patel "` → `"Mansi Patel"`) |
| Mobile number | Required · digits only · exactly 10 digits · must start with **6, 7, 8 or 9** (Indian mobile) · `9999999999`-style numbers rejected · must not already be registered |
| Password | 8–64 characters · at least one **uppercase**, **lowercase**, **number** and **special character** · no spaces · must not contain the mobile number · Django's built-in checks (common passwords, too similar to name/email) |
| Confirm password | Required · must match |
| Email | Required · valid format · must not already be registered |

**Two layers of validation**

* **Browser (instant feedback):** `static/js/form_validation.js`
  * Shows the error under each field as you type / leave the field.
  * Mobile field accepts digits only (letters and symbols are removed as you type).
  * Live password checklist (✓ for each rule met) and a strength bar.
  * Show / Hide buttons on password fields (`static/js/login.js`).
  * On submit, focuses the first wrong field instead of submitting.
* **Server (security):** `distributor_register()` in `core/views.py`
  validates again with `core/validators.py`. JavaScript can be turned off,
  so the server check is the one that really protects the database.
  Entered values are kept in the form when there is an error.

The same name + mobile rules are also used on **Edit Profile**
(`/distributor-profile/edit/`), so a distributor cannot change their details
to something the register page would reject.

## 2. Admin links removed from user pages

* **Home page** (`templates/home.html`): "Admin Login" button → **Login**
  (distributor login); "Get Started" → **Create Account**; footer "Admin"
  link removed.
* **Distributor Login** (`templates/distributor_login.html`): removed
  "System administrator? Admin Login".
* **Forgot Password** for distributors used to say "Registered Admin Email"
  and "Back to Login" went to the admin login. It now goes back to the
  **distributor** login.
* The admin login still works by typing `/admin-login/` directly. The admin
  login page now uses the admin-only reset page (`/admin-forgot-password/`).
* The navigation bar on logged-in pages (`templates/includes/app_nav.html`)
  checks `request.user.is_staff`, so distributors never see admin links
  (Reports, Add Admin). Admins don't see distributor-only links.

## 3. UI improvements

* **One design system:** `static/css/theme.css` (new) gives every logged-in
  page the same font (Inter), colours, inputs, tables and buttons as the
  dashboards. `static/css/login.css` gives every sign-in page (logins,
  register, forgot/verify/reset password) the same navy + blue look.
* **Navigation bar on every inner page**
  (`templates/includes/app_nav.html`): Dashboard, Customers, Products,
  Invoices, New Invoice, Scan QR, Profile, Logout. The current page is
  highlighted. Previously most pages were dead ends with "Back to Home".
* **Same brand everywhere:** "BillFlow" (pages previously said
  "Advanced Billing", "BillPro" or "Advance Billing System").
* **Dashboards show real numbers:** the views were not sending any data,
  so stat cards were empty. Admin: customers, distributors, products,
  sales revenue. Distributor: my customers, products, my invoices, my sales.
  Stat cards and sidebar links now open real pages.
* **Bugs fixed while improving the UI**
  * Add Product page showed the whole form **twice**.
  * Invoice list: table headers did not line up with the columns.
  * Customer list: "Edit" link was outside the table row; added Edit and
    Delete buttons in an Actions column and success/error messages.
  * Customer list showed **every distributor's customers** and did not
    require login; now login is required and each distributor sees only
    their own customers (admin sees all).
  * My Profile values were invisible on the dark card; success message
    after editing the profile was never shown.
  * Distributor "Forgot password" form was missing a hidden `action` field,
    so it always failed with "Invalid request". It now works end to end
    (request OTP → verify → new password).
  * Reports page: summary cards and tables were always empty (the view
    did not send that data), and a date filter like 3 Nov → 3 Nov returned
    nothing (fixed with `invoice_date__date__range`).
  * Admin dashboard "Add Customer" links went to a distributor-only page;
    replaced with Reports / View all customers.
* CSS/JS links end in `?v=2` so browsers load the new files instead of
  an old cached copy.

## 4. Distributor register link

* Distributor Login page: **"New distributor? Create an account"**.
* Home page: "Create Account" in the navbar, "Get Started" button and footer.
* Admin dashboard sidebar: **Register Distributor** (replaces the old
  "Distributor Portal" link, which just sent the admin back to the dashboard).

---

## Files

New:

* `core/validators.py` – shared validation rules
* `static/css/theme.css` – design system for logged-in pages
* `static/js/form_validation.js` – live form validation
* `templates/includes/app_nav.html` – shared top navigation

Main changes: `core/views.py`, `core/tests.py`, `static/css/login.css`,
`static/js/login.js`, and the templates listed in `git status`.

## How to test

```bash
python manage.py check
python manage.py test core      # 32 tests (17 new for these changes)
python manage.py runserver
```

Then open `http://127.0.0.1:8000/distributor-register/` and try a wrong
name, mobile number and password to see the validation.
