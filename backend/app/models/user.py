import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app.extensions.db import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(
        db.String(20),
        nullable=False  # DOCTOR, TECHNICIAN, RECEPTIONIST
    )
    password_hash = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)

