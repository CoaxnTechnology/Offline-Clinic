from app.extensions import db
from .base import TimestampMixin

class DicomSeries(db.Model, TimestampMixin):
    __tablename__ = 'dicom_series'

    id = db.Column(db.Integer, primary_key=True)
    series_instance_uid = db.Column(db.String(255), unique=True, nullable=False, index=True)
    study_id = db.Column(db.Integer, db.ForeignKey('dicom_studies.id'), nullable=False, index=True)
    
    # Series Information
    modality = db.Column(db.String(10), nullable=False, index=True)  # US, CT, MR, etc.
    series_number = db.Column(db.Integer)
    series_description = db.Column(db.String(255))
    body_part_examined = db.Column(db.String(100))
    series_date = db.Column(db.Date)
    series_time = db.Column(db.String(20))
    manufacturer = db.Column(db.String(100))
    manufacturer_model_name = db.Column(db.String(100))
    
    # Relationships
    images = db.relationship('DicomImage', backref='series', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<DicomSeries {self.series_instance_uid} - {self.modality}>"
