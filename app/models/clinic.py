"""
Clinic Model for Multi-Tenant Support (Free - No Subscription)
"""
from datetime import datetime
from app.extensions import db


class Clinic(db.Model):
    """Clinic model - each clinic is a separate tenant (FREE)"""
    __tablename__ = 'clinics'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    
    # License (for identification only - no expiry)
    license_key = db.Column(db.String(50), unique=True, nullable=False)
    max_doctors = db.Column(db.Integer, default=1)  # 1 doctor per clinic
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    admins = db.relationship('Admin', backref='clinic', lazy='dynamic')
    patients = db.relationship('Patient', backref='clinic', lazy='dynamic')
    appointments = db.relationship('Appointment', backref='clinic', lazy='dynamic')
    
    def is_valid(self):
        """Check if clinic is active"""
        return self.is_active
    
    def get_doctor_count(self):
        """Get number of doctors in clinic"""
        from app.models import Admin
        return Admin.query.filter_by(clinic_id=self.id, role='doctor').count()
    
    def can_add_doctor(self):
        """Check if clinic can add more doctors (limit: 1)"""
        return self.get_doctor_count() < self.max_doctors
    
    def get_patient_count(self):
        """Get number of patients in clinic"""
        from app.models import Patient
        return Patient.query.filter_by(clinic_id=self.id).count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'license_key': self.license_key,
            'max_doctors': self.max_doctors,
            'is_active': self.is_active,
            'doctor_count': self.get_doctor_count(),
            'patient_count': self.get_patient_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
