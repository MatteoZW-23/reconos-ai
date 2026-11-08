from datetime import datetime
from decimal import Decimal
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.services.ai_investigation.anomaly_detector import AnomalyDetector
from app.services.ai_investigation.discrepancy_explainer import DiscrepancyExplainer

def test_anomaly_detection_scoring(db_session, seed_data):
    org_id = seed_data["org"].id
    acc = seed_data["bank_account"]

    # Insert a set of typical transactions ($20 - $100 during work hours)
    for i in range(15):
        tx = NormalizedTransaction(
            organization_id=org_id,
            batch_id="batch-normal",
            financial_account_id=acc.id,
            transaction_date=datetime(2026, 10, 5, 10 + (i % 6), 0),
            amount=Decimal(str(30.0 + (i * 4.0))),
            currency="USD",
            transaction_type=TransactionType.CREDIT,
            reconciliation_status=ReconciliationStatus.UNRECONCILED
        )
        db_session.add(tx)

    # Insert an obvious outlier: $12,500 at 3:15 AM
    outlier = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-anom",
        financial_account_id=acc.id,
        transaction_date=datetime(2026, 10, 6, 3, 15),  # 3 AM off-hours
        amount=Decimal("12500.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    db_session.add(outlier)
    db_session.commit()

    detector = AnomalyDetector(contamination=0.10)
    results = detector.scan_transactions(db_session, org_id)

    assert len(results) >= 16
    outlier_res = next((r for r in results if r.transaction_id == outlier.id), None)
    assert outlier_res is not None
    assert outlier_res.anomaly_score > 0.60
    assert any("outlier" in r.lower() or "off-hours" in r.lower() or "unusual" in r.lower() for r in outlier_res.reasons)

def test_discrepancy_explainer(db_session, seed_data):
    org_id = seed_data["org"].id
    acc = seed_data["bank_account"]

    tx = NormalizedTransaction(
        organization_id=org_id,
        batch_id="batch-1",
        financial_account_id=acc.id,
        transaction_date=datetime(2026, 10, 9, 17, 30),  # Friday afternoon
        amount=Decimal("450.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        description="POS Merchant Settlement",
        external_reference="POS-9912",
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    db_session.add(tx)
    db_session.commit()

    explanation = DiscrepancyExplainer.explain_unmatched_transaction(db_session, tx.id, org_id)

    assert explanation.transaction_id == tx.id
    assert "450.00 USD" in explanation.amount
    assert len(explanation.evidence_points) >= 4
    assert explanation.suggested_investigator_action != ""


def test_insights_does_not_fabricate_or_delete_data(client, db_session, seed_data):
    from app.models.ai_insight import AIInsight, InsightType
    assert client.get('/api/v1/ai/insights', headers=seed_data['headers']).json() == []
    assert db_session.query(AIInsight).count() == 0
    old = AIInsight(organization_id=seed_data['org'].id, insight_type=InsightType.SETTLEMENT_LAG,
        title='Mobile Money Weekend Settlement Window Latency', summary='Old placeholder', severity='MEDIUM',
        evidence={'affected_channel': 'EcoCash Merchant Wallet', 'sample_window': 'Friday 16:00 to Monday 09:00', 'average_lag_hours': 52}, recommendation='Review')
    db_session.add(old); db_session.commit()
    assert client.get('/api/v1/ai/insights', headers=seed_data['headers']).json() == []
    assert db_session.query(AIInsight).filter_by(id=old.id).count() == 1


def test_explanation_excludes_cross_currency_candidates(db_session, seed_data):
    common = dict(organization_id=seed_data['org'].id, batch_id='b', transaction_date=datetime(2026, 10, 9),
        amount=Decimal('450'), transaction_type=TransactionType.CREDIT, reconciliation_status=ReconciliationStatus.UNRECONCILED)
    target = NormalizedTransaction(**common, financial_account_id=seed_data['bank_account'].id, currency='USD')
    other = NormalizedTransaction(**common, financial_account_id=seed_data['erp_account'].id, currency='ZAR')
    db_session.add_all([target, other]); db_session.commit()
    explanation = DiscrepancyExplainer.explain_unmatched_transaction(db_session, target.id, seed_data['org'].id)
    assert not any(other.id[:8] in evidence for evidence in explanation.evidence_points)
    assert explanation.confidence is None


def test_anomaly_scan_groups_accounts_and_currencies(db_session, seed_data, monkeypatch):
    common = dict(organization_id=seed_data['org'].id, batch_id='b', transaction_date=datetime(2026, 10, 9),
        amount=Decimal('450'), transaction_type=TransactionType.CREDIT, reconciliation_status=ReconciliationStatus.UNRECONCILED)
    db_session.add_all([
        NormalizedTransaction(**common, financial_account_id=seed_data['bank_account'].id, currency='USD'),
        NormalizedTransaction(**common, financial_account_id=seed_data['bank_account'].id, currency='ZAR'),
        NormalizedTransaction(**common, financial_account_id=seed_data['erp_account'].id, currency='USD')])
    db_session.commit()
    groups = []
    def capture(self, transactions):
        groups.append({(tx.financial_account_id, tx.currency) for tx in transactions})
        return []
    monkeypatch.setattr(AnomalyDetector, '_scan_group', capture)
    AnomalyDetector().scan_transactions(db_session, seed_data['org'].id)
    assert len(groups) == 3 and all(len(group) == 1 for group in groups)
