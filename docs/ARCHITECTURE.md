# ReconOS AI — System Architecture & Technical Specification

## 1. Executive Summary

**ReconOS AI** is a commercial-grade, multi-tenant B2B SaaS platform engineered for financial transaction reconciliation and financial operations intelligence. It bridges the critical operational gap faced by enterprises operating in emerging markets and high-volume retail sectors where commercial banks, mobile-money providers, POS networks, and cash operations lack synchronized live APIs.

---

## 2. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Client Layer ["Client Layer (Next.js / TypeScript / Tailwind CSS)"]
        UI_Dash["Dashboard & KPIs"]
        UI_Ingest["Universal Ingestion & Mapping"]
        UI_Recon["Reconciliation Workspace"]
        UI_Ex["Exception & Discrepancy Manager"]
        UI_AI["AI Investigation & Insights"]
        UI_Shifts["Cash Float & Shift Accountability"]
        UI_Reports["Audit & Financial Reports"]
    end

    subgraph API Gateway ["API Gateway (FastAPI 0.115 / Pydantic v2)"]
        AuthMiddleware["JWT Auth & Tenant Scoping"]
        RBAC["Role-Based Access Control"]
        AuditInterceptor["Immutable Audit Logger"]
    end

    subgraph Core Engine Layer ["Core Engine & Processing Layer"]
        IngestionService["Ingestion & Normalization Engine\n(CSV, XLSX, Manual, Delimiter/BOM Sniffer)"]
        ReconEngine["Deterministic Reconciliation Engine\n(Exact, Tolerance, 1-to-Many, Many-to-1)"]
        AI_Layer["Explainable AI & ML Intelligence\n(Isolation Forest, Outlier Scoring, Candidate Ranker)"]
        BalanceVerifier["Mathematical Balance Integrity Verifier\n(Decimal Precision Verification)"]
        ReportGen["Reporting & Document Engine\n(ReportLab PDF, CSV Exports)"]
    end

    subgraph Data & Storage Layer ["Data & Storage Layer"]
        Postgres_SQLite["PostgreSQL / SQLite Storage Engine"]
        RawStore["Raw Transaction Store (JSON Lineage)"]
        NormStore["Normalized Financial Ledger (Decimal 18,4)"]
        AuditLedger["Immutable Audit Event Ledger"]
    end

    Client Layer -->|REST API over TLS| API Gateway
    API Gateway --> Core Engine Layer
    Core Engine Layer --> Data & Storage Layer
```

---

## 3. Core Architectural Modules

### Module A — Multi-Tenant Organization & Branch Management
- **Strict Isolation:** Enforces `organization_id` scoping across all database queries.
- **Granular Branch Access:** Branch managers and cashiers are isolated to their physical branch while finance managers and executives maintain enterprise-wide rollups.
- **Role-Based Access Control (RBAC):**
  - `Owner`: Unrestricted access, organization configuration, billing, and sign-offs.
  - `Finance Manager`: Reconciliation configuration, match approval, write-offs, and reporting.
  - `Accountant`: Manual matches, statement imports, exception investigations.
  - `Branch Manager`: Branch-level cashier shifts, local exception review.
  - `Operator`: Shift cash float submissions and manual transaction entry.
  - `Auditor`: Read-only access to all transactions, matches, and immutable audit logs.
  - `Admin`: User provisioning and system settings.

### Module B — Universal Statement Ingestion
- **Cryptographic File Deduplication:** Uses SHA-256 hashing to prevent duplicate statement imports.
- **Extensible Adapter Architecture:**
  - `CsvAdapter`: Multi-encoding support (`utf-8`, `utf-8-sig`, `latin-1`), automatic delimiter sniffing (`,` `;` `\t`).
  - `ExcelAdapter`: Native XLSX ingestion using `openpyxl`.
  - `EcoCashAdapter`: Auto-detection for mobile money statements (EcoCash, M-Pesa, Airtel Money).
  - `BankStatementAdapter`: Standard bank statement layout recognition.
- **Full Data Lineage:** Every row is preserved in `raw_transactions` in original format before normalization into `normalized_transactions`.

### Module C — Deterministic Financial Reconciliation Engine
- **Decimal Arithmetic:** Strict usage of Python's `Decimal` with 4 decimal places (`Decimal("0.0001")`) to eradicate IEEE-754 floating-point inaccuracies.
- **Multi-Stage Execution:**
  1. *Stage 1:* Exact reference match (100% confidence).
  2. *Stage 2:* Date & amount tolerance match (configurable $\pm N$ days window).
  3. *Stage 3:* One-to-many aggregate match (e.g., matching a single bulk POS merchant settlement payout against multiple individual sales).
  4. *Stage 4:* Mathematical balance verification ($Opening + Credits - Debits = Closing$).
- **Deterministic First:** Probabilistic algorithms never auto-commit ambiguous matches. Any match below confidence threshold remains in `MANUAL_REVIEW`.

### Module D — Explainable AI Financial Investigation
- **Isolation Forest & Statistical Z-Score:** Unsupervised anomaly detection on 4-dimensional feature vectors: log-amount, hour-of-day, day-of-week, and fee ratio.
- **Evidence-Grounded Explanations:** Discrepancy analysis reports cite exact transaction IDs, dates, and amounts without generative hallucinations.
- **Advisory Guarantee:** The AI layer possesses read-only analysis capability; it cannot mutate ledgers or execute transfers.

### Module E — Financial Operations Dashboard
- Operational KPIs, reconciliation rates, payment-channel volume breakdown, branch performance, and cashier shift float integrity.

### Module F — Exception Management
- Lifecycle tracking: `OPEN` $\rightarrow$ `UNDER_INVESTIGATION` $\rightarrow$ `RESOLVED` / `CLOSED` / `ESCALATED`.
- High-value discrepancies ($\ge \$500$) or substantial cashier shortages automatically generate exception tickets with evidence payloads.

### Module G — Financial Reporting
- On-demand Daily Reconciliation Summaries, Branch Performance breakdowns, CSV audit exports, and formatted PDF reports generated via `ReportLab`.

### Module H — Security & Compliance
- Bcrypt password hashing, JWT authentication with role payload, immutable append-only audit ledger (`audit_events`), and CORS protection.
