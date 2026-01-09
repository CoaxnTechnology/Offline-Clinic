import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Date, DateTime, Boolean,
    ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db import Base

class Study(Base):
    __tablename__ = "studies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_uid = Column(Text, unique=True, nullable=False)
    modality = Column(String(10), default="US")
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"))
    status = Column(String(20), default="RECEIVED")
    created_at = Column(DateTime, default=datetime.utcnow)
