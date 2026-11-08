import io
import json

def test_ingestion_csv_preview(client, seed_data):
    csv_content = (
        "Date,Reference,Amount,Type,Description\n"
        "2026-10-01,REF-001,150.00,CREDIT,Customer Payment A\n"
        "2026-10-02,REF-002,280.50,CREDIT,Customer Payment B\n"
    )
    files = {"file": ("bank_statement.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/v1/ingestion/preview", files=files, headers=seed_data["headers"])

    assert response.status_code == 200
    data = response.json()
    assert data["total_estimated_rows"] == 2
    assert "Date" in data["headers"]
    assert "Amount" in data["headers"]
    assert data["is_duplicate"] is False

def test_ingestion_upload_and_normalization(client, seed_data):
    csv_content = (
        "TxnDate,ExternalRef,GrossAmount,TxnType,Narrative\n"
        "2026-10-01,TXN-99881,500.00,CREDIT,Merchant Payout\n"
        "2026-10-02,TXN-99882,120.00,DEBIT,Bank Maintenance Fee\n"
    )
    mapping = {
        "date_col": "TxnDate",
        "amount_col": "GrossAmount",
        "reference_col": "ExternalRef",
        "type_col": "TxnType",
        "description_col": "Narrative"
    }

    files = {"file": ("statement_oct.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {
        "account_id": seed_data["bank_account"].id,
        "mapping_json": json.dumps(mapping)
    }

    response = client.post("/api/v1/ingestion/upload", files=files, data=data, headers=seed_data["headers"])
    assert response.status_code == 200
    batch = response.json()
    assert batch["valid_rows"] == 2
    assert batch["error_rows"] == 0
    assert batch["status"] == "NORMALIZED"

    # Verify transactions created
    tx_resp = client.get(f"/api/v1/transactions?account_id={seed_data['bank_account'].id}", headers=seed_data["headers"])
    assert tx_resp.status_code == 200
    txs = tx_resp.json()
    assert len(txs) == 2
    assert any(t["external_reference"] == "TXN-99881" and float(t["amount"]) == 500.00 for t in txs)

def test_duplicate_file_detection(client, seed_data):
    csv_content = "Date,Amount\n2026-10-01,100.00\n"
    mapping = {"date_col": "Date", "amount_col": "Amount"}

    files = {"file": ("same_file.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": seed_data["bank_account"].id, "mapping_json": json.dumps(mapping)}

    # First upload
    client.post("/api/v1/ingestion/upload", files=files, data=data, headers=seed_data["headers"])

    # Preview same file
    preview_resp = client.post(
        "/api/v1/ingestion/preview",
        files={"file": ("same_file.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        headers=seed_data["headers"]
    )
    assert preview_resp.status_code == 200
    assert preview_resp.json()["is_duplicate"] is True
    assert "already imported" in preview_resp.json()["duplicate_message"]


def test_duplicate_upload_rejected_and_invalid_amount_not_created(client, seed_data):
    content = b'Date,Reference,Amount,Type\n2026-10-01,A,invalid,CREDIT\n2026-10-02,B,12.50,CREDIT\n'
    data = {'account_id': seed_data['bank_account'].id, 'mapping_json': json.dumps({
        'date_col': 'Date', 'amount_col': 'Amount', 'reference_col': 'Reference', 'type_col': 'Type'})}
    def upload():
        return client.post('/api/v1/ingestion/upload', files={'file': ('statement.csv', io.BytesIO(content), 'text/csv')}, data=data, headers=seed_data['headers'])
    first = upload()
    assert first.status_code == 200
    assert first.json()['valid_rows'] == 1 and first.json()['error_rows'] == 1
    second = upload()
    assert second.status_code == 400
    txs = client.get('/api/v1/transactions', headers=seed_data['headers']).json()
    assert len(txs) == 1 and txs[0]['external_reference'] == 'B'


def test_repeated_references_preserve_distinct_transactions(client, seed_data):
    content = b'Date,Reference,Amount,Type\n2026-10-01,A,10,CREDIT\n2026-10-01,A,20,CREDIT\n2026-10-01,A,10,CREDIT\n'
    data = {'account_id': seed_data['bank_account'].id, 'mapping_json': json.dumps({
        'date_col': 'Date', 'amount_col': 'Amount', 'reference_col': 'Reference', 'type_col': 'Type'})}
    response = client.post('/api/v1/ingestion/upload', files={'file': ('statement.csv', io.BytesIO(content), 'text/csv')}, data=data, headers=seed_data['headers'])
    assert response.status_code == 200
    txs = client.get('/api/v1/transactions?include_duplicates=true', headers=seed_data['headers']).json()
    from app.models.transaction import NormalizedTransaction
    # Inspect database through the batch endpoint's persisted counts and the API's nonduplicate view.
    assert response.json()['valid_rows'] == 3
    assert len([t for t in txs if not t['is_duplicate']]) == 2


def test_unknown_transaction_type_is_a_row_error(client, seed_data):
    content = b'Date,Amount,Type\n2026-10-01,100,MYSTERY\n'
    data = {'account_id': seed_data['bank_account'].id, 'mapping_json': json.dumps({'date_col': 'Date', 'amount_col': 'Amount', 'type_col': 'Type'})}
    response = client.post('/api/v1/ingestion/upload', files={'file': ('bad.csv', io.BytesIO(content), 'text/csv')}, data=data, headers=seed_data['headers'])
    assert response.status_code == 200
    assert response.json()['valid_rows'] == 0 and response.json()['error_rows'] == 1


def test_ambiguous_date_requires_explicit_format(client, db_session, seed_data):
    from datetime import datetime
    from app.models.transaction import NormalizedTransaction
    def submit(content, mapping):
        return client.post('/api/v1/ingestion/upload', headers=seed_data['headers'],
            files={'file': ('statement.csv', io.BytesIO(content), 'text/csv')},
            data={'account_id': seed_data['bank_account'].id, 'mapping_json': json.dumps(mapping)})
    base = {'date_col': 'Date', 'amount_col': 'Amount', 'type_col': 'Type'}
    missing = submit(b'Date,Amount,Type\n04/03/2026,100,CREDIT\n', base)
    assert missing.status_code == 200 and missing.json()['valid_rows'] == 0 and missing.json()['error_rows'] == 1
    explicit = submit(b'Date,Amount,Type\n05/03/2026,100,CREDIT\n', {**base, 'date_format': '%d/%m/%Y'})
    assert explicit.status_code == 200 and explicit.json()['valid_rows'] == 1
    tx = db_session.query(NormalizedTransaction).filter_by(batch_id=explicit.json()['id']).one()
    assert tx.transaction_date == datetime(2026, 3, 5)


def test_missing_or_conflicting_direction_does_not_create_transaction(client, db_session, seed_data):
    from app.models.transaction import NormalizedTransaction
    content = b'Date,Amount,Type\n2026-01-01,100,\n2026-01-02,-50,CREDIT\n'
    response = client.post('/api/v1/ingestion/upload', headers=seed_data['headers'],
        files={'file': ('bad.csv', io.BytesIO(content), 'text/csv')}, data={
        'account_id': seed_data['bank_account'].id,
        'mapping_json': json.dumps({'date_col': 'Date', 'amount_col': 'Amount', 'type_col': 'Type'})})
    assert response.status_code == 200 and response.json()['error_rows'] == 2
    assert db_session.query(NormalizedTransaction).count() == 0


def test_split_debit_credit_columns_are_not_silently_dropped(client, seed_data):
    content = b'Date,Debit,Credit\n2026-01-01,50,\n2026-01-02,,100\n'
    response = client.post('/api/v1/ingestion/upload', headers=seed_data['headers'],
        files={'file': ('bank.csv', io.BytesIO(content), 'text/csv')}, data={
        'account_id': seed_data['bank_account'].id,
        'mapping_json': json.dumps({'date_col': 'Date', 'amount_col': 'Credit', 'default_type': 'CREDIT'})})
    assert response.status_code == 400 and 'Separate debit and credit' in response.json()['detail']


def test_import_errors_are_visible_only_to_their_organization(client, db_session, seed_data):
    from app.models.organization import Organization
    from app.models.user import User, UserRole
    from app.utils.security import create_access_token
    content = b'Date,Amount,Type\n04/03/2026,100,CREDIT\n'
    response = client.post('/api/v1/ingestion/upload', headers=seed_data['headers'],
        files={'file': ('bad.csv', io.BytesIO(content), 'text/csv')}, data={
        'account_id': seed_data['bank_account'].id,
        'mapping_json': json.dumps({'date_col': 'Date', 'amount_col': 'Amount', 'type_col': 'Type'})})
    assert response.status_code == 200
    batch_id = response.json()['id']
    errors = client.get(f'/api/v1/ingestion/batches/{batch_id}/errors', headers=seed_data['headers'])
    assert errors.status_code == 200 and len(errors.json()) == 1
    assert errors.json()[0]['row_number'] == 2 and 'date' in errors.json()[0]['error_message'].lower()
    other = Organization(name='Other', slug='other', default_currency='USD'); db_session.add(other); db_session.flush()
    user = User(organization_id=other.id, email='other@example.com', hashed_password='unused', full_name='Other', role=UserRole.OWNER)
    db_session.add(user); db_session.commit()
    token = create_access_token({'sub': user.id, 'org_id': other.id})
    denied = client.get(f'/api/v1/ingestion/batches/{batch_id}/errors', headers={'Authorization': f'Bearer {token}'})
    assert denied.status_code == 404


def test_retry_only_failed_rows_preserves_source_and_avoids_duplicates(client, db_session, seed_data):
    from app.models.ingestion import RawTransaction
    from app.models.transaction import NormalizedTransaction
    from app.models.audit import AuditEvent
    content = b'Date,Amount,Type\n2026-03-04,100,CREDIT\n05/03/2026,25,CREDIT\n'
    mapping = {'date_col': 'Date', 'amount_col': 'Amount', 'type_col': 'Type'}
    first = client.post('/api/v1/ingestion/upload', headers=seed_data['headers'],
        files={'file': ('mixed.csv', io.BytesIO(content), 'text/csv')}, data={
            'account_id': seed_data['bank_account'].id, 'mapping_json': json.dumps(mapping)})
    assert first.status_code == 200
    batch = first.json(); assert (batch['valid_rows'], batch['error_rows']) == (1, 1)
    original = db_session.query(RawTransaction).filter_by(batch_id=batch['id'], row_number=3).one().raw_data.copy()
    retry = client.post(f"/api/v1/ingestion/batches/{batch['id']}/retry", headers=seed_data['headers'],
        json={**mapping, 'date_format': '%d/%m/%Y'})
    assert retry.status_code == 200 and (retry.json()['valid_rows'], retry.json()['error_rows']) == (2, 0)
    assert db_session.query(NormalizedTransaction).filter_by(batch_id=batch['id']).count() == 2
    row = db_session.query(RawTransaction).filter_by(batch_id=batch['id'], row_number=3).one()
    db_session.refresh(row); assert row.raw_data == original and row.error_message is None
    assert db_session.query(AuditEvent).filter_by(resource_id=batch['id'], action='RETRY_IMPORT_ERRORS').count() == 1
    again = client.post(f"/api/v1/ingestion/batches/{batch['id']}/retry", headers=seed_data['headers'], json=mapping)
    assert again.status_code == 400
    assert db_session.query(NormalizedTransaction).filter_by(batch_id=batch['id']).count() == 2


def test_retry_rejects_another_tenant(client, db_session, seed_data):
    from app.models.organization import Organization
    from app.models.user import User, UserRole
    from app.utils.security import create_access_token
    content = b'Date,Amount,Type\n04/03/2026,100,CREDIT\n'
    mapping = {'date_col': 'Date', 'amount_col': 'Amount', 'type_col': 'Type'}
    result = client.post('/api/v1/ingestion/upload', headers=seed_data['headers'], files={'file': ('a.csv', io.BytesIO(content), 'text/csv')},
        data={'account_id': seed_data['bank_account'].id, 'mapping_json': json.dumps(mapping)})
    other = Organization(name='Foreign', slug='foreign', default_currency='USD'); db_session.add(other); db_session.flush()
    user = User(organization_id=other.id, email='foreign@example.com', hashed_password='unused', full_name='Other', role=UserRole.OWNER)
    db_session.add(user); db_session.commit()
    token = create_access_token({'sub': user.id, 'org_id': other.id})
    response = client.post(f"/api/v1/ingestion/batches/{result.json()['id']}/retry", headers={'Authorization': f'Bearer {token}'}, json=mapping)
    assert response.status_code == 400
    assert client.get(f"/api/v1/ingestion/batches/{result.json()['id']}/errors", headers=seed_data['headers']).json()[0]['row_number'] == 2
