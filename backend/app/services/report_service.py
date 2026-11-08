import io
import csv
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.models.organization import Organization, Branch
from app.models.reconciliation import ReconciliationSession, ReconciliationMatch, MatchStatus
from app.models.transaction import NormalizedTransaction, ReconciliationStatus
from app.models.exception_case import ExceptionCase, ExceptionStatus
from app.models.shift import ShiftSummary
from app.schemas.reports import DailyReconciliationSummary, BranchPerformanceReport, BranchPerformanceItem
from app.utils.decimal_math import to_decimal

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_daily_summary(
        self,
        organization_id: str,
        target_date: datetime
    ) -> DailyReconciliationSummary:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        org_name = org.name if org else "Organization"
        if not org:
            raise ValueError("Organization not found")
        currency = org.default_currency

        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Transactions
        txs = self.db.query(NormalizedTransaction).filter(
            NormalizedTransaction.organization_id == organization_id,
            NormalizedTransaction.transaction_date >= day_start,
            NormalizedTransaction.transaction_date <= day_end,
            NormalizedTransaction.is_duplicate == False,
            NormalizedTransaction.currency == currency
        ).all()

        total_tx = len(txs)
        total_vol = sum((to_decimal(t.amount) for t in txs), Decimal("0.0000"))

        matched_txs = [t for t in txs if t.reconciliation_status == ReconciliationStatus.MATCHED]
        matched_count = len(matched_txs)
        matched_vol = sum((to_decimal(t.amount) for t in matched_txs), Decimal("0.0000"))

        unmatched_txs = [t for t in txs if t.reconciliation_status != ReconciliationStatus.MATCHED]
        unmatched_count = len(unmatched_txs)
        unmatched_vol = sum((to_decimal(t.amount) for t in unmatched_txs), Decimal("0.0000"))

        recon_rate = Decimal(str(round((matched_count / total_tx) * 100, 2))) if total_tx > 0 else Decimal("0.00")

        # Open exceptions
        open_ex = self.db.query(ExceptionCase).filter(
            ExceptionCase.organization_id == organization_id,
            ExceptionCase.status.in_([ExceptionStatus.OPEN, ExceptionStatus.UNDER_INVESTIGATION]),
            ExceptionCase.currency == currency
        ).all()
        open_ex_count = len(open_ex)
        open_ex_vol = sum((to_decimal(e.discrepancy_amount) for e in open_ex), Decimal("0.0000"))

        # Branches
        branches = self.db.query(Branch).filter(
            Branch.organization_id == organization_id,
            Branch.is_active == True
        ).all()
        branch_names = [b.name for b in branches]

        return DailyReconciliationSummary(
            report_date=day_start.strftime("%Y-%m-%d"),
            organization_name=org_name,
            currency=currency,
            total_volume=total_vol,
            total_transactions=total_tx,
            matched_count=matched_count,
            matched_volume=matched_vol,
            unmatched_count=unmatched_count,
            unmatched_volume=unmatched_vol,
            reconciliation_rate=recon_rate,
            open_exceptions_count=open_ex_count,
            open_exceptions_volume=open_ex_vol,
            branches_covered=branch_names
        )

    def generate_reconciliation_csv(self, organization_id: str, session_id: str) -> str:
        session = self.db.query(ReconciliationSession).filter(
            ReconciliationSession.id == session_id,
            ReconciliationSession.organization_id == organization_id
        ).first()

        if not session:
            raise ValueError("Reconciliation session not found")

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["ReconOS AI - Financial Reconciliation Audit Export"])
        def safe_cell(value):
            text = str(value)
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text

        writer.writerow(["Session Name", safe_cell(session.session_name)])
        writer.writerow(["Period", f"{session.date_from.strftime('%Y-%m-%d')} to {session.date_to.strftime('%Y-%m-%d')}"])
        writer.writerow(["Status", session.status.value])
        writer.writerow(["Matched Amount", f"{session.matched_amount:,.2f}"])
        writer.writerow(["Discrepancy Amount", f"{session.discrepancy_amount:,.2f}"])
        writer.writerow([])

        # Table
        writer.writerow(["Match ID", "Match Type", "Confidence", "Status", "Primary Total", "Secondary Total", "Variance", "Notes"])

        matches = self.db.query(ReconciliationMatch).filter(
            ReconciliationMatch.session_id == session.id
        ).all()

        for m in matches:
            writer.writerow([
                m.id[:8],
                m.match_type.value,
                f"{m.confidence_score}%",
                m.status.value,
                f"{m.primary_amount_total:,.2f}",
                f"{m.secondary_amount_total:,.2f}",
                f"{m.difference_amount:,.2f}",
                safe_cell(m.notes or "")
            ])

        return output.getvalue()

    def generate_pdf_report(self, organization_id: str, summary: DailyReconciliationSummary) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A")
        )

        sub_style = ParagraphStyle(
            name="SubStyle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#64748B")
        )

        elements.append(Paragraph(f"<b>ReconOS AI</b> — Financial Operations Daily Report", title_style))
        from xml.sax.saxutils import escape
        elements.append(Paragraph(f"Organization: {escape(summary.organization_name)} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", sub_style))
        elements.append(Paragraph(f"Currency: {escape(summary.currency)}. Other currencies are excluded; no conversion has been applied.", sub_style))
        elements.append(Spacer(1, 15))

        # Metrics Table
        metrics_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Report Date", summary.report_date, "Reconciliation Rate", f"{summary.reconciliation_rate}%"],
            ["Total Transactions", str(summary.total_transactions), "Total Volume", f"{summary.total_volume:,.2f}"],
            ["Matched Count", str(summary.matched_count), "Matched Volume", f"{summary.matched_volume:,.2f}"],
            ["Unmatched Count", str(summary.unmatched_count), "Unmatched Volume", f"{summary.unmatched_volume:,.2f}"],
            ["Open Exceptions", str(summary.open_exceptions_count), "Exception Value", f"{summary.open_exceptions_volume:,.2f}"]
        ]

        t = Table(metrics_data, colWidths=[140, 120, 140, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')])
        ]))

        elements.append(t)
        elements.append(Spacer(1, 20))

        # Branches coverage section
        elements.append(Paragraph("<b>Configured Operating Branches:</b> " + ", ".join(escape(x) for x in summary.branches_covered), sub_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<i>Open exceptions reflect current status, not historical status at the report date.</i>", sub_style))

        doc.build(elements)
        return buffer.getvalue()
