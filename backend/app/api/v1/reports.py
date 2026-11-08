from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.reports import DailyReconciliationSummary
from app.services.report_service import ReportService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/daily", response_model=DailyReconciliationSummary)
def get_daily_report(
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.utcnow()
    service = ReportService(db)
    return service.get_daily_summary(current_user.organization_id, target_date)

@router.get("/sessions/{session_id}/export/csv")
def export_session_csv(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    csv_data = service.generate_reconciliation_csv(current_user.organization_id, session_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=recon_session_{session_id[:8]}.csv"}
    )

@router.get("/daily/export/pdf")
def export_daily_pdf(
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.utcnow()
    service = ReportService(db)
    summary = service.get_daily_summary(current_user.organization_id, target_date)
    pdf_bytes = service.generate_pdf_report(current_user.organization_id, summary)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ReconOS_Daily_Report_{summary.report_date}.pdf"}
    )
