# Fraud & Risk Detection Platform — Auth + Transaction Management

Scope of this build (2 of the modules from the full spec):

1. **Authentication & Users** — JWT auth with three roles: Admin, Business Manager, Analyst, each with different permissions.
2. **Transaction Management** — manual entry, CSV import, API ingestion, listing, search/filter, and detail view.

Risk scoring / AI analysis / alerting are **not** included — this is the foundation those features would sit on top of.

## Stack

- **Backend:** FastAPI + SQLAlchemy
- **Database:** SQLite by default (zero setup); swap in Postgres via `DATABASE_URL` for production
- **Auth:** JWT access + refresh tokens (`python-jose`), bcrypt password hashing
- **Frontend:** Single-page vanilla HTML/CSS/JS console, served directly by FastAPI at `/`

## Project layout

```
fraud-risk-platform/
├── app/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── core/
│   │   ├── config.py             # env-driven settings
│   │   ├── database.py           # SQLAlchemy engine/session
│   │   ├── security.py           # password hashing, JWT
│   │   └── deps.py               # auth dependencies, role guards
│   ├── models/                   # SQLAlchemy models (User, Business, Transaction, APIKey)
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/
│   │   └── csv_import.py         # CSV parsing/validation/bulk insert
│   └── routers/
│       ├── auth_router.py        # register, login, refresh, invite
│       ├── admin_router.py       # business management (Admin only)
│       └── transaction_router.py # manual add, CSV import, API ingestion, list/search/detail
├── frontend/
│   └── index.html                # console UI (login + transactions dashboard)
├── sample_data/
│   └── sample_transactions.csv   # 10-row sample for testing import
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd fraud-risk-platform
pip install -r requirements.txt
cp .env.example .env   # edit SECRET_KEY at minimum
uvicorn app.main:app --reload
```

Then open **http://localhost:8000** for the console, or **http://localhost:8000/docs** for interactive API docs (Swagger UI).

## Roles & permissions

| Action                          | Admin | Business Manager | Analyst |
|----------------------------------|:-----:|:-----------------:|:-------:|
| Create businesses                | ✅    | ❌                 | ❌      |
| Create Business Manager accounts | ✅    | ❌                 | ❌      |
| Invite Analysts                  | ❌*   | ✅ (own business)  | ❌      |
| Add transaction manually         | ❌*   | ✅                 | ❌      |
| Import transactions via CSV      | ❌*   | ✅                 | ❌      |
| Issue API keys                   | ❌*   | ✅                 | ❌      |
| View / search / filter txns      | ✅ (all) | ✅ (own business) | ✅ (own business) |
| View transaction detail          | ✅ (all) | ✅ (own business) | ✅ (own business) |

\* Admin is platform-wide and intentionally does not act *as* a business — an Admin creates the Business Manager account, who then owns that business's day-to-day data.

Data is **tenant-isolated**: a Business Manager or Analyst only ever sees their own business's transactions. This is enforced at the query level (`business_id` filter derived from the authenticated user's token), not just hidden in the UI.

## How account creation works

- The **first person ever to register** becomes the platform **Admin** — no separate bootstrap script needed.
- Anyone registering after that must supply a `business_name`, which creates a new Business and makes them its **Business Manager**.
- **Analysts cannot self-register.** A Business Manager (or Admin) invites them via `/auth/invite`, setting their initial password.
- An Admin can also spin up a business + its first manager directly via `/admin/businesses` and `/admin/businesses/{id}/managers` — useful for onboarding a new client business.

## Transaction ingestion — three ways in

1. **Manual** — `POST /transactions` (Business Manager, JWT auth). Used by the "Add transaction" screen in the console.
2. **CSV import** — `POST /transactions/import-csv` (multipart file upload, Business Manager, JWT auth). Row-level validation: bad rows are skipped and reported individually; good rows still import. See `sample_data/sample_transactions.csv` for the expected format.
3. **API** — `POST /transactions/ingest`, authenticated via an `X-API-Key` header instead of a user login. Meant for a business's own checkout/payment backend to push transactions in real time. Keys are generated from the console (or `POST /transactions/api-keys`) and shown **once** at creation — only a salted hash is stored server-side.

All three paths converge on the same `Transaction` table and the same search/filter/detail endpoints, tagged with a `source` field (`manual` / `csv_import` / `api`) so you can always trace where a record came from.

## Search & filter

`GET /transactions` supports: free-text `search` (matches customer ID, transaction ID, or IP), `payment_method`, `source`, `min_amount`/`max_amount`, `date_from`/`date_to`, `location`, plus pagination (`page`, `page_size`). The console's transaction list wires all of these into the toolbar.

## Known simplifications (flagged, not hidden)

- Refresh tokens are stateless JWTs (not stored/revocable server-side) — fine for a demo, but production would want a revocation list or short-lived refresh + rotation.
- No email delivery for invites — the Business Manager sets the Analyst's password directly and shares it out of band.
- No rate limiting on the API ingestion endpoint.
- SQLite is used by default for zero-setup local running; switch `DATABASE_URL` to Postgres and add `psycopg2-binary` to `requirements.txt` for production.
- Schema migrations use `Base.metadata.create_all()` for simplicity — swap in Alembic before this goes anywhere real.

## Testing it quickly

1. Open the console, register — you become Admin.
2. Register a second account with a business name — you become that business's Manager (or log out and use "Create account").
3. As the Manager: add a transaction, import `sample_data/sample_transactions.csv`, generate an API key, invite an Analyst.
4. Log in as the Analyst — confirm you can view/search transactions but the "Add transaction" / "Import CSV" / "API keys" / "Team" nav items are hidden (and the underlying endpoints reject the attempt even if called directly).
