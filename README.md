# Pharmacy Management System (PMS)

ប្រព័ន្ធគ្រប់គ្រងឱសថស្ថាន សម្រាប់ **លក់រាយ (Retail POS)** និង **លក់ដុំ (Wholesale)** ដោយប្រើ Django REST Framework (backend) និង Vue 3 (frontend)។

ផែនការលម្អិត (requirements, modules, data model, roadmap): [Pharmacy Management System plan](https://claude.ai/artifact/TzPGBWckbNUGyA3kiQqfjM)

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, Django 5.1, Django REST Framework, SimpleJWT, django-filter, drf-spectacular |
| Database | PostgreSQL 16 (SQLite for quick local development) |
| Frontend | Vue 3, Vite, Pinia, Vue Router, Axios, vue-i18n (Khmer / English) |
| Deployment | Docker Compose: nginx + gunicorn + postgres |
| CI | GitHub Actions: backend tests on PostgreSQL, frontend tests and build |

## Project layout

```
backend/
  config/            settings, urls
  apps/
    accounts/        Branch, User (role + branch), JWT login, /api/auth/me/
    catalog/         Product, Unit, ProductUnit (box/strip/tablet), PriceTier, ProductPrice
    inventory/       StockBatch (batch + expiry), StockMovement ledger, FEFO services
    purchasing/      Phase 1: suppliers, purchase orders, goods receipt
    sales/           Phase 1: retail POS; Phase 2: wholesale orders and invoices
    customers/       Phase 2
    prescriptions/   Phase 2
    finance/         Phase 2: payments, KHR/USD
    reports/         Phase 1-3
frontend/
  src/api            axios client with JWT refresh
  src/stores         Pinia stores
  src/views          Login, Dashboard, Products, Stock & Expiry, POS (placeholder)
  src/i18n           Khmer and English text
```

## Key rules already in the code

- Stock quantity is always stored in the **base unit** (e.g. tablet). `ProductUnit.factor` converts box/strip to base units.
- Stock only changes through `apps/inventory/services.py`, which locks the batch rows, runs in a transaction and writes a `StockMovement` row.
- Selling uses **FEFO** (First Expiry, First Out) and never issues an expired batch.
- Each product has exactly one base unit (database constraint), and a batch can never go below zero.

## Run locally (without Docker)

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # demo data, login admin / admin12345
python manage.py runserver
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173, /api is proxied to :8000
```

API docs: http://localhost:8000/api/docs/ · Admin: http://localhost:8000/admin/

## Run with Docker

```bash
cp .env.example .env              # change the secrets
docker compose up --build
docker compose exec backend python manage.py seed_demo
```

Open http://localhost:8080

## Tests

```bash
cd backend && pytest -q
cd frontend && npm test
```

## Main API endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /api/auth/token/`, `POST /api/auth/token/refresh/` | JWT login and refresh |
| `GET /api/auth/me/` | Signed-in user with role and branch |
| `/api/products/`, `/api/product-units/`, `/api/product-prices/` | Products, units, price tiers |
| `/api/categories/`, `/api/manufacturers/`, `/api/units/`, `/api/price-tiers/`, `/api/branches/` | Master data |
| `GET /api/stock/batches/`, `POST /api/stock/batches/receive/` | Batches and manual stock receipt |
| `POST /api/stock/batches/{id}/adjust/` | Stock count adjustment |
| `GET /api/stock/batches/expiring/?days=90` | Batches expiring soon |
| `GET /api/stock/movements/` | Stock ledger |

## Roadmap

1. **Phase 0, Inception**: requirements, ERD, wireframes, this skeleton
2. **Phase 1, Retail MVP**: users and roles, products and units, batch/expiry/FEFO, purchasing, POS, basic reports
3. **Phase 2, Wholesale**: quotation, order and invoice, price tiers, credit, customers, prescriptions, KHR/USD payments
4. **Phase 3, Grow**: branch transfers, dashboard, loyalty, offline POS, KHQR
