BILLFLOW DASHBOARD UPDATE
=========================

This archive contains your existing BillFlow Django project with refreshed
Admin and Distributor dashboard templates and CSS.

INSTALL / RUN (Windows PowerShell)
1. Extract this ZIP.
2. Open the extracted Billing_system_with_QR folder in VS Code.
3. Create/activate your virtual environment if needed:
   python -m venv venv
   .\venv\Scripts\Activate.ps1
4. Install Django if it is not installed:
   python -m pip install django
5. Run:
   python manage.py check
   python manage.py migrate
   python manage.py runserver
6. Visit:
   http://127.0.0.1:8000/admin-dashboard/
   http://127.0.0.1:8000/distributor-dashboard/

NOTES
- Existing authentication and URL routes are retained.
- Admin customer and distributor counts are read from the database.
- Invoice, sales and payment totals show a dash because this project currently
  has no invoice/payment models to calculate real totals from.
- The Customer model currently has no distributor-owner field. To avoid
  exposing all customers to every distributor, the distributor dashboard
  does not list global customer records. Ownership should be added before
  connecting distributor-specific customer statistics.
- QR payment panel is a UI placeholder; it does not process payments.
- Keep a backup of your original project/database before replacing files.
