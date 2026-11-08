# ReconOS AI — Financial Reconciliation & Operations Intelligence Platform

[![Build & Test Status](https://img.shields.io/badge/pytest-12%20passed-brightgreen.svg)]()
[![Backend](https://img.shields.io/badge/FastAPI-0.115-blue.svg)]()
[![Frontend](https://img.shields.io/badge/React%20%7C%20TypeScript%20%7C%20Tailwind-Production-sky.svg)]()
[![License](https://img.shields.io/badge/License-Proprietary%20Commercial-indigo.svg)]()

> **Commercial-Grade B2B SaaS Platform** designed to monitor, reconcile, and investigate transactions across disconnected banking institutions, mobile-money providers (EcoCash, M-Pesa), POS networks, cash drawers, and enterprise accounting systems (ERP / General Ledger) without requiring live third-party bank APIs.

---

## 1. Quick Start (Instant Launch)

The source repository excludes local virtual environments, environment files, and SQLite databases. Create a local environment and seed the demo database before launching:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Push-Location backend
$env:PYTHONPATH = (Get-Location).Path
..\.venv\Scripts\python.exe -m app.seed
Pop-Location
```

The generated database is created locally at `backend\reconos_ai.db`.

### Option A: One-Click Launch (Windows)
Double-click `start_reconos.bat` or run:
```powershell
.\start_reconos.bat
```
This automatically launches the unified server at **`http://localhost:8000/`** and opens your default browser.

### Option B: Manual CLI Launch
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Launch FastAPI Unified Server (serves both REST API and React UI)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option C: Independent Frontend Dev Server (Optional)
If you wish to run the Vite dev server with Hot Module Replacement (HMR):
```powershell
cd frontend
npm run dev
# Running on http://localhost:3000 (proxies /api to localhost:8000)
```

---

## 2. Default Demo Credentials

The local database (`backend/reconos_ai.db`) is pre-seeded with realistic financial statements, accounts, and demo users:

| Role | Email | Password | Scope |
| :--- | :--- | :--- | :--- |
| **Owner / Executive** | `admin@harareretail.co.zw` | `SuperSecret123!` | Enterprise-wide |
| **Finance Manager** | `finance@harareretail.co.zw` | `FinanceSecure123!` | Enterprise approvals |
| **Cashier / Operator** | `cashier1@harareretail.co.zw` | `CashierPass123!` | CBD Flagship Store |

---

## 3. Automated Test Suite (Pytest)

The test suite validates multi-tenant data isolation, cryptographic file deduplication, exact reference matching, temporal tolerances, mathematical balance equations, and Isolation Forest anomaly scoring:

```powershell
# Run tests directly
.\run_tests.bat

# Or via pytest in terminal
cd backend
..\.venv\Scripts\python.exe -m pytest tests -v
```

**Results:**
- `test_anomaly_detection_scoring` — **PASSED**
- `test_discrepancy_explainer` — **PASSED**
- `test_health_check` — **PASSED**
- `test_login_success` — **PASSED**
- `test_login_invalid_password` — **PASSED**
- `test_onboarding_new_organization` — **PASSED**
- `test_ingestion_csv_preview` — **PASSED**
- `test_ingestion_upload_and_normalization` — **PASSED**
- `test_duplicate_file_detection` — **PASSED**
- `test_exact_reference_and_tolerance_matching` — **PASSED**
- `test_balance_checker_equation` — **PASSED**
- `test_tenant_data_isolation` — **PASSED**

---

## 4. Key Architectural Capabilities

### 1. Deterministic Multi-Stage Reconciliation Engine
- **Stage 1 (Exact Match):** Matches identical reference codes and values ($100\%$ confidence).
- **Stage 2 (Tolerance Match):** Evaluates date proximity ($\pm N$ days) and amount thresholds ($95\%$ confidence).
- **Stage 3 (One-to-Many Aggregate):** Matches bulk settlements against individual sales batches ($90\%$ confidence).
- **Stage 4 (Balance Verification):** Enforces $Opening + Credits - Debits = Closing$.
- **Arbitrary-Precision Arithmetic:** Strict use of Python `Decimal` ($18$ digits, $4$ decimals) to eliminate IEEE-754 floating-point errors.

### 2. Universal Statement Ingestion
- Ingests CSV, TSV, and Excel (XLSX).
- Automatic header and dialect detection (BOM stripping, delimiter sniffing).
- Pre-built adapters for Standard Bank statements, EcoCash/M-Pesa statements, and POS settlements.
- **SHA-256 Deduplication:** Blocks repeated imports of identical statement files.

### 3. Explainable AI Financial Investigation
- **Isolation Forest & Statistical Z-Scores:** Scans multi-dimensional feature space (amount magnitude, timestamp hour, weekday, fee proportion).
- **Advisory Non-Destructive Guarantee:** Generates evidence-grounded hypotheses with citations to underlying transaction IDs; strictly advisory.

### 4. Enterprise Cashier Float Reconciliation
- Verifies physical cash counts against system expected balances:
  $$\text{Expected} = \text{Opening Float} + \text{Cash Sales} - \text{Cash Payouts}$$
- Automatically opens an Exception Case for material shortfalls.

### 5. Financial Reporting & Document Exports
- Daily Reconciliation Summaries, Branch Performance Rollups, CSV Exports, and official PDF Reports generated via `ReportLab`.

---

## 5. Repository Structure

```
reconos-ai/
├── README.md                      # Platform documentation & quickstart
├── start_reconos.bat              # One-click Windows launch script
├── start_reconos.ps1              # PowerShell launch script
├── run_tests.bat                  # Automated Pytest suite runner
├── docker-compose.yml             # Containerized orchestration (PostgreSQL + API + UI)
├── .env.example                   # Environment configuration template
│
├── docs/                          # Technical Specifications
│   ├── ARCHITECTURE.md            # High-level system architecture & diagrams
│   ├── DATABASE_ERD.md            # Full relational schema & foreign keys
│   ├── RECONCILIATION_ENGINE.md   # Detailed mathematical matching algorithms
│   ├── AI_INTELLIGENCE.md         # 3-Layer intelligence architecture
│   ├── SECURITY_COMPLIANCE.md     # Tenant isolation & RBAC matrix
│   └── PRODUCTION_BACKLOG.md      # Prioritized product roadmap
│
├── samples/                       # Realistic Synthetic Statement Datasets
│   ├── bank_statement_oct2026.csv
│   ├── mobile_money_ecocash_oct2026.csv
│   ├── pos_settlement_oct2026.csv
│   ├── internal_erp_ledger_oct2026.csv
│   └── generate_samples.py
│
├── backend/                       # FastAPI Backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                # App entrypoint & static mount
│   │   ├── config.py              # Settings & JWT configuration
│   │   ├── database.py            # SQLAlchemy engine & session factory
│   │   ├── seed.py                # Initial demo dataset seeder
│   │   ├── models/                # SQLAlchemy ORM models (12 tables)
│   │   ├── schemas/               # Pydantic v2 schemas
│   │   ├── services/              # Ingestion, Engine, AI, Reports
│   │   ├── api/v1/                # 13 REST API routers
│   │   └── utils/                 # Decimal arithmetic & Bcrypt security
│   └── tests/                     # 12 Pytest automated tests
│
└── frontend/                      # React / TypeScript / Tailwind CSS
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── src/
    │   ├── App.tsx                # Master router & state coordinator
    │   ├── api.ts                 # Type-safe API client
    │   ├── types.ts               # Core domain interfaces
    │   ├── components/            # Sidebar, Navbar, Badges
    │   └── pages/                 # 15 Interactive SaaS Pages
    └── dist/                      # Production compiled assets
```

---

## 6. Docker Deployment

To launch ReconOS AI with a production PostgreSQL container, copy `.env.example` to `.env`, replace the `SECRET_KEY` and `POSTGRES_PASSWORD` placeholders with unique random values, then run:
```powershell
Copy-Item .env.example .env
# Replace the placeholder secrets in .env before starting the containers.
docker-compose up --build -d
```
- Frontend: `http://localhost:3000`
- Backend API & Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
