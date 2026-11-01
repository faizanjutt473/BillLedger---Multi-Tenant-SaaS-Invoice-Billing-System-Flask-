# BillLedger - Multi-Tenant SaaS Invoice & Billing System

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00)

BillLedger is a multi-tenant SaaS application for invoicing and billing, built with Flask. Every company that registers gets its own isolated workspace where it can manage clients, create invoices with tax, record payments, send PDF invoices by email, and automate recurring billing and payment reminders. Access is controlled by roles: Admin, Accountant and Client.

![BillLedger preview](docs/preview.png)

## Table of contents
- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Daily job: recurring invoices and reminders](#daily-job-recurring-invoices-and-reminders)
- [Roles and permissions](#roles-and-permissions)
- [Multi-tenant security](#multi-tenant-security)
- [Current limitations and roadmap](#current-limitations-and-roadmap)
- [Author](#author)

## Features
- **Multi-tenant workspaces:** register a company and its first admin in one step. Every record belongs to a tenant, and one company can never see another company's data.
- **Clients:** add, edit and delete clients, with outstanding balance per client.
- **Invoices:** line items, quantity, unit price, tax percentage, notes, automatic invoice numbers (`INV-1001`, `INV-1002`, ...), live totals in the form, search and status filters.
- **Invoice lifecycle:** `draft` -> `sent` -> `paid`, with `overdue` set automatically when the due date passes.
- **Payments:** record full or partial payments (bank transfer, cash, Stripe or Paymob as a recorded method). The invoice status updates automatically and overpayment is blocked.
- **PDF and email:** download an invoice as PDF and email it to the client with the PDF attached.
- **Recurring invoices:** monthly or yearly plans that generate and email invoices automatically.
- **Payment reminders:** 3 days before the due date, on the due date, and every 7 days while overdue.
- **Team management:** the admin adds team members and changes their roles.
- **Client portal:** clients log in to view and download their own invoices (read-only).
- **Dashboard:** billed, paid, awaiting payment and overdue totals, plus recent invoices.

## Architecture
![Architecture](docs/architecture.png)

The browser talks to a Flask application organised with an app factory and two blueprints (`auth` and `main`). Business services (PDF, email, daily jobs) sit beside the routes, and all data goes through SQLAlchemy to SQLite in development or PostgreSQL in production.

## Tech stack
| Layer | Technology |
|---|---|
| Backend | Python, Flask, Blueprints, app factory |
| Database | SQLAlchemy ORM, Flask-Migrate (Alembic), SQLite (PostgreSQL ready) |
| Auth and security | Flask-Login, Flask-WTF (CSRF and forms), password hashing with Werkzeug |
| Frontend | Jinja2 templates, HTML, CSS, vanilla JavaScript |
| PDF | xhtml2pdf |
| Email | Flask-Mail (SMTP) |

## Project structure
```
BillLedger/
├── frontend/                  # static HTML/CSS/JS prototype of the UI
├── docs/                      # preview image, architecture diagram, report
└── backend/
    ├── run.py                 # entry point
    ├── config.py              # settings read from .env
    ├── requirements.txt
    ├── migrations/            # database migrations
    └── app/
        ├── __init__.py        # create_app() factory
        ├── extensions.py      # db, migrate, login_manager, csrf, mail
        ├── models.py          # Tenant, User, Client, Invoice, InvoiceItem, Payment, RecurringPlan
        ├── utils.py           # roles_required decorator
        ├── pdf.py             # invoice -> PDF
        ├── emailer.py         # invoice and reminder emails
        ├── jobs.py            # recurring invoices, reminders, run-daily command
        ├── auth/              # register, login, logout
        ├── main/              # dashboard, clients, invoices, payments, team, recurring, portal
        ├── static/            # css and js
        └── templates/         # Jinja2 templates
```

## Getting started

### 1. Clone and create a virtual environment
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>/backend

python -m venv venv
# Windows
venv\Scripts\activate
# Mac / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create the `.env` file
Create a file named `.env` inside the `backend` folder (see [Configuration](#configuration)).

### 4. Create the database
```bash
flask --app run db upgrade
```

### 5. Run the app
```bash
python run.py
```
Open `http://127.0.0.1:5000`, click **Get started**, and register your company.

## Configuration
Create `backend/.env`:
```
SECRET_KEY=replace-with-a-long-random-string
DATABASE_URL=sqlite:///billledger.db
MAIL_USERNAME=
MAIL_PASSWORD=
```
Generate a secret key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
If `MAIL_USERNAME` and `MAIL_PASSWORD` are empty, the app runs in **test mode**: PDFs are generated, but emails are not actually sent. For Gmail, enable 2-Step Verification and use an **App Password**, never your normal password. Never commit `.env` to Git.

## Daily job: recurring invoices and reminders
A single command creates due recurring invoices and sends payment reminders:
```bash
flask --app run run-daily
```
Run it once a day with Windows Task Scheduler or a Linux cron job. There is also a **Run now** button on the Recurring page, which runs the job for your own company only.

## Roles and permissions
| Area | Admin | Accountant | Client |
|---|:-:|:-:|:-:|
| Dashboard, clients, invoices, payments, recurring | Yes | Yes | No |
| Team management | Yes | No | No |
| Own invoices and PDF (read-only portal) | No | No | Yes |

## Multi-tenant security
- Every business table carries a `tenant_id`, and every query is filtered by the logged-in user's tenant.
- Looking up another company's record returns 404, and a Client opening a staff page gets 403.
- Passwords are stored as hashes, forms are protected by CSRF tokens, and redirects after login only accept local paths.
- Isolation is enforced in the application layer. For stricter guarantees in production, consider PostgreSQL row-level security.

## Current limitations and roadmap
- Payments are recorded manually. Stripe and Paymob are listed as methods, but no online checkout is integrated yet.
- No automated test suite yet (pytest is planned).
- No password reset, email verification or email-based team invitations (admins set a temporary password).
- One currency display (Rs) and no multi-language support.
- The daily job must be scheduled externally (cron or Task Scheduler).
- Planned: Docker, CI, online payments, audit log, CSV export, dashboard charts from live data.

## Author
**Muhammad Faizan Farooq** - Machine Learning & AI Engineer
GitHub: [faizanjutt473](https://github.com/faizanjutt473)
LinkedIn: [muhammad-faizan-farooq](https://www.linkedin.com/in/muhammad-faizan-farooq-8bab35372)
