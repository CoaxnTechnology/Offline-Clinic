"""
Report Template Model
Structured OB/GYN templates for report generation (PDF spec §5)
"""
from app.extensions import db
from .base import TimestampMixin
import json


class ReportTemplate(db.Model, TimestampMixin):
    """
    Report template for structured OB/GYN reporting
    
    Templates define:
    - Fields (measurements, findings, etc.)
    - Required fields (must be filled before validation)
    - Field types (text, number, select, etc.)
    - Language (English/French)
    """
    __tablename__ = 'report_templates'

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'), nullable=True, index=True)
    
    # Template identification
    name = db.Column(db.String(100), nullable=False)  # e.g., "1st Trimester Scan"
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., "OB_1ST_TRIMESTER"
    
    # Template type and category
    template_type = db.Column(db.String(20), nullable=False, index=True)  # 'OB' or 'GYN'
    category = db.Column(db.String(50), nullable=False, index=True)  # '1st_trimester', 'morphology', 'growth', 'BPP', 'pelvic', 'TVUS', 'follicular'
    
    # Language
    language = db.Column(db.String(10), default='en', nullable=False, index=True)  # 'en' or 'fr'
    
    # Template structure (JSON)
    fields = db.Column(db.Text, nullable=False)  # JSON array of field definitions
    required_fields = db.Column(db.Text)  # JSON array of required field codes
    
    # Display order and grouping
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    clinic = db.relationship('Clinic', backref='report_templates', lazy=True)
    
    def get_fields(self):
        """Parse and return fields JSON"""
        try:
            return json.loads(self.fields) if self.fields else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_required_fields(self):
        """Parse and return required fields JSON"""
        try:
            return json.loads(self.required_fields) if self.required_fields else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_fields(self, fields_list):
        """Set fields from list"""
        self.fields = json.dumps(fields_list, ensure_ascii=False)
    
    def set_required_fields(self, required_list):
        """Set required fields from list"""
        self.required_fields = json.dumps(required_list, ensure_ascii=False)
    
    def __repr__(self):
        return f"<ReportTemplate {self.code} - {self.name} ({self.language})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'template_type': self.template_type,
            'category': self.category,
            'language': self.language,
            'fields': self.get_fields(),
            'required_fields': self.get_required_fields(),
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
