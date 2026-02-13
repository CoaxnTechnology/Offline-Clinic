from app.extensions import db
from .base import TimestampMixin
from datetime import datetime


class DicomImage(db.Model, TimestampMixin):
    """
    Unified DICOM model - stores all DICOM data (Study, Series, Image) in one table
    """

    __tablename__ = "dicom_images"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(
        db.Integer, db.ForeignKey("clinics.id"), nullable=True, index=True
    )

    # DICOM Identifiers (Study, Series, Image)
    sop_instance_uid = db.Column(
        db.String(255), unique=True, nullable=False, index=True
    )
    study_instance_uid = db.Column(db.String(255), nullable=False, index=True)
    series_instance_uid = db.Column(db.String(255), nullable=False, index=True)

    # Patient Information
    patient_id = db.Column(
        db.String(20), db.ForeignKey("patients.id"), nullable=True, index=True
    )
    patient_name = db.Column(db.String(255))
    patient_birth_date = db.Column(db.Date)
    patient_sex = db.Column(db.String(10))

    # Visit/Appointment Links
    visit_id = db.Column(
        db.Integer, db.ForeignKey("visits.id"), nullable=True, index=True
    )
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=True, index=True
    )

    # Study Information
    study_date = db.Column(db.Date, nullable=False, index=True)
    study_time = db.Column(db.String(20))
    study_description = db.Column(db.String(255))
    accession_number = db.Column(db.String(50), index=True)
    referring_physician = db.Column(db.String(255))
    institution_name = db.Column(db.String(255))

    # Series Information
    series_number = db.Column(db.Integer)
    series_description = db.Column(db.String(255))
    series_date = db.Column(db.Date)
    series_time = db.Column(db.String(20))
    modality = db.Column(db.String(10), nullable=False, index=True)  # US, CT, MR, etc.
    body_part_examined = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100))
    manufacturer_model_name = db.Column(db.String(100))

    # Image Information
    instance_number = db.Column(db.Integer)

    # File Storage
    file_path = db.Column(db.String(500), nullable=False)  # Path to .dcm file
    thumbnail_path = db.Column(db.String(500))  # Path to thumbnail image

    # Additional Metadata (JSON)
    # Note: Using 'dicom_metadata' instead of 'metadata' because 'metadata' is reserved in SQLAlchemy
    dicom_metadata = db.Column(db.Text)  # Store additional DICOM tags as JSON

    # Relationships
    patient = db.relationship("Patient", backref="dicom_images", lazy=True)
    visit = db.relationship("Visit", backref="dicom_images", lazy=True)
    appointment = db.relationship("Appointment", backref="dicom_images", lazy=True)

    def __repr__(self):
        return f"<DicomImage {self.sop_instance_uid} - {self.patient_name}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "sop_instance_uid": self.sop_instance_uid,
            "study_instance_uid": self.study_instance_uid,
            "series_instance_uid": self.series_instance_uid,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "patient_birth_date": self.patient_birth_date.isoformat()
            if self.patient_birth_date
            else None,
            "patient_sex": self.patient_sex,
            "accession_number": self.accession_number,
            "study_date": self.study_date.isoformat() if self.study_date else None,
            "study_time": self.study_time,
            "study_description": self.study_description,
            "referring_physician": self.referring_physician,
            "institution_name": self.institution_name,
            "series_number": self.series_number,
            "series_description": self.series_description,
            "series_date": self.series_date.isoformat() if self.series_date else None,
            "series_time": self.series_time,
            "modality": self.modality,
            "body_part_examined": self.body_part_examined,
            "manufacturer": self.manufacturer,
            "manufacturer_model_name": self.manufacturer_model_name,
            "instance_number": self.instance_number,
            "file_path": self.file_path,
            "thumbnail_path": self.thumbnail_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "visit_id": self.visit_id,
            "appointment_id": self.appointment_id,
        }


class DicomMeasurement(db.Model, TimestampMixin):
    """
    Model to store measurements extracted from DICOM images
    """

    __tablename__ = "dicom_measurements"

    id = db.Column(db.Integer, primary_key=True)

    # Link to DICOM Image
    dicom_image_id = db.Column(
        db.Integer, db.ForeignKey("dicom_images.id"), nullable=False
    )

    # Patient/Study Information
    patient_id = db.Column(
        db.String(20), db.ForeignKey("patients.id"), nullable=True, index=True
    )
    study_instance_uid = db.Column(db.String(255), index=True)

    # Measurement Data
    measurement_type = db.Column(
        db.String(100)
    )  # e.g., "Liver", "Gallbladder", "Kidney"
    measurement_value = db.Column(db.String(255))  # e.g., "12.5 cm", "Normal"
    measurement_data = db.Column(db.Text)  # JSON string for complex measurements

    # Relationships
    dicom_image = db.relationship("DicomImage", backref="measurements", lazy=True)
    patient = db.relationship("Patient", backref="dicom_measurements", lazy=True)

    def __repr__(self):
        return f"<DicomMeasurement {self.measurement_type}: {self.measurement_value}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "dicom_image_id": self.dicom_image_id,
            "patient_id": self.patient_id,
            "study_instance_uid": self.study_instance_uid,
            "measurement_type": self.measurement_type,
            "measurement_value": self.measurement_value,
            "measurement_data": self.measurement_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
