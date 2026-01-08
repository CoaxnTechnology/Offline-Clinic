from .auth import auth_bp
from .patient import patient_bp
from .appointment import appointment_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'patient_bp', 'appointment_bp', 'admin_bp']
