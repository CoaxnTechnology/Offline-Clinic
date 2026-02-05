from app.extensions import db
from .base import TimestampMixin
from datetime import date

class Patient(db.Model, TimestampMixin):
    __tablename__ = 'patients'

    id = db.Column(db.String(20), primary_key=True)  # e.g., P001
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)

    # Personal
    title = db.Column(db.String(10))  # Mr, Ms, Mrs
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    maiden_name = db.Column(db.String(100))  # Additional surname field
    gender = db.Column(db.String(20))
    birth_date = db.Column(db.Date)  # DOB
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)

    
    identity_number = db.Column(db.String(50))
    social_security_number = db.Column(db.String(50))
    secondary_phone = db.Column(db.String(20))
    other_phone = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    height = db.Column(db.Float)  # cm
    weight = db.Column(db.Float)   # kg
    blood_group = db.Column(db.String(5))
    smoker = db.Column(db.String(3))  # Yes/No
    cigarettes_per_day = db.Column(db.Integer)
    family_history = db.Column(db.Text)
    medical_history = db.Column(db.Text)  # medical / surgical
    gynecological_history = db.Column(db.Text)
    allergies = db.Column(db.Text)
    notes = db.Column(db.Text)
    primary_doctor = db.Column(db.String(100))
    delivery_location = db.Column(db.String(100))
    legacy_number = db.Column(db.String(50))
    new_patient = db.Column(db.Boolean, default=True)  # True = New, False = Existing

    # Demographics (free-form or JSON for future extensions)
    demographics = db.Column(db.Text)

    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy='dynamic')
    
    def __repr__(self):
        return f"<Patient {self.first_name} {self.last_name} ({self.id})>"