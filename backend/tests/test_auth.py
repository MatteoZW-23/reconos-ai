def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_success(client, seed_data):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@harareretail.co.zw",
        "password": "SuperSecret123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "owner"
    assert data["organization_name"] == "Harare Mega Retail"

def test_login_invalid_password(client, seed_data):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@harareretail.co.zw",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_onboarding_new_organization(client):
    response = client.post("/api/v1/auth/onboarding", json={
        "organization_name": "Bulawayo Wholesale Ltd",
        "default_currency": "USD",
        "admin_full_name": "Sipho Ncube",
        "admin_email": "sipho@bulawayowholesale.co.zw",
        "admin_password": "SecurePassword456!",
        "branch_name": "Bulawayo Main Depot",
        "branch_code": "BYO-01"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["organization_name"] == "Bulawayo Wholesale Ltd"
    assert "access_token" in data


def test_onboarding_has_no_invented_accounts(client):
    response = client.post('/api/v1/auth/onboarding', json={
        'organization_name': 'New Business', 'default_currency': 'USD',
        'admin_full_name': 'New Owner', 'admin_email': 'owner@newbusiness.example',
        'admin_password': 'StrongPassword123!', 'branch_name': 'Main', 'branch_code': 'MAIN'})
    assert response.status_code == 200
    token = response.json()['access_token']
    accounts = client.get('/api/v1/accounts', headers={'Authorization': f'Bearer {token}'})
    assert accounts.status_code == 200
    assert accounts.json() == []


def test_suspended_organization_cannot_authenticate(client, db_session, seed_data):
    seed_data['org'].is_active = False
    db_session.commit()
    assert client.get('/api/v1/auth/me', headers=seed_data['headers']).status_code == 401
    response = client.post('/api/v1/auth/login', json={'email': seed_data['user'].email, 'password': 'SuperSecret123!'})
    assert response.status_code == 401


def test_production_configuration_rejects_development_defaults():
    import pytest
    from pydantic import ValidationError
    from app.config import Settings, DEVELOPMENT_SECRET
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT='production', SECRET_KEY=DEVELOPMENT_SECRET, DATABASE_URL='postgresql://localhost/test')
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT='production', SECRET_KEY='replace-with-a-random-secret-at-least-32-characters', DATABASE_URL='postgresql://localhost/test')
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT='production', SECRET_KEY='x' * 40, DATABASE_URL='sqlite:///test.db')


def test_finance_manager_cannot_create_owner(client, db_session, seed_data):
    from app.models.user import UserRole
    seed_data['user'].role = UserRole.FINANCE_MANAGER
    db_session.commit()
    response = client.post('/api/v1/organization/members', headers=seed_data['headers'], json={
        'email': 'another-owner@example.com', 'password': 'Password123!', 'full_name': 'Another Owner', 'role': 'owner'})
    assert response.status_code == 403


def test_token_requires_expiration_and_issued_at(client, seed_data):
    import jwt
    from app.config import settings
    token = jwt.encode({'sub': seed_data['user'].id, 'org_id': seed_data['org'].id}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_onboarding_rejects_weak_and_oversized_password(client):
    data = {'organization_name': 'Example Company', 'default_currency': 'USD', 'admin_full_name': 'Owner',
        'admin_email': 'new@example.com', 'admin_password': 'short', 'branch_name': 'Main', 'branch_code': 'HQ'}
    assert client.post('/api/v1/auth/onboarding', json=data).status_code == 422
    assert client.post('/api/v1/auth/onboarding', json={**data, 'admin_password': 'é' * 37}).status_code == 422
