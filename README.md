# ProFuel Admin Dashboard (Flask demo)

## Features
- Responsive admin dashboard overview
- Revenue, order, customer and stock KPI cards
- Revenue trend and sales-channel visualizations
- Inventory/product catalogue with add-product form
- Demo order and customer views
- Services management view
- Business helper chatbot (rule-based demo)
- Mobile-responsive navigation

## Run locally
1. Install Python 3.10+
2. Open a terminal in this folder
3. Create and activate a virtual environment (recommended)
4. Install dependencies:
   `pip install -r requirements.txt`
5. Start the app:
   `python app.py`
6. Open `http://127.0.0.1:5000`

## Important
This is a front-end and Flask proof-of-concept with in-memory demo data.
- Data resets when the server restarts.
- No real authentication, payment processing, or customer account security is implemented.
- The chatbot uses simple keyword rules; it is not connected to an LLM.
- Before production deployment, add a database, authentication/role permissions, CSRF protection,
  input validation, audit logs, backups, secure hosting, and FSSAI-compliant product workflows.
- Replace sample company figures, product records and dates with verified company data.
