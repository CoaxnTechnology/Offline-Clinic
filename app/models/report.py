"""
Report Model
Stores metadata for generated PDF reports
"""
from app.extensions import db
from .base import TimestampMixin
from datetime import datetime


class Report(db.Model, TimestampMixin):
    """
    Report model for storing PDF report metadata
    """
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)
    
    # Report identification
    report_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Associated DICOM study
    study_instance_uid = db.Column(db.String(255), nullable=False, index=True)
    
    # Patient information (denormalized for quick access)
    patient_id = db.Column(db.String(20), db.ForeignKey('patients.id'), nullable=True, index=True)
    patient_name = db.Column(db.String(255))
    
    # Report details
    report_type = db.Column(db.String(50), default='DICOM Study Report')
    report_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date, index=True)
    
    # File storage
    file_path = db.Column(db.String(500), nullable=False)  # Path to PDF file
    file_size = db.Column(db.Integer)  # File size in bytes
    
    # Status
    status = db.Column(db.String(20), default='completed', nullable=False)  # completed, generating, failed
    generation_task_id = db.Column(db.String(100))  # Celery task ID if async

    # Report lifecycle (PDF spec §6): Draft → Validated → Archived; no modification after validation
    lifecycle_state = db.Column(db.String(20), default='draft', nullable=False, index=True)  # draft, validated, archived
    validated_at = db.Column(db.DateTime, nullable=True)
    validated_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True, index=True)
    accession_number = db.Column(db.String(64), nullable=True, index=True)  # Copy from order for PDF header

    # Metadata
    image_count = db.Column(db.Integer, default=0)
    generated_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    notes = db.Column(db.Text)
    
    # Relationships
    patient = db.relationship('Patient', backref='reports', lazy=True)
    generator = db.relationship('Admin', foreign_keys=[generated_by], backref='generated_reports', lazy=True)
    validator = db.relationship('Admin', foreign_keys=[validated_by], lazy=True)
    
    def to_dict(self):
        """Convert report to dictionary"""
        return {
            'id': self.id,
            'report_number': self.report_number,
            'study_instance_uid': self.study_instance_uid,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'report_type': self.report_type,
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'status': self.status,
            'lifecycle_state': self.lifecycle_state,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'validated_by': self.validated_by,
            'accession_number': self.accession_number,
            'image_count': self.image_count,
            'generated_by': self.generated_by,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
