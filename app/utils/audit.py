"""
Audit logging (PDF spec §9): create, edit, validate, export.
"""
import json
import logging
from typing import Any, Optional

from app.extensions import db
from app.models import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
    entity_type: str,
    action: str,
    user_id: Optional[int] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Append an audit log entry."""
    try:
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            action=action,
            user_id=user_id,
            details=json.dumps(details, default=str) if details else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        logger.warning("Audit log failed: %s", e)
        db.session.rollback()
