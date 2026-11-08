from decimal import Decimal
from datetime import datetime
from app.models.organization import Organization, Branch
from app.models.user import User, UserRole
from app.models.financial_account import FinancialAccount, AccountType
from app.models.transaction import NormalizedTransaction, TransactionType, ReconciliationStatus
from app.utils.security import hash_password, create_access_token

def test_tenant_data_isolation(client, db_session, seed_data):
    # Org A is created in seed_data ("Harare Mega Retail")
    # Now create Org B: "Mutare Logistics Ltd"
    org_b = Organization(
        name="Mutare Logistics Ltd",
        slug="mutare-logistics",
        default_currency="USD"
    )
    db_session.add(org_b)
    db_session.flush()

    branch_b = Branch(
        organization_id=org_b.id,
        name="Mutare Main Depot",
        code="MUT-01",
        country="Zimbabwe"
    )
    db_session.add(branch_b)
    db_session.flush()

    user_b = User(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        email="manager@mutarelogistics.co.zw",
        hashed_password=hash_password("Pass123!"),
        full_name="Farai Chimuka",
        role=UserRole.FINANCE_MANAGER
    )
    db_session.add(user_b)
    db_session.flush()

    acc_b = FinancialAccount(
        organization_id=org_b.id,
        branch_id=branch_b.id,
        name="Mutare CBZ Account",
        account_type=AccountType.BANK,
        provider_name="CBZ Bank",
        account_number="CBZ-998811",
        currency="USD"
    )
    db_session.add(acc_b)
    db_session.flush()

    tx_b = NormalizedTransaction(
        organization_id=org_b.id,
        batch_id="batch-b1",
        financial_account_id=acc_b.id,
        external_reference="CONFIDENTIAL-PAY-B",
        transaction_date=datetime(2026, 10, 5),
        amount=Decimal("8500.0000"),
        currency="USD",
        transaction_type=TransactionType.CREDIT,
        reconciliation_status=ReconciliationStatus.UNRECONCILED
    )
    db_session.add(tx_b)
    db_session.commit()

    # Org A queries transactions using Org A's token
    headers_a = seed_data["headers"]
    resp = client.get("/api/v1/transactions", headers=headers_a)
    assert resp.status_code == 200
    tx_list = resp.json()

    # Assert that NONE of Org B's transactions or references leak to Org A
    refs = [t.get("external_reference") for t in tx_list]
    assert "CONFIDENTIAL-PAY-B" not in refs

    # Org A queries accounts
    acc_resp = client.get("/api/v1/accounts", headers=headers_a)
    assert acc_resp.status_code == 200
    acc_names = [a["name"] for a in acc_resp.json()]
    assert "Mutare CBZ Account" not in acc_names


def test_exception_rejects_foreign_tenant_assignee(client, db_session, seed_data):
    other = Organization(name='Other Org', slug='other-org', default_currency='USD')
    db_session.add(other); db_session.flush()
    foreign_user = User(organization_id=other.id, email='foreign@example.com', hashed_password='unused',
        full_name='Foreign User', role=UserRole.OPERATOR)
    db_session.add(foreign_user); db_session.commit()
    response = client.post('/api/v1/exceptions', headers=seed_data['headers'], json={
        'title': 'Investigate', 'description': 'Unmatched', 'category': 'MISSING_TRANSACTION', 'assigned_to_id': foreign_user.id})
    assert response.status_code == 404
