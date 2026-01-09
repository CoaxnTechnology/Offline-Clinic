from app.extensions import db
from .base import TimestampMixin

class DicomStudy(db.Model, TimestampMixin):
    __tablename__ = 'dicom_studies'

    id = db.Column(db.Integer, primary_key=True)
    study_instance_uid = db.Column(db.String(255), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.String(20), db.ForeignKey('patients.id'), nullable=False, index=True)
    
    # Study Information
    study_date = db.Column(db.Date, nullable=False, index=True)
    study_time = db.Column(db.String(20))  # HHMMSS.FFFFFF
    study_description = db.Column(db.String(255))
    accession_number = db.Column(db.String(50), index=True)
    referring_physician = db.Column(db.String(255))
    institution_name = db.Column(db.String(255))
    
    # Relationships
    patient = db.relationship('Patient', backref='dicom_studies')
    series = db.relationship('DicomSeries', backref='study', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<DicomStudy {self.study_instance_uid} - Patient {self.patient_id}>"
