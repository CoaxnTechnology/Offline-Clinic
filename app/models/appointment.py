from app.extensions import db
from .base import TimestampMixin
from datetime import datetime

class Appointment(db.Model, TimestampMixin):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)
    patient_id = db.Column(db.String(20), db.ForeignKey('patients.id'), nullable=False)

    doctor = db.Column(db.String(100), nullable=False)  # e.g., Dr. Sharma
    department = db.Column(db.String(100))  # e.g., Gynecology, Radiology
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)  # e.g., "10:45"

    # Status from PDF + frontend: Waiting → In-Room → In-Scan → Review → Completed
    status = db.Column(db.String(30), default='Waiting')
    # Possible values: Waiting, In-Room, In-Scan, With Doctor, With Technician, Review, Completed

    def __repr__(self):
        return f"<Appointment {self.patient_id} - {self.doctor} on {self.date} {self.time}>"