import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Date, DateTime, Boolean,
    ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db import Base

class Report(Base):
    __tablename__ = "reports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id = Column(UUID(as_uuid=True), ForeignKey("studies.id"))
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String(10), default="DRAFT")
    report_html = Column(Text)
    pdf_path = Column(Text)
    finalized_at = Column(DateTime)
