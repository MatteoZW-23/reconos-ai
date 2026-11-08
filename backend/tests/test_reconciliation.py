from datetime import datetime, timedelta
from decimal import Decimal
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.models.reconciliation import ReconciliationSession, SessionStatus
from app.services.reconciliation_engine.engine import ReconciliationEngine
from app.services.reconciliation_engine.balance_checker import BalanceChecker
from app.utils.decimal_math import to_decimal

def test_exact_reference_and_tolerance_matching(db_session, seed_data):
    org_id = seed_data["org"].id
    p_acc = seed_data["erp_account"]
    s_acc = seed_data["bank_account"]

    # 1. Exact match pair
    t1_p = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-1",
        financial_account_id=p_acc.id,
        external_reference="INV-2026-001",
        transaction_date=datetime(2026, 10, 1, 10, 0),
        amount=Decimal("150.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    t1_s = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-2",
        financial_account_id=s_acc.id,
        external_reference="INV-2026-001",
        transaction_date=datetime(2026, 10, 1, 14, 30),
        amount=Decimal("150.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )

    # 2. Amount & Date Tolerance pair (different ref or no ref, but within 1 day)
    t2_p = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-1",
        financial_account_id=p_acc.id,
        external_reference="SALE-991",
        transaction_date=datetime(2026, 10, 2, 9, 0),
        amount=Decimal("345.5000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    t2_s = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-2",
        financial_account_id=s_acc.id,
        external_reference=None,  # No ref in bank statement
        transaction_date=datetime(2026, 10, 3, 11, 0),  # +1 day lag
        amount=Decimal("345.5000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )

    # 3. Unmatched transaction
    t3_unmatched = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-1",
        financial_account_id=p_acc.id,
        external_reference="MISSING-001",
        transaction_date=datetime(2026, 10, 4, 12, 0),
        amount=Decimal("999.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )

    db_session.add_all([t1_p, t1_s, t2_p, t2_s, t3_unmatched])
    db_session.commit()

    # Create session
    session = ReconciliationSession(
        organization_id=org_id,
        session_name="October Recon Test",
        primary_account_id=p_acc.id,
        secondary_account_id=s_acc.id,
        date_from=datetime(2026, 9, 30),
        date_to=datetime(2026, 10, 10),
        status=SessionStatus.DRAFT,
        initiated_by_id=seed_data["user"].id
    )
    db_session.add(session)
    db_session.commit()

    # Execute engine
    engine = ReconciliationEngine(db_session)
    updated_session = engine.execute_session(session.id, org_id, seed_data["user"].id)

    assert updated_session.matched_count == 2
    assert updated_session.status == SessionStatus.COMPLETED
    assert t1_p.reconciliation_status == ReconciliationStatus.MATCHED
    assert t1_s.reconciliation_status == ReconciliationStatus.MATCHED
    assert t2_p.reconciliation_status == ReconciliationStatus.MATCHED
    assert t2_s.reconciliation_status == ReconciliationStatus.MATCHED
    assert t3_unmatched.reconciliation_status == ReconciliationStatus.EXCEPTION

def test_balance_checker_equation(db_session, seed_data):
    org_id = seed_data["org"].id
    acc = seed_data["bank_account"]

    # Opening balance is 10,000.00
    # Add Credit 1,500.00
    # Add Debit 300.00
    # Expected closing = 10,000 + 1,500 - 300 = 11,200.00
    # Set actual current_balance to 11,200.00 -> balanced!
    acc.current_balance = Decimal("11200.0000")

    t_cr = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-1",
        financial_account_id=acc.id,
        transaction_date=datetime(2026, 10, 5),
        amount=Decimal("1500.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    t_dr = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-1",
        financial_account_id=acc.id,
        transaction_date=datetime(2026, 10, 5),
        amount=Decimal("300.0000"),
        currency="USD",
        transaction_type=TransactionType.DEBIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    db_session.add_all([t_cr, t_dr])
    db_session.commit()

    result = BalanceChecker.check_account_balance(
        db=db_session,
        account_id=acc.id,
        organization_id=org_id,
        date_from=datetime(2026, 10, 1),
        date_to=datetime(2026, 10, 10)
    )

    assert result.is_balanced is True
    assert result.expected_closing == Decimal("11200.0000")
    assert result.variance == Decimal("0.0000")


def test_ambiguous_reference_and_tolerant_amount_require_review():
    from app.services.reconciliation_engine.rules import ReconciliationRules
    def tx(id, ref, amount):
        return NormalizedTransaction(id=id, external_reference=ref, amount=Decimal(amount), currency='USD',
            transaction_type=TransactionType.CREDIT, transaction_date=datetime(2026, 1, 1))
    primary = [tx('p1', 'R', '100'), tx('p2', 'R', '100')]
    secondary = [tx('s1', 'R', '100'), tx('s2', 'R', '100')]
    matches = ReconciliationRules.match_exact_references(primary, secondary)
    assert len(matches) == 2 and all(m.confidence_score < 95 for m in matches)
    tolerance = ReconciliationRules.match_amount_and_date_tolerance([tx('p', 'P', '100')], [tx('s', 'S', '99')], amount_tolerance_percent=Decimal('0.02'))
    assert len(tolerance) == 1 and tolerance[0].confidence_score < 95


def test_pending_match_excluded_from_confirmed_rate(client, db_session, seed_data):
    from app.models.reconciliation import ReconciliationMatch, MatchParticipant, MatchStatus, MatchType, ParticipantSide
    org = seed_data['org'].id
    date = datetime(2026, 1, 1)
    p = NormalizedTransaction(organization_id=org, batch_id='p', financial_account_id=seed_data['erp_account'].id,
        transaction_date=date, amount=Decimal('100'), currency='USD', transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.MANUAL_REVIEW)
    s = NormalizedTransaction(organization_id=org, batch_id='s', financial_account_id=seed_data['bank_account'].id,
        transaction_date=date, amount=Decimal('100'), currency='USD', transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.MANUAL_REVIEW)
    session = ReconciliationSession(organization_id=org, session_name='Review', primary_account_id=seed_data['erp_account'].id,
        secondary_account_id=seed_data['bank_account'].id, date_from=date, date_to=date, status=SessionStatus.COMPLETED,
        total_primary_count=1, total_secondary_count=1, total_primary_amount=100, total_secondary_amount=100,
        matched_count=0, matched_amount=0, discrepancy_amount=200)
    db_session.add_all([p, s, session]); db_session.flush()
    match = ReconciliationMatch(session_id=session.id, organization_id=org, match_type=MatchType.EXACT_REFERENCE,
        confidence_score=80, status=MatchStatus.SUGGESTED, primary_amount_total=100, secondary_amount_total=100, difference_amount=0)
    db_session.add(match); db_session.flush()
    db_session.add_all([MatchParticipant(match_id=match.id, transaction_id=p.id, side=ParticipantSide.PRIMARY, allocated_amount=100),
        MatchParticipant(match_id=match.id, transaction_id=s.id, side=ParticipantSide.SECONDARY, allocated_amount=100)])
    db_session.commit()
    base = f'/api/v1/reconciliation/sessions/{session.id}'
    before = client.get(base, headers=seed_data['headers']).json()
    assert Decimal(before['reconciliation_rate']) == 0 and before['matched_count'] == 0
    result = client.post(base + f'/matches/{match.id}/decision', json={'action': 'CONFIRM'}, headers=seed_data['headers'])
    assert result.status_code == 200
    assert result.json()['matched_count'] == 1 and Decimal(result.json()['reconciliation_rate']) == 100
    assert Decimal(result.json()['discrepancy_amount']) == 0


def test_aggregate_suggestions_support_both_directions(db_session, seed_data):
    from app.models.reconciliation import MatchType, MatchStatus
    org = seed_data['org'].id
    p_acc, s_acc = seed_data['erp_account'].id, seed_data['bank_account'].id
    dt = datetime(2026, 2, 1)
    # Two independent groups: primary 100 -> secondary 40+60; primary 20+30 -> secondary 50.
    for account_id, amount in [(p_acc, '100'), (p_acc, '20'), (p_acc, '30'), (s_acc, '40'), (s_acc, '60'), (s_acc, '50')]:
        db_session.add(NormalizedTransaction(organization_id=org, batch_id='aggregate', financial_account_id=account_id,
            transaction_date=dt, amount=Decimal(amount), currency='USD', transaction_type=TransactionType.CREDIT,
            reconciliation_status=ReconciliationStatus.UNRECONCILED))
    session = ReconciliationSession(organization_id=org, session_name='Aggregates', primary_account_id=p_acc,
        secondary_account_id=s_acc, date_from=dt, date_to=dt, status=SessionStatus.DRAFT,
        rule_config={'allow_one_to_many': True, 'allow_many_to_one': True, 'date_tolerance_days': 0})
    db_session.add(session); db_session.commit()
    result = ReconciliationEngine(db_session).execute_session(session.id, org, seed_data['user'].id)
    assert {m.match_type for m in result.matches} == {MatchType.ONE_TO_MANY, MatchType.MANY_TO_ONE}
    assert all(m.status == MatchStatus.SUGGESTED for m in result.matches)
    assert result.matched_count == 0 and result.discrepancy_amount == Decimal('300')


def test_reconciliation_rule_bounds_reject_unsafe_values(client, seed_data):
    data = {'session_name': 'Invalid', 'primary_account_id': seed_data['erp_account'].id,
        'secondary_account_id': seed_data['bank_account'].id, 'date_from': '2026-01-01T00:00:00',
        'date_to': '2026-01-02T00:00:00', 'rule_config': {'amount_tolerance_percent': '3'}}
    assert client.post('/api/v1/reconciliation/sessions', json=data, headers=seed_data['headers']).status_code == 422


def test_unequal_tolerance_match_cannot_be_confirmed(client, db_session, seed_data):
    from app.models.reconciliation import MatchStatus
    org = seed_data['org'].id; dt = datetime(2026, 3, 1)
    p_acc, s_acc = seed_data['erp_account'].id, seed_data['bank_account'].id
    for account, amount in [(p_acc, '100'), (s_acc, '99')]:
        db_session.add(NormalizedTransaction(organization_id=org, batch_id='b', financial_account_id=account,
            transaction_date=dt, amount=Decimal(amount), currency='USD', transaction_type=TransactionType.CREDIT,
            reconciliation_status=ReconciliationStatus.UNRECONCILED))
    session = ReconciliationSession(organization_id=org, session_name='Tolerance', primary_account_id=p_acc,
        secondary_account_id=s_acc, date_from=dt, date_to=dt, status=SessionStatus.DRAFT,
        rule_config={'amount_tolerance_percent': '0.02'})
    db_session.add(session); db_session.commit()
    session = ReconciliationEngine(db_session).execute_session(session.id, org, seed_data['user'].id)
    match = session.matches[0]
    response = client.post(f'/api/v1/reconciliation/sessions/{session.id}/matches/{match.id}/decision',
        json={'action': 'CONFIRM'}, headers=seed_data['headers'])
    assert response.status_code == 400
    db_session.refresh(match)
    assert match.status == MatchStatus.SUGGESTED
    assert all(p.transaction.reconciliation_status == ReconciliationStatus.MANUAL_REVIEW for p in match.participants)
