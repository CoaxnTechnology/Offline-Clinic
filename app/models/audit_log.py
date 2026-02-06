"""
Audit log for create, edit, validate, export (PDF spec §9).
"""
from app.extensions import db
from datetime import datetime


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(64), nullable=False, index=True)  # patient, appointment, report, etc.
    entity_id = db.Column(db.String(64), nullable=True, index=True)
    action = db.Column(db.String(32), nullable=False, index=True)  # create, edit, validate, export, delete
    user_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True, index=True)
    details = db.Column(db.Text, nullable=True)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "user_id": self.user_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
