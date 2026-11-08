from datetime import datetime, timedelta, date
from decimal import Decimal
from app.database import SessionLocal, Base, engine
from app.models.organization import Organization, Branch
from app.models.user import User, UserRole
from app.models.financial_account import FinancialAccount, AccountType
from app.models.ingestion import ImportBatch, FileType, IngestionStatus
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.models.reconciliation import (
    ReconciliationSession,
    ReconciliationMatch,
    MatchParticipant,
    SessionStatus,
    MatchType,
    MatchStatus,
    ParticipantSide,
)
from app.models.exception_case import (
    ExceptionCase,
    ExceptionCategory,
    ExceptionSeverity,
    ExceptionStatus,
)
from app.models.shift import ShiftSummary, ShiftStatus
from app.models.ai_insight import AIInsight, InsightType
from app.models.audit import AuditEvent
from app.utils.security import hash_password

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    existing_org = db.query(Organization).filter(Organization.slug == "harare-mega-retail").first()
    if existing_org:
        print("Database already contains demo organization.")
        db.close()
        return

    print("Seeding ReconOS AI demo organization and accounts...")

    # 1. Organization
    org = Organization(
        name="Harare Mega Retail",
        slug="harare-mega-retail",
        default_currency="USD"
    )
    db.add(org)
    db.flush()

    # 2. Branches
    branch_cbd = Branch(
        organization_id=org.id,
        name="CBD Flagship Hypermarket",
        code="HRE-CBD-01",
        city="Harare",
        country="Zimbabwe"
    )
    branch_bor = Branch(
        organization_id=org.id,
        name="Borrowdale Village Mall",
        code="HRE-BOR-02",
        city="Harare",
        country="Zimbabwe"
    )
    db.add_all([branch_cbd, branch_bor])
    db.flush()

    # 3. Users
    owner = User(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        email="admin@harareretail.co.zw",
        hashed_password=hash_password("SuperSecret123!"),
        full_name="Tinashe Moyo",
        role=UserRole.OWNER
    )
    fin_manager = User(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        email="finance@harareretail.co.zw",
        hashed_password=hash_password("FinanceSecure123!"),
        full_name="Ruvimbo Chidemo",
        role=UserRole.FINANCE_MANAGER
    )
    cashier = User(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        email="cashier1@harareretail.co.zw",
        hashed_password=hash_password("CashierPass123!"),
        full_name="Tendai Chikore",
        role=UserRole.OPERATOR
    )
    db.add_all([owner, fin_manager, cashier])
    db.flush()

    # 4. Financial Accounts
    acc_bank = FinancialAccount(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        name="Stanbic Operating Account",
        account_type=AccountType.BANK,
        provider_name="Stanbic Bank",
        account_number="STAN-901124",
        currency="USD",
        opening_balance=Decimal("15000.00"),
        current_balance=Decimal("28805.50")
    )
    acc_ecocash = FinancialAccount(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        name="EcoCash Merchant Wallet",
        account_type=AccountType.MOBILE_MONEY,
        provider_name="EcoCash Zimbabwe",
        account_number="MERCH-99412",
        currency="USD",
        opening_balance=Decimal("5000.00"),
        current_balance=Decimal("13538.89")
    )
    acc_pos = FinancialAccount(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        name="CBD POS Terminal Gateway",
        account_type=AccountType.POS_TERMINAL,
        provider_name="Zimswitch POS",
        account_number="POS-TERM-CBD-01",
        currency="USD",
        opening_balance=Decimal("0.00"),
        current_balance=Decimal("9440.00")
    )
    acc_erp = FinancialAccount(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        name="ERP Sales Ledger (Internal)",
        account_type=AccountType.ERP_LEDGER,
        provider_name="SAP Business One",
        account_number="GL-4001-SALES",
        currency="USD",
        opening_balance=Decimal("0.00"),
        current_balance=Decimal("18040.50")
    )
    db.add_all([acc_bank, acc_ecocash, acc_pos, acc_erp])
    db.flush()

    # 5. Import Batch
    batch = ImportBatch(
        organization_id=org.id,
        financial_account_id=acc_bank.id,
        file_name="bank_statement_oct2026.csv",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_type=FileType.CSV,
        status=IngestionStatus.NORMALIZED,
        total_rows=12,
        valid_rows=12,
        error_rows=0,
        created_by_id=owner.id
    )
    db.add(batch)
    db.flush()

    # 6. Normalized Transactions
    # Exact Match Pair 1
    t1_p = NormalizedTransaction(
        organization_id=org.id,
        batch_id=batch.id,
        financial_account_id=acc_erp.id,
        branch_id=branch_cbd.id,
        external_reference="REF-SALE-101",
        internal_reference="ERP-JV-8801",
        transaction_date=datetime(2026, 10, 1, 10, 0),
        amount=Decimal("1250.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        description="Daily POS Card Collections CBD",
        reconciliation_status=ReconciliationStatus.MATCHED
    )
    t1_s = NormalizedTransaction(
        organization_id=org.id,
        batch_id=batch.id,
        financial_account_id=acc_bank.id,
        branch_id=branch_cbd.id,
        external_reference="REF-SALE-101",
        internal_reference="BNK-STAN-1002",
        transaction_date=datetime(2026, 10, 1, 14, 30),
        amount=Decimal("1250.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        description="POS SETTLEMENT CBD BRANCH",
        reconciliation_status=ReconciliationStatus.MATCHED
    )

    # Exact Match Pair 2
    t2_p = NormalizedTransaction(
        organization_id=org.id,
        batch_id=batch.id,
        financial_account_id=acc_erp.id,
        branch_id=branch_cbd.id,
        external_reference="ECO-MERCH-881",
        internal_reference="ERP-JV-8802",
        transaction_date=datetime(2026, 10, 2, 9, 30),
        amount=Decimal("3400.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        description="EcoCash Merchant Settlement Transfer",
        reconciliation_status=ReconciliationStatus.MATCHED
    )
    t2_s = NormalizedTransaction(
        organization_id=org.id,
        batch_id=batch.id,
        financial_account_id=acc_bank.id,
        branch_id=branch_cbd.id,
        external_reference="ECO-MERCH-881",
        internal_reference="BNK-STAN-1003",
        transaction_date=datetime(2026, 10, 2, 11, 15),
        amount=Decimal("3400.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        description="ECOCASH BULK MERCHANT PAYOUT",
        reconciliation_status=ReconciliationStatus.MATCHED
    )

    # Outlier / Anomaly transaction (EcoCash 12,500.00 at 23:15)
    t_anom = NormalizedTransaction(
        organization_id=org.id,
        batch_id=batch.id,
        financial_account_id=acc_ecocash.id,
        branch_id=branch_cbd.id,
        external_reference="MP261008.2315.A01244",
        internal_reference="ECO-TXN-1244",
        transaction_date=datetime(2026, 10, 8, 23, 15),
        amount=Decimal("12500.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        fee_amount=Decimal("150.0000"),
        description="Customer bulk payment via EcoCash",
        reconciliation_status=ReconciliationStatus.UNRECONCILED,
        anomaly_score=0.92,
        anomaly_flag=True,
        anomaly_reasons=["High statistical outlier (> 3 std dev above mean)", "Off-hours transaction recorded at 23:15"]
    )

    # Unmatched bank fee
    t_unmatched_fee = NormalizedTransaction(
        organization_id=org.id,
        batch_id=batch.id,
        financial_account_id=acc_bank.id,
        branch_id=branch_cbd.id,
        external_reference="BANK-CHG-99",
        internal_reference="BNK-STAN-1005",
        transaction_date=datetime(2026, 10, 3, 16, 0),
        amount=Decimal("45.0000"),
        currency="USD",
        transaction_type=TransactionType.DEBIT,
        description="MONTHLY ACCOUNT MAINTENANCE FEE",
        reconciliation_status=ReconciliationStatus.EXCEPTION
    )
    db.add_all([t1_p, t1_s, t2_p, t2_s, t_anom, t_unmatched_fee])
    db.flush()

    # 7. Reconciliation Session
    session = ReconciliationSession(
        organization_id=org.id,
        session_name="October 2026 Stanbic vs Sales Ledger",
        primary_account_id=acc_erp.id,
        secondary_account_id=acc_bank.id,
        date_from=datetime(2026, 10, 1),
        date_to=datetime(2026, 10, 10),
        status=SessionStatus.COMPLETED,
        total_primary_count=4,
        total_secondary_count=4,
        total_primary_amount=Decimal("8950.0000"),
        total_secondary_amount=Decimal("8995.0000"),
        matched_count=2,
        matched_amount=Decimal("4650.0000"),
        discrepancy_amount=Decimal("4345.0000"),
        initiated_by_id=owner.id
    )
    db.add(session)
    db.flush()

    # 8. Matches
    m1 = ReconciliationMatch(
        session_id=session.id,
        organization_id=org.id,
        match_type=MatchType.EXACT_REFERENCE,
        confidence_score=Decimal("100.00"),
        status=MatchStatus.CONFIRMED,
        primary_amount_total=Decimal("1250.0000"),
        secondary_amount_total=Decimal("1250.0000"),
        difference_amount=Decimal("0.0000"),
        notes="Exact reference match: REF-SALE-101",
        matched_by_user_id=owner.id
    )
    m2 = ReconciliationMatch(
        session_id=session.id,
        organization_id=org.id,
        match_type=MatchType.EXACT_REFERENCE,
        confidence_score=Decimal("100.00"),
        status=MatchStatus.CONFIRMED,
        primary_amount_total=Decimal("3400.0000"),
        secondary_amount_total=Decimal("3400.0000"),
        difference_amount=Decimal("0.0000"),
        notes="Exact reference match: ECO-MERCH-881",
        matched_by_user_id=owner.id
    )
    db.add_all([m1, m2])
    db.flush()

    # Match participants
    db.add_all([
        MatchParticipant(match_id=m1.id, transaction_id=t1_p.id, side=ParticipantSide.PRIMARY, allocated_amount=Decimal("1250.0000")),
        MatchParticipant(match_id=m1.id, transaction_id=t1_s.id, side=ParticipantSide.SECONDARY, allocated_amount=Decimal("1250.0000")),
        MatchParticipant(match_id=m2.id, transaction_id=t2_p.id, side=ParticipantSide.PRIMARY, allocated_amount=Decimal("3400.0000")),
        MatchParticipant(match_id=m2.id, transaction_id=t2_s.id, side=ParticipantSide.SECONDARY, allocated_amount=Decimal("3400.0000")),
    ])

    # 9. Exception Case
    ex_case = ExceptionCase(
        organization_id=org.id,
        session_id=session.id,
        transaction_id=t_unmatched_fee.id,
        case_number="EX-261003-BANKFEE",
        title="Unrecorded Monthly Account Maintenance Fee",
        description="Stanbic Bank debited $45.00 on 2026-10-03 for routine maintenance with no counterpart entry in ERP sales ledger.",
        category=ExceptionCategory.UNRECOGNIZED_FEE,
        severity=ExceptionSeverity.LOW,
        status=ExceptionStatus.OPEN,
        discrepancy_amount=Decimal("45.0000"),
        currency="USD",
        assigned_to_id=fin_manager.id,
        created_by_id=owner.id,
        evidence={
            "bank_ref": "BANK-CHG-99",
            "amount": "45.00",
            "date": "2026-10-03",
            "type": "DEBIT"
        }
    )
    db.add(ex_case)

    # 10. Shift Summary
    shift1 = ShiftSummary(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        cashier_id=cashier.id,
        cashier_name="Tendai Chikore",
        shift_date=date(2026, 10, 1),
        shift_number="SHIFT-CBD-MORN-01",
        opening_cash=Decimal("200.0000"),
        cash_sales=Decimal("1850.0000"),
        mobile_money_sales=Decimal("940.0000"),
        card_sales=Decimal("1250.0000"),
        cash_payouts=Decimal("50.0000"),
        closing_cash_counted=Decimal("2000.0000"),
        system_expected_cash=Decimal("2000.0000"),
        cash_discrepancy=Decimal("0.0000"),
        status=ShiftStatus.VERIFIED,
        supervisor_notes="Float balanced perfectly. Physical cash matched register drawer."
    )
    shift2 = ShiftSummary(
        organization_id=org.id,
        branch_id=branch_cbd.id,
        cashier_id=cashier.id,
        cashier_name="Tendai Chikore",
        shift_date=date(2026, 10, 2),
        shift_number="SHIFT-CBD-EVE-02",
        opening_cash=Decimal("200.0000"),
        cash_sales=Decimal("2100.0000"),
        mobile_money_sales=Decimal("1100.0000"),
        card_sales=Decimal("1500.0000"),
        cash_payouts=Decimal("80.0000"),
        closing_cash_counted=Decimal("2200.0000"),
        system_expected_cash=Decimal("2220.0000"),
        cash_discrepancy=Decimal("-20.0000"),
        status=ShiftStatus.DISCREPANCY_FLAGGED,
        supervisor_notes="Minor $20.00 shortfall under review by branch supervisor."
    )
    db.add_all([shift1, shift2])

    # 11. AI Insight
    insight = AIInsight(
        organization_id=org.id,
        insight_type=InsightType.SETTLEMENT_LAG,
        severity="MEDIUM",
        title="EcoCash Weekend Cut-off Settlement Latency",
        summary="Customer mobile-money transactions processed after 16:00 on Fridays show an average 52-hour lag before appearing in Stanbic Bank clearing reports.",
        evidence={
            "provider": "EcoCash Zimbabwe",
            "bank": "Stanbic Bank",
            "impacted_window": "Friday 16:00 to Monday 08:30",
            "average_delay_hours": 52
        },
        recommendation="Configure reconciliation rule temporal tolerance to 3 business days for Friday batches to eliminate false-positive exception flags."
    )
    db.add(insight)

    # 12. Audit Log
    audit = AuditEvent(
        organization_id=org.id,
        user_id=owner.id,
        action="SYSTEM_INITIALIZE_DEMO_DATA",
        resource_type="ORGANIZATION",
        resource_id=org.id,
        details={"status": "INITIALIZED", "entities_created": 12}
    )
    db.add(audit)

    db.commit()
    db.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
