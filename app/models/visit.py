"""
Visit/Order Model
Represents a single visit/order that maps to one study and one report (PDF spec: One Visit = One Study = One Report)
"""
from app.extensions import db
from .base import TimestampMixin
from datetime import datetime


class Visit(db.Model, TimestampMixin):
    """
    Visit/Order model - One Visit = One Study (via AccessionNumber) = One Report
    
    A Visit is created when an appointment is scheduled or when MWL is first sent.
    Each Visit has exactly one AccessionNumber, which maps to one DICOM Study and one Report.
    """
    __tablename__ = 'visits'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)
    
    # Link to Appointment (visit is created from appointment)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False, unique=True, index=True)
    patient_id = db.Column(db.String(20), db.ForeignKey('patients.id'), nullable=False, index=True)
    
    # AccessionNumber - immutable, unique, study matching key (PDF spec §4)
    accession_number = db.Column(db.String(64), unique=True, nullable=True, index=True)
    
    # Visit metadata
    visit_date = db.Column(db.Date, nullable=False, index=True)
    visit_status = db.Column(db.String(30), default='scheduled')  # scheduled, in_progress, completed, cancelled
    
    # Exam details
    exam_type = db.Column(db.String(100))  # e.g., "OB/GYN Ultrasound", "1st Trimester Scan"
    modality = db.Column(db.String(10), default='US')  # US, CT, MR, etc.
    
    # DICOM identifiers (copied from Appointment when MWL is sent)
    requested_procedure_id = db.Column(db.String(64), nullable=True, index=True)
    scheduled_procedure_step_id = db.Column(db.String(64), nullable=True, index=True)
    study_instance_uid = db.Column(db.String(255), nullable=True, index=True)  # Set when DICOM study is received
    
    # Created by (secretary/receptionist)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True, index=True)
    
    # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    appointment = db.relationship('Appointment', backref='visit', uselist=False, lazy=True)
    patient = db.relationship('Patient', backref='visits', lazy=True)
    creator = db.relationship('Admin', foreign_keys=[created_by], backref='created_visits', lazy=True)
    
    def __repr__(self):
        return f"<Visit {self.id} - Patient: {self.patient_id} - Accession: {self.accession_number}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'patient_id': self.patient_id,
            'accession_number': self.accession_number,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'visit_status': self.visit_status,
            'exam_type': self.exam_type,
            'modality': self.modality,
            'requested_procedure_id': self.requested_procedure_id,
            'scheduled_procedure_step_id': self.scheduled_procedure_step_id,
            'study_instance_uid': self.study_instance_uid,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
