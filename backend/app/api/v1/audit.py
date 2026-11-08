from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.audit import AuditEvent
from app.schemas.reports import AuditEventResponse
from app.api.deps import get_current_user, require_roles

router = APIRouter()

@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(require_roles([UserRole.OWNER, UserRole.ADMIN, UserRole.FINANCE_MANAGER, UserRole.AUDITOR])),
    db: Session = Depends(get_db)
):
    query = db.query(AuditEvent).filter(AuditEvent.organization_id == current_user.organization_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)

    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()

    # Enrich with user names
    user_ids = {e.user_id for e in events if e.user_id}
    users_map = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    result = []
    for e in events:
        resp = AuditEventResponse(
            id=e.id,
            organization_id=e.organization_id,
            user_id=e.user_id,
            user_name=users_map.get(e.user_id, "System"),
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            details=e.details,
            ip_address=e.ip_address,
            created_at=e.created_at
        )
        result.append(resp)

    return result
