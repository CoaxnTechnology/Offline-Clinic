import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Date, DateTime, Boolean,
    ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db import Base

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
