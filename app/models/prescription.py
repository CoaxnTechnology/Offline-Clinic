from app.extensions import db
from .base import TimestampMixin
from datetime import datetime
import json


class Prescription(db.Model, TimestampMixin):
    """
    Prescription model - stores prescription data and PDF path.

    Supports:
    - Single medicine via medicine/dosage/duration_days/notes
    - Multiple medicines via items_json (list of dicts)
    """

    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)

    # Patient reference
    patient_id = db.Column(
        db.String(20), db.ForeignKey("patients.id"), nullable=False, index=True
    )

    # Visit reference (each visit can have a prescription)
    visit_id = db.Column(
        db.Integer, db.ForeignKey("visits.id"), nullable=True, index=True
    )

    # Prescription details (single-medicine, kept for backwards compatibility)
    medicine = db.Column(db.String(255), nullable=False)  # Medicine name
    dosage = db.Column(db.String(50), nullable=False)  # e.g., "1-0-1"
    duration_days = db.Column(db.Integer, nullable=False)  # Duration in days
    notes = db.Column(db.Text, nullable=True)  # Additional notes/instructions

    # Multiple medicines (JSON list: [{medicine, dosage, duration_days, notes}, ...])
    items_json = db.Column(db.Text, nullable=True)

    # PDF storage
    pdf_path = db.Column(db.String(500), nullable=True)  # Path to generated PDF

    # Doctor who created the prescription
    created_by = db.Column(
        db.Integer, db.ForeignKey("admins.id"), nullable=True, index=True
    )

    # Relationships
    patient = db.relationship("Patient", backref="prescriptions", lazy=True)
    visit = db.relationship("Visit", backref="prescription", lazy=True)
    doctor = db.relationship(
        "Admin", foreign_keys=[created_by], backref="prescriptions", lazy=True
    )

    def __repr__(self):
        return f"<Prescription {self.id} - Patient: {self.patient_id}>"
    
    @property
    def items(self):
        """
        Return list of medicines for this prescription.
        If items_json is set, parse and return it.
        Otherwise, build a single-item list from legacy fields.
        """
        if self.items_json:
            try:
                data = json.loads(self.items_json)
                if isinstance(data, list):
                    return data
            except (TypeError, json.JSONDecodeError):
                pass
        
        return [
            {
                "medicine": self.medicine,
                "dosage": self.dosage,
                "duration_days": self.duration_days,
                "notes": self.notes or "",
            }
        ]

    def to_dict(self):
        """Convert to dictionary for API responses."""
        # Expose pdf_path as a web path (relative URL) pointing to the PDF file,
        # not as an internal filesystem path or API download endpoint.
        # Example value: "/reports/prescriptions/prescription_PAT004_11_20260210_063914.pdf"
        if self.pdf_path:
            if self.pdf_path.startswith("/"):
                web_path = self.pdf_path
            else:
                web_path = f"/{self.pdf_path}"
        else:
            web_path = None
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "visit_id": self.visit_id,
            "medicine": self.medicine,
            "dosage": self.dosage,
            "duration_days": self.duration_days,
            "notes": self.notes or "",
            "items": self.items,
            # Browser-linkable path; prefix with your server, e.g.
            # http://SERVER + pdf_path
            "pdf_path": web_path,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
