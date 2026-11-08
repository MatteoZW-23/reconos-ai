from datetime import datetime
from decimal import Decimal
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus


def test_dashboard_and_daily_report_exclude_other_currencies(client, db_session, seed_data):
    for currency, amount in [('USD', '10'), ('ZAR', '500')]:
        db_session.add(NormalizedTransaction(
            organization_id=seed_data['org'].id, batch_id='test',
            financial_account_id=seed_data['bank_account'].id,
            transaction_date=datetime(2026, 1, 1, 12), amount=Decimal(amount), currency=currency,
            transaction_type=TransactionType.CREDIT, reconciliation_status=ReconciliationStatus.UNRECONCILED))
    db_session.commit()
    headers = seed_data['headers']
    dashboard = client.get('/api/v1/analytics/dashboard', headers=headers)
    assert dashboard.status_code == 200
    data = dashboard.json()['kpis']
    assert data['currency'] == 'USD'
    assert Decimal(data['total_volume']) == Decimal('10')
    assert data['total_transactions'] == 1
    assert data['shift_float_variance_total'] is None
    report = client.get('/api/v1/reports/daily?date=2026-01-01', headers=headers)
    assert report.status_code == 200
    data = report.json()
    assert data['currency'] == 'USD'
    assert Decimal(data['total_volume']) == Decimal('10')
    assert data['total_transactions'] == 1
    pdf = client.get('/api/v1/reports/daily/export/pdf?date=2026-01-01', headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
