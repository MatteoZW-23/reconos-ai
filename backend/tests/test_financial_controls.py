from datetime import datetime
from decimal import Decimal

import pytest

from app.models.reconciliation import ReconciliationSession, SessionStatus
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.services.reconciliation_engine.engine import ReconciliationEngine
from app.services.reconciliation_engine.rules import ReconciliationRules


def test_rules_never_match_different_currency_or_direction():
    def tx(id, currency, kind):
        return NormalizedTransaction(id=id, currency=currency, transaction_type=kind,
            amount=Decimal('100'), external_reference='SAME', transaction_date=datetime(2026, 1, 1))
    primary = tx('p', 'USD', TransactionType.CREDIT)
    wrong_currency = tx('s1', 'ZAR', TransactionType.CREDIT)
    wrong_direction = tx('s2', 'USD', TransactionType.DEBIT)
    for secondary in (wrong_currency, wrong_direction):
        assert not ReconciliationRules.match_exact_references([primary], [secondary])
        assert not ReconciliationRules.match_amount_and_date_tolerance([primary], [secondary])


def test_session_account_validation_and_execute_once(client, db_session, seed_data):
    data = {'session_name': 'Test', 'primary_account_id': seed_data['erp_account'].id,
            'secondary_account_id': seed_data['bank_account'].id,
            'date_from': '2026-01-01T00:00:00', 'date_to': '2026-01-31T23:59:59'}
    headers = seed_data['headers']
    response = client.post('/api/v1/reconciliation/sessions', json={**data, 'secondary_account_id': 'other-tenant-id'}, headers=headers)
    assert response.status_code == 404
    response = client.post('/api/v1/reconciliation/sessions', json={**data, 'secondary_account_id': data['primary_account_id']}, headers=headers)
    assert response.status_code == 400
    response = client.post('/api/v1/reconciliation/sessions', json=data, headers=headers)
    assert response.status_code == 200, response.text
    session_id = response.json()['id']
    assert client.post(f'/api/v1/reconciliation/sessions/{session_id}/execute', headers=headers).status_code == 200
    assert client.post(f'/api/v1/reconciliation/sessions/{session_id}/execute', headers=headers).status_code == 400


def test_supervisor_cannot_verify_own_shift(client, seed_data):
    headers = seed_data['headers']
    data = {'branch_id': seed_data['branch'].id, 'cashier_name': 'Owner', 'shift_date': '2026-01-01',
            'shift_number': '1', 'opening_cash': '100', 'cash_sales': '10', 'mobile_money_sales': '0',
            'card_sales': '0', 'cash_payouts': '0', 'closing_cash_counted': '110'}
    response = client.post('/api/v1/shifts', json=data, headers=headers)
    assert response.status_code == 200, response.text
    response = client.patch('/api/v1/shifts/' + response.json()['id'] + '/verify', json={'status': 'VERIFIED'}, headers=headers)
    assert response.status_code == 403


def test_manual_transactions_reject_currency_mismatch_and_negative_amount(client, seed_data):
    data = {'financial_account_id': seed_data['bank_account'].id, 'transaction_date': '2026-01-01T00:00:00',
        'amount': '10', 'currency': 'ZAR', 'transaction_type': 'CREDIT'}
    response = client.post('/api/v1/transactions', headers=seed_data['headers'], json=data)
    assert response.status_code == 400
    response = client.post('/api/v1/transactions', headers=seed_data['headers'], json={**data, 'currency': 'USD', 'amount': '-10'})
    assert response.status_code == 422


def test_shift_discrepancy_does_not_invent_case_currency(client, db_session, seed_data):
    from app.models.exception_case import ExceptionCase
    data = {'branch_id': seed_data['branch'].id, 'cashier_name': 'Name', 'shift_date': '2026-01-01',
        'shift_number': 'SHORT', 'opening_cash': '100', 'cash_sales': '0', 'mobile_money_sales': '0',
        'card_sales': '0', 'cash_payouts': '0', 'closing_cash_counted': '0'}
    response = client.post('/api/v1/shifts', headers=seed_data['headers'], json=data)
    assert response.status_code == 200 and response.json()['status'] == 'DISCREPANCY_FLAGGED'
    assert db_session.query(ExceptionCase).count() == 0


def test_shift_rejects_negative_and_duplicate_submission(client, seed_data):
    data = {'branch_id': seed_data['branch'].id, 'cashier_name': 'User', 'shift_date': '2026-04-01',
        'shift_number': ' M1 ', 'opening_cash': '100', 'cash_sales': '0', 'mobile_money_sales': '0',
        'card_sales': '0', 'cash_payouts': '0', 'closing_cash_counted': '100'}
    assert client.post('/api/v1/shifts', headers=seed_data['headers'], json={**data, 'cash_sales': '-1'}).status_code == 422
    first = client.post('/api/v1/shifts', headers=seed_data['headers'], json=data)
    assert first.status_code == 200 and first.json()['shift_number'] == 'M1'
    second = client.post('/api/v1/shifts', headers=seed_data['headers'], json={**data, 'shift_number': 'M1'})
    assert second.status_code == 409
    assert len(client.get('/api/v1/shifts', headers=seed_data['headers']).json()) == 1


def test_shift_rejects_result_overflow(client, seed_data):
    data = {'branch_id': seed_data['branch'].id, 'cashier_name': 'User', 'shift_date': '2026-04-01',
        'shift_number': 'M1', 'opening_cash': '99999999999999', 'cash_sales': '1', 'mobile_money_sales': '0',
        'card_sales': '0', 'cash_payouts': '0', 'closing_cash_counted': '0'}
    assert client.post('/api/v1/shifts', headers=seed_data['headers'], json=data).status_code == 422
