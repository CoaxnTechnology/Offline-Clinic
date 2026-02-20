"""
Database seed data — runs once on app startup if tables are empty.
"""
import json
import logging

from app.extensions import db
from app.models import ReportTemplate

logger = logging.getLogger(__name__)

REPORT_TEMPLATES = [
    {
        "name": "1st Trimester Scan",
        "code": "OB_1ST_TRIMESTER",
        "template_type": "OB",
        "category": "1st_trimester",
        "language": "en",
        "display_order": 1,
        "fields": [
            {"code": "crl", "label": "CRL (mm)", "type": "number"},
            {"code": "fetal_heart_rate", "label": "Fetal Heart Rate (bpm)", "type": "number"},
            {"code": "ga_weeks", "label": "Gestational Age (weeks)", "type": "number"},
            {"code": "ga_days", "label": "Gestational Age (days)", "type": "number"},
            {"code": "edd", "label": "EDD", "type": "date"},
            {"code": "yolk_sac", "label": "Yolk Sac", "type": "text"},
            {"code": "placenta", "label": "Placenta", "type": "text"},
            {"code": "amniotic_fluid", "label": "Amniotic Fluid", "type": "text"},
            {"code": "findings", "label": "Findings", "type": "textarea"},
            {"code": "impression", "label": "Impression", "type": "textarea"},
        ],
        "required_fields": ["crl", "fetal_heart_rate", "impression"],
    },
    {
        "name": "2nd/3rd Trimester Growth Scan",
        "code": "OB_GROWTH",
        "template_type": "OB",
        "category": "growth",
        "language": "en",
        "display_order": 2,
        "fields": [
            {"code": "bpd", "label": "BPD (mm)", "type": "number"},
            {"code": "hc", "label": "HC (mm)", "type": "number"},
            {"code": "ac", "label": "AC (mm)", "type": "number"},
            {"code": "fl", "label": "FL (mm)", "type": "number"},
            {"code": "efw", "label": "EFW (g)", "type": "number"},
            {"code": "ga_weeks", "label": "Gestational Age (weeks)", "type": "number"},
            {"code": "ga_days", "label": "Gestational Age (days)", "type": "number"},
            {"code": "edd", "label": "EDD", "type": "date"},
            {"code": "fetal_heart_rate", "label": "Fetal Heart Rate (bpm)", "type": "number"},
            {"code": "placenta", "label": "Placenta Location", "type": "text"},
            {"code": "afi", "label": "AFI (cm)", "type": "number"},
            {"code": "presentation", "label": "Presentation", "type": "text"},
            {"code": "findings", "label": "Findings", "type": "textarea"},
            {"code": "impression", "label": "Impression", "type": "textarea"},
        ],
        "required_fields": ["bpd", "hc", "ac", "fl", "impression"],
    },
    {
        "name": "Gynecological Pelvic Scan",
        "code": "GYN_PELVIC",
        "template_type": "GYN",
        "category": "pelvic",
        "language": "en",
        "display_order": 3,
        "fields": [
            {"code": "uterus_length", "label": "Uterus Length (mm)", "type": "number"},
            {"code": "uterus_width", "label": "Uterus Width (mm)", "type": "number"},
            {"code": "uterus_ap", "label": "Uterus AP (mm)", "type": "number"},
            {"code": "endometrium", "label": "Endometrial Thickness (mm)", "type": "number"},
            {"code": "right_ovary_length", "label": "Right Ovary Length (mm)", "type": "number"},
            {"code": "right_ovary_width", "label": "Right Ovary Width (mm)", "type": "number"},
            {"code": "left_ovary_length", "label": "Left Ovary Length (mm)", "type": "number"},
            {"code": "left_ovary_width", "label": "Left Ovary Width (mm)", "type": "number"},
            {"code": "free_fluid", "label": "Free Fluid", "type": "text"},
            {"code": "findings", "label": "Findings", "type": "textarea"},
            {"code": "impression", "label": "Impression", "type": "textarea"},
        ],
        "required_fields": ["uterus_length", "endometrium", "impression"],
    },
]


def seed_report_templates():
    """Create default report templates if none exist."""
    try:
        if ReportTemplate.query.count() == 0:
            for tpl in REPORT_TEMPLATES:
                t = ReportTemplate(
                    name=tpl["name"],
                    code=tpl["code"],
                    template_type=tpl["template_type"],
                    category=tpl["category"],
                    language=tpl["language"],
                    display_order=tpl["display_order"],
                    is_active=True,
                    fields=json.dumps(tpl["fields"]),
                    required_fields=json.dumps(tpl["required_fields"]),
                )
                db.session.add(t)
            db.session.commit()
            logger.info("Seeded %d default report templates", len(REPORT_TEMPLATES))
    except Exception as e:
        db.session.rollback()
        logger.warning("Report template seeding skipped: %s", e)
