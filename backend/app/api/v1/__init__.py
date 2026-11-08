from fastapi import APIRouter, Depends
from app.api.deps import require_non_operator, require_organization_finance_access

from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.branches import router as branch_router
from app.api.v1.accounts import router as account_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.transactions import router as transaction_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.exceptions import router as exception_router
from app.api.v1.shifts import router as shift_router
from app.api.v1.ai import router as ai_router
from app.api.v1.reports import router as report_router
from app.api.v1.audit import router as audit_router
from app.api.v1.analytics import router as analytics_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Onboarding"])
api_v1_router.include_router(org_router, prefix="/organization", tags=["Organization Management"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(branch_router, prefix="/branches", tags=["Branch Management"])
api_v1_router.include_router(account_router, prefix="/accounts", tags=["Financial Accounts"], dependencies=[Depends(require_non_operator)])
api_v1_router.include_router(ingestion_router, prefix="/ingestion", tags=["Statement Ingestion & Normalization"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(transaction_router, prefix="/transactions", tags=["Transaction Operations"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(reconciliation_router, prefix="/reconciliation", tags=["Reconciliation Engine"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(exception_router, prefix="/exceptions", tags=["Exception Management & Cases"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(shift_router, prefix="/shifts", tags=["Cashier & Shift Operations"])
api_v1_router.include_router(ai_router, prefix="/ai", tags=["AI Investigation & Intelligence"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(report_router, prefix="/reports", tags=["Financial Reports & Exports"], dependencies=[Depends(require_organization_finance_access)])
api_v1_router.include_router(audit_router, prefix="/audit", tags=["Security & Audit Ledger"])
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["Operational Analytics"])
