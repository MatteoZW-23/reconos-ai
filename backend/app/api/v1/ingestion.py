import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.ingestion import ImportBatch
from app.schemas.ingestion import ImportPreviewResponse, BatchResponse, ColumnMapping
from app.services.ingestion_service import IngestionService
from app.services.ai_investigation.anomaly_detector import AnomalyDetector
from app.api.deps import get_current_user, require_roles

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

async def read_statement(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Statement exceeds the 10 MB upload limit")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".tsv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV, TSV and XLSX files are supported")
    return content

@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_statement_file(
    file: UploadFile = File(...),
    account_id: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = IngestionService(db)
    content_bytes = await read_statement(file)

    try:
        preview = service.generate_preview(
            file_bytes=content_bytes,
            filename=file.filename or "statement.csv",
            organization_id=current_user.organization_id,
            account_id=account_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return preview

@router.post("/upload", response_model=BatchResponse)
async def upload_statement_file(
    file: UploadFile = File(...),
    account_id: str = Form(...),
    mapping_json: str = Form(...),
    current_user: User = Depends(require_roles([
        UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.ACCOUNTANT, UserRole.OPERATOR
    ])),
    db: Session = Depends(get_db)
):
    try:
        mapping_data = json.loads(mapping_json)
        column_mapping = ColumnMapping(**mapping_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid column mapping structure: {str(e)}")

    content_bytes = await read_statement(file)

    service = IngestionService(db)
    try:
        batch = service.process_import(
            file_bytes=content_bytes,
            filename=file.filename or "statement.csv",
            organization_id=current_user.organization_id,
            account_id=account_id,
            column_mapping=column_mapping,
            user_id=current_user.id
        )

        # Run AI anomaly detection scan on newly ingested batch
        try:
            detector = AnomalyDetector()
            detector.scan_transactions(db, current_user.organization_id, batch_id=batch.id)
        except Exception:
            pass  # Anomaly detection runs non-blocking

        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process statement")

@router.get("/batches", response_model=list[BatchResponse])
def list_import_batches(
    account_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ImportBatch).filter(ImportBatch.organization_id == current_user.organization_id)
    if account_id:
        query = query.filter(ImportBatch.financial_account_id == account_id)
    return query.order_by(ImportBatch.created_at.desc()).limit(100).all()
