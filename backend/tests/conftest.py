import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.organization import Organization, Branch
from app.models.user import User, UserRole
from app.models.financial_account import FinancialAccount, AccountType
from app.utils.security import hash_password, create_access_token

# Test In-Memory SQLite Engine
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def seed_data(db_session):
    # Create Organization
    org = Organization(
        name="Harare Mega Retail",
        slug="harare-mega-retail",
        default_currency="USD"
    )
    db_session.add(org)
    db_session.flush()

    # Create Branch
    branch = Branch(
        organization_id=org.id,
        name="CBD Flagship",
        code="HRE-CBD-01",
        country="Zimbabwe"
    )
    db_session.add(branch)
    db_session.flush()

    # Create Owner User
    user = User(
        organization_id=org.id,
        branch_id=branch.id,
        email="admin@harareretail.co.zw",
        hashed_password=hash_password("SuperSecret123!"),
        full_name="Tinashe Moyo",
        role=UserRole.OWNER
    )
    db_session.add(user)
    db_session.flush()

    # Create Financial Accounts
    bank_acc = FinancialAccount(
        organization_id=org.id,
        branch_id=branch.id,
        name="Stanbic Operating",
        account_type=AccountType.BANK,
        provider_name="Stanbic Bank",
        account_number="STAN-901124",
        currency="USD",
        opening_balance=10000.00,
        current_balance=10000.00
    )
    ecocash_acc = FinancialAccount(
        organization_id=org.id,
        branch_id=branch.id,
        name="EcoCash Merchant",
        account_type=AccountType.MOBILE_MONEY,
        provider_name="EcoCash",
        account_number="ECO-88771",
        currency="USD",
        opening_balance=5000.00,
        current_balance=5000.00
    )
    erp_acc = FinancialAccount(
        organization_id=org.id,
        branch_id=branch.id,
        name="ERP POS Sales Ledger",
        account_type=AccountType.ERP_LEDGER,
        provider_name="SAP Business One",
        account_number="GL-SALES-4000",
        currency="USD",
        opening_balance=0.00,
        current_balance=0.00
    )
    db_session.add_all([bank_acc, ecocash_acc, erp_acc])
    db_session.commit()

    token = create_access_token({
        "sub": user.id,
        "org_id": org.id,
        "role": user.role.value,
        "branch_id": branch.id
    })

    return {
        "org": org,
        "branch": branch,
        "user": user,
        "token": token,
        "bank_account": bank_acc,
        "ecocash_account": ecocash_acc,
        "erp_account": erp_acc,
        "headers": {"Authorization": f"Bearer {token}"}
    }
