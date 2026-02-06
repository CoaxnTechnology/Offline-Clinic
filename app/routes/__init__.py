from .auth import auth_bp
from .patient import patient_bp
from .appointment import appointment_bp
from .admin import admin_bp
from .dicom import dicom_bp
from .health import health_bp
from .reporting import reporting_bp
from .prescription import prescription_bp

__all__ = ['auth_bp', 'patient_bp', 'appointment_bp', 'admin_bp', 'dicom_bp', 'health_bp', 'reporting_bp', 'prescription_bp']
