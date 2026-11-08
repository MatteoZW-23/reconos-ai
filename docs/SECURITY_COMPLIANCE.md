# ReconOS AI — Security, Compliance & Governance Foundation

## 1. Security Architecture Principles

1. **Non-Custodial & Read-Only:**
   ReconOS AI does not initiate, transmit, reverse, or execute financial transactions on external banking or payment networks. It is an analytics and reconciliation platform.
2. **Multi-Tenant Isolation:**
   Tenant data isolation is enforced at the database layer. All transactional queries and session lookups must include `organization_id == current_user.organization_id`.
3. **Defense-in-Depth Authentication:**
   Standardized JSON Web Tokens (JWT) signed via HMAC-SHA256 (`HS256`) with a cryptographically secure key ($\ge 32$ characters). Passwords hashed with `bcrypt` (adaptive work factor).
4. **Append-Only Immutable Audit Trail:**
   The `audit_events` table logs every sensitive action (statement uploads, reconciliation execution, manual match overrides, exception status transitions, session approvals) with caller identity and UTC timestamp.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Permission / Action | Owner | Finance Manager | Accountant | Branch Manager | Operator | Auditor | Admin |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Onboard Organization | :white_check_mark: | :x: | :x: | :x: | :x: | :x: | :x: |
| Manage Branches | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :x: | :white_check_mark: |
| Manage Team Users | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :x: | :white_check_mark: |
| Create Financial Accounts | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :white_check_mark: |
| Ingest Statement Files | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: | :x: | :white_check_mark: |
| Execute Reconciliation | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :white_check_mark: |
| Manual Match Override | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :x: |
| Approve Session Formal Sign-Off | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :x: | :x: |
| Submit Shift Summary | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: |
| Verify Shift Summary | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: | :x: | :x: | :white_check_mark: |
| View Audit Logs | :white_check_mark: | :white_check_mark: | :x: | :x: | :x: | :white_check_mark: | :white_check_mark: |
| Export Reports (CSV / PDF) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |

---

## 3. Data Protection & Compliance

- **Sensitive Data Minimization:** Bank account numbers and payment phone numbers are stored without exposing customer PINs, CVVs, or online banking passwords.
- **Data Retention Policies:** Historical statement rows (`raw_transactions`) and reconciliation records are maintained in compliance with standard 7-year statutory financial auditing requirements.
