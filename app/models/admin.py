from app.extensions import db, bcrypt
from .base import TimestampMixin
from flask_login import UserMixin

class Admin(db.Model, TimestampMixin, UserMixin):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    
    # Role - only 3 options: 'doctor', 'technician', 'receptionist'
    role = db.Column(db.String(20), nullable=False, index=True)
    # Possible values: 'doctor', 'technician', 'receptionist'
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)  # Super admin bypasses all permissions
    
    # Last login tracking
    last_login = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """Check if admin has a specific role"""
        return self.role == role_name
    
    def has_any_role(self, *role_names):
        """Check if admin has any of the specified roles"""
        return self.role in role_names
    
    def is_doctor(self):
        """Check if admin is a doctor"""
        return self.role == 'doctor'
    
    def is_technician(self):
        """Check if admin is a technician"""
        return self.role == 'technician'
    
    def is_receptionist(self):
        """Check if admin is a receptionist"""
        return self.role == 'receptionist'
    
    def is_super_admin_user(self):
        """Check if admin is super admin"""
        return self.is_super_admin
    
    def __repr__(self):
        return f"<Admin {self.username} ({self.first_name} {self.last_name}) - {self.role}>"
