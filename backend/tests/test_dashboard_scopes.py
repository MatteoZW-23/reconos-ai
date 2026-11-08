from datetime import date, datetime
from decimal import Decimal
from app.models.organization import Branch
from app.models.user import User, UserRole
from app.models.shift import ShiftSummary, ShiftStatus
from app.models.financial_account import FinancialAccount, AccountType
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.utils.security import create_access_token


def headers(user):
    return {'Authorization': 'Bearer ' + create_access_token({'sub': user.id, 'org_id': user.organization_id})}


def test_branch_dashboard_excludes_other_branch(client, db_session, seed_data):
    org = seed_data['org']; branch = seed_data['branch']
    other = Branch(organization_id=org.id, name='Other branch', code='OTHER', country='Zimbabwe')
    db_session.add(other); db_session.flush()
    manager = User(organization_id=org.id, branch_id=branch.id, email='branch@example.com',
        hashed_password='unused', full_name='Branch Manager', role=UserRole.BRANCH_MANAGER)
    account = FinancialAccount(organization_id=org.id, branch_id=other.id, name='Private account',
        account_type=AccountType.BANK, provider_name='Other', account_number='private', currency='USD',
        opening_balance=Decimal('900'), current_balance=Decimal('900'))
    db_session.add_all([manager, account]); db_session.flush()
    for account_id, branch_id, amount in [(seed_data['bank_account'].id, branch.id, '10'), (account.id, other.id, '900')]:
        db_session.add(NormalizedTransaction(organization_id=org.id, branch_id=branch_id, batch_id='test',
            financial_account_id=account_id, transaction_date=datetime(2026, 1, 1), amount=Decimal(amount),
            currency='USD', transaction_type=TransactionType.CREDIT, reconciliation_status=ReconciliationStatus.UNRECONCILED))
    db_session.commit()
    response = client.get('/api/v1/analytics/dashboard', headers=headers(manager))
    assert response.status_code == 200
    result = response.json()
    assert result['scope'] == 'branch' and result['branch_name'] == branch.name
    assert 'Private account' not in [a['name'] for a in result['accounts']]
    assert Decimal(result['kpis']['total_volume']) == Decimal('10')
    assert len(result['branches']) == 1


def test_operator_dashboard_contains_only_own_shifts(client, db_session, seed_data):
    org = seed_data['org']; branch = seed_data['branch']
    operator = User(organization_id=org.id, branch_id=branch.id, email='cashier@example.com',
        hashed_password='unused', full_name='Cashier', role=UserRole.OPERATOR)
    db_session.add(operator); db_session.flush()
    for user, number in [(operator, 'OWN'), (seed_data['user'], 'OTHER')]:
        db_session.add(ShiftSummary(organization_id=org.id, branch_id=branch.id, cashier_id=user.id,
            cashier_name=user.full_name, shift_date=date(2026,1,1), shift_number=number,
            opening_cash=0, cash_sales=0, mobile_money_sales=0, card_sales=0, cash_payouts=0,
            closing_cash_counted=0, system_expected_cash=0, cash_discrepancy=0, status=ShiftStatus.SUBMITTED))
    db_session.commit()
    response = client.get('/api/v1/analytics/dashboard', headers=headers(operator))
    assert response.status_code == 200
    result = response.json()
    assert result['scope'] == 'employee' and [s['shift_number'] for s in result['shifts']] == ['OWN']
    assert 'accounts' not in result and 'kpis' not in result


def test_branch_manager_without_branch_is_denied(client, db_session, seed_data):
    user = seed_data['user']; user.role = UserRole.BRANCH_MANAGER; user.branch_id = None
    db_session.commit()
    assert client.get('/api/v1/analytics/dashboard', headers=headers(user)).status_code == 403


def test_cashier_cannot_read_organization_financial_areas(client, db_session, seed_data):
    user = seed_data['user']; user.role = UserRole.OPERATOR
    db_session.commit()
    for path in ['/api/v1/accounts', '/api/v1/transactions', '/api/v1/organization/members',
                 '/api/v1/reconciliation/sessions', '/api/v1/ingestion/batches',
                 '/api/v1/exceptions', '/api/v1/ai/insights', '/api/v1/reports/daily', '/api/v1/audit']:
        response = client.get(path, headers=headers(user))
        assert response.status_code == 403, (path, response.status_code)


def test_cashier_gets_only_assigned_branch_and_own_shift_supervisor_note(client, db_session, seed_data):
    org = seed_data['org']; branch = seed_data['branch']
    other = Branch(organization_id=org.id, name='Other branch', code='OTHER', country='Zimbabwe')
    cashier = User(organization_id=org.id, branch_id=branch.id, email='operator@example.com',
        hashed_password='unused', full_name='Assigned Cashier', role=UserRole.OPERATOR)
    db_session.add_all([other, cashier]); db_session.flush()
    shift = ShiftSummary(organization_id=org.id, branch_id=branch.id, cashier_id=cashier.id,
        cashier_name=cashier.full_name, shift_date=date(2026,1,1), shift_number='OWN',
        opening_cash=0, cash_sales=0, mobile_money_sales=0, card_sales=0, cash_payouts=0,
        closing_cash_counted=0, system_expected_cash=0, cash_discrepancy=0, status=ShiftStatus.VERIFIED,
        supervisor_notes='Please review your count')
    db_session.add(shift); db_session.commit()
    result = client.get('/api/v1/branches', headers=headers(cashier)).json()
    assert [item['id'] for item in result] == [branch.id]
    dashboard = client.get('/api/v1/analytics/dashboard', headers=headers(cashier)).json()
    assert dashboard['shifts'][0]['supervisor_notes'] == 'Please review your count'
    assert client.patch(f'/api/v1/shifts/{shift.id}/verify', json={'status':'VERIFIED'}, headers=headers(cashier)).status_code == 403


def test_branch_manager_cannot_access_organization_wide_endpoints(client, db_session, seed_data):
    user = seed_data['user']; user.role = UserRole.BRANCH_MANAGER
    db_session.commit()
    for path in ['/api/v1/transactions', '/api/v1/organization/members', '/api/v1/reconciliation/sessions',
                 '/api/v1/ingestion/batches', '/api/v1/exceptions', '/api/v1/ai/insights', '/api/v1/reports/daily']:
        response = client.get(path, headers=headers(user))
        assert response.status_code == 403, (path, response.status_code)
    assert client.get('/api/v1/accounts', headers=headers(user)).status_code == 200


def test_branch_manager_balance_check_does_not_access_other_branch(client, db_session, seed_data):
    user = seed_data['user']; user.role = UserRole.BRANCH_MANAGER
    other = Branch(organization_id=seed_data['org'].id, name='Other', code='OTHER', country='Zimbabwe')
    db_session.add(other); db_session.flush()
    account = FinancialAccount(organization_id=seed_data['org'].id, branch_id=other.id, name='Other Bank',
        account_type=AccountType.BANK, provider_name='Bank', account_number='123', currency='USD')
    db_session.add(account); db_session.commit()
    assert client.get(f'/api/v1/accounts/{account.id}/balance-check', headers=headers(user)).status_code == 404
    assert all(item['id'] != account.id for item in client.get('/api/v1/accounts', headers=headers(user)).json())
    user.branch_id = None; db_session.commit()
    assert client.get('/api/v1/accounts', headers=headers(user)).status_code == 403


def test_auditor_has_read_access_but_cannot_create_transactions_or_members(client, db_session, seed_data):
    user = seed_data['user']; user.role = UserRole.AUDITOR
    db_session.commit()
    assert client.get('/api/v1/transactions', headers=headers(user)).status_code == 200
    assert client.get('/api/v1/organization/members', headers=headers(user)).status_code == 403
    response = client.post('/api/v1/transactions', headers=headers(user), json={
        'financial_account_id': seed_data['bank_account'].id, 'transaction_date': '2026-01-01T00:00:00',
        'amount': '100', 'currency': 'USD', 'transaction_type': 'CREDIT'})
    assert response.status_code == 403
