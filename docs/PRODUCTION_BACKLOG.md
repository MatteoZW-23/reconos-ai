# ReconOS AI — Prioritized Production-Readiness Backlog

## Phase 1: Working Reconciliation MVP (Completed & Runnable)
- [x] Multi-tenant organization and branch data models
- [x] Universal statement ingestion (CSV, XLSX, Delimiter/BOM sniffer)
- [x] Cryptographic SHA-256 file duplicate rejection
- [x] Exact reference matching & amount/date tolerance matching
- [x] One-to-many aggregate settlement matching
- [x] Decimal arithmetic throughout financial pipeline
- [x] Anomaly scoring via Isolation Forest & statistical Z-scores
- [x] Evidence-grounded plain-language discrepancy explainer
- [x] Interactive Exception Management queue
- [x] Cashier shift float reconciliation
- [x] Audit ledger tracking all administrative actions
- [x] PDF & CSV reporting exports
- [x] Pytest automated test suite (Auth, Ingestion, Matching, Anomalies, Tenant Isolation)

---

## Phase 2: High-Volume Operational Readiness (Next Sprint)
1. **Asynchronous Distributed Worker Queue:**
   - Integrate Celery with Redis for processing statement files with $\ge 250,000$ transactions.
   - Implement streaming chunked database inserts (`copy_from` / bulk_insert_mappings) for 10x throughput.
2. **Automated Optical & PDF Statement Extraction:**
   - Integrate OCR & table extraction models (`pdfplumber` / layout analysis) with confidence scoring and side-by-side human review.
3. **Automated Bank Feed SFTP & Webhooks:**
   - Polling SFTP adapter for corporate host-to-host bank statement drops (MT940, CAMT.053).
4. **Automated Notification Dispatcher:**
   - Email / Webhook / Slack alerts on critical discrepancies ($\ge \$1,000$ or cash shortages).

---

## Phase 3: Enterprise & International Expansion
1. **Multi-Currency Dynamic Conversion:**
   - Support for dual-currency accounting (e.g., USD and local currency) with historical central bank exchange rate lookup.
2. **ERP Two-Way Connectors:**
   - Read/write connectors for SAP Business One, Oracle NetSuite, QuickBooks Online, and Xero.
3. **Self-Service Billing & Subscription Management:**
   - Stripe / Paynow billing integration with tiered limits based on monthly transaction volume.
4. **SOC 2 Type II & ISO 27001 Certification Readiness:**
   - KMS envelope encryption for sensitive database columns at rest and external penetration testing.
