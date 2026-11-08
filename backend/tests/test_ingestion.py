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
