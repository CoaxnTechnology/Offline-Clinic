"""
Seed Report Templates
Creates OB/GYN templates for structured reporting (English and French)
"""
from app import create_app
from app.extensions import db
from app.models import ReportTemplate
import json

app = create_app()

# Template definitions
TEMPLATES = [
    {
        'code': 'OB_1ST_TRIMESTER_EN',
        'name': '1st Trimester Scan',
        'template_type': 'OB',
        'category': '1st_trimester',
        'language': 'en',
        'fields': [
            {'code': 'crl', 'label': 'Crown-Rump Length', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'gestational_sac', 'label': 'Gestational Sac', 'type': 'text', 'required': False},
            {'code': 'yolk_sac', 'label': 'Yolk Sac', 'type': 'text', 'required': False},
            {'code': 'fetal_heart_rate', 'label': 'Fetal Heart Rate', 'type': 'number', 'unit': 'bpm', 'required': True},
            {'code': 'nt_measurement', 'label': 'Nuchal Translucency', 'type': 'number', 'unit': 'mm', 'required': False},
            {'code': 'ga_weeks', 'label': 'Gestational Age', 'type': 'number', 'unit': 'weeks', 'required': True},
            {'code': 'edd', 'label': 'Estimated Due Date', 'type': 'date', 'required': True},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True},
            {'code': 'recommendations', 'label': 'Recommendations', 'type': 'textarea', 'required': False}
        ],
        'required_fields': ['crl', 'fetal_heart_rate', 'ga_weeks', 'edd', 'impression']
    },
    {
        'code': 'OB_1ST_TRIMESTER_FR',
        'name': 'Échographie du 1er Trimestre',
        'template_type': 'OB',
        'category': '1st_trimester',
        'language': 'fr',
        'fields': [
            {'code': 'crl', 'label': 'Longueur Cranio-Caudale', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'gestational_sac', 'label': 'Sac Gestationnel', 'type': 'text', 'required': False},
            {'code': 'yolk_sac', 'label': 'Sac Vitellin', 'type': 'text', 'required': False},
            {'code': 'fetal_heart_rate', 'label': 'Fréquence Cardiaque Fœtale', 'type': 'number', 'unit': 'bpm', 'required': True},
            {'code': 'nt_measurement', 'label': 'Clarté Nucale', 'type': 'number', 'unit': 'mm', 'required': False},
            {'code': 'ga_weeks', 'label': 'Âge Gestationnel', 'type': 'number', 'unit': 'semaines', 'required': True},
            {'code': 'edd', 'label': 'Date Prévue d\'Accouchement', 'type': 'date', 'required': True},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True},
            {'code': 'recommendations', 'label': 'Recommandations', 'type': 'textarea', 'required': False}
        ],
        'required_fields': ['crl', 'fetal_heart_rate', 'ga_weeks', 'edd', 'impression']
    },
    {
        'code': 'OB_MORPHOLOGY_EN',
        'name': 'Morphology Scan',
        'template_type': 'OB',
        'category': 'morphology',
        'language': 'en',
        'fields': [
            {'code': 'bpd', 'label': 'Biparietal Diameter', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'hc', 'label': 'Head Circumference', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'ac', 'label': 'Abdominal Circumference', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'fl', 'label': 'Femur Length', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'efw', 'label': 'Estimated Fetal Weight', 'type': 'number', 'unit': 'g', 'required': True},
            {'code': 'ga_weeks', 'label': 'Gestational Age', 'type': 'number', 'unit': 'weeks', 'required': True},
            {'code': 'edd', 'label': 'Estimated Due Date', 'type': 'date', 'required': True},
            {'code': 'amniotic_fluid', 'label': 'Amniotic Fluid', 'type': 'text', 'required': False},
            {'code': 'placenta', 'label': 'Placenta', 'type': 'text', 'required': False},
            {'code': 'fetal_anatomy', 'label': 'Fetal Anatomy', 'type': 'textarea', 'required': True},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True},
            {'code': 'recommendations', 'label': 'Recommendations', 'type': 'textarea', 'required': False}
        ],
        'required_fields': ['bpd', 'hc', 'ac', 'fl', 'efw', 'ga_weeks', 'edd', 'fetal_anatomy', 'impression']
    },
    {
        'code': 'OB_MORPHOLOGY_FR',
        'name': 'Échographie Morphologique',
        'template_type': 'OB',
        'category': 'morphology',
        'language': 'fr',
        'fields': [
            {'code': 'bpd', 'label': 'Diamètre Bipariétal', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'hc', 'label': 'Circonférence Céphalique', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'ac', 'label': 'Circonférence Abdominale', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'fl', 'label': 'Longueur du Fémur', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'efw', 'label': 'Poids Fœtal Estimé', 'type': 'number', 'unit': 'g', 'required': True},
            {'code': 'ga_weeks', 'label': 'Âge Gestationnel', 'type': 'number', 'unit': 'semaines', 'required': True},
            {'code': 'edd', 'label': 'Date Prévue d\'Accouchement', 'type': 'date', 'required': True},
            {'code': 'amniotic_fluid', 'label': 'Liquide Amniotique', 'type': 'text', 'required': False},
            {'code': 'placenta', 'label': 'Placenta', 'type': 'text', 'required': False},
            {'code': 'fetal_anatomy', 'label': 'Anatomie Fœtale', 'type': 'textarea', 'required': True},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True},
            {'code': 'recommendations', 'label': 'Recommandations', 'type': 'textarea', 'required': False}
        ],
        'required_fields': ['bpd', 'hc', 'ac', 'fl', 'efw', 'ga_weeks', 'edd', 'fetal_anatomy', 'impression']
    },
    {
        'code': 'OB_GROWTH_EN',
        'name': 'Growth Scan',
        'template_type': 'OB',
        'category': 'growth',
        'language': 'en',
        'fields': [
            {'code': 'bpd', 'label': 'Biparietal Diameter', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'hc', 'label': 'Head Circumference', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'ac', 'label': 'Abdominal Circumference', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'fl', 'label': 'Femur Length', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'efw', 'label': 'Estimated Fetal Weight', 'type': 'number', 'unit': 'g', 'required': True},
            {'code': 'ga_weeks', 'label': 'Gestational Age', 'type': 'number', 'unit': 'weeks', 'required': True},
            {'code': 'percentile', 'label': 'Percentile', 'type': 'number', 'unit': '%', 'required': False},
            {'code': 'amniotic_fluid', 'label': 'Amniotic Fluid', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['bpd', 'hc', 'ac', 'fl', 'efw', 'ga_weeks', 'impression']
    },
    {
        'code': 'OB_GROWTH_FR',
        'name': 'Échographie de Croissance',
        'template_type': 'OB',
        'category': 'growth',
        'language': 'fr',
        'fields': [
            {'code': 'bpd', 'label': 'Diamètre Bipariétal', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'hc', 'label': 'Circonférence Céphalique', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'ac', 'label': 'Circonférence Abdominale', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'fl', 'label': 'Longueur du Fémur', 'type': 'number', 'unit': 'mm', 'required': True},
            {'code': 'efw', 'label': 'Poids Fœtal Estimé', 'type': 'number', 'unit': 'g', 'required': True},
            {'code': 'ga_weeks', 'label': 'Âge Gestationnel', 'type': 'number', 'unit': 'semaines', 'required': True},
            {'code': 'percentile', 'label': 'Percentile', 'type': 'number', 'unit': '%', 'required': False},
            {'code': 'amniotic_fluid', 'label': 'Liquide Amniotique', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['bpd', 'hc', 'ac', 'fl', 'efw', 'ga_weeks', 'impression']
    },
    {
        'code': 'OB_BPP_EN',
        'name': 'Biophysical Profile',
        'template_type': 'OB',
        'category': 'BPP',
        'language': 'en',
        'fields': [
            {'code': 'fetal_breathing', 'label': 'Fetal Breathing', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'fetal_movement', 'label': 'Fetal Movement', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'fetal_tone', 'label': 'Fetal Tone', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'amniotic_fluid_volume', 'label': 'Amniotic Fluid Volume', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'nst', 'label': 'Non-Stress Test', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'total_score', 'label': 'Total Score', 'type': 'number', 'unit': '/10', 'required': True},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['fetal_breathing', 'fetal_movement', 'fetal_tone', 'amniotic_fluid_volume', 'nst', 'total_score', 'impression']
    },
    {
        'code': 'OB_BPP_FR',
        'name': 'Profil Biophysique',
        'template_type': 'OB',
        'category': 'BPP',
        'language': 'fr',
        'fields': [
            {'code': 'fetal_breathing', 'label': 'Respiration Fœtale', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'fetal_movement', 'label': 'Mouvement Fœtal', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'fetal_tone', 'label': 'Tonus Fœtal', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'amniotic_fluid_volume', 'label': 'Volume de Liquide Amniotique', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'nst', 'label': 'Test de Non-Stress', 'type': 'number', 'unit': 'score', 'required': True},
            {'code': 'total_score', 'label': 'Score Total', 'type': 'number', 'unit': '/10', 'required': True},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['fetal_breathing', 'fetal_movement', 'fetal_tone', 'amniotic_fluid_volume', 'nst', 'total_score', 'impression']
    },
    {
        'code': 'GYN_PELVIC_EN',
        'name': 'Pelvic Ultrasound',
        'template_type': 'GYN',
        'category': 'pelvic',
        'language': 'en',
        'fields': [
            {'code': 'uterus', 'label': 'Uterus', 'type': 'textarea', 'required': True},
            {'code': 'endometrium', 'label': 'Endometrium', 'type': 'text', 'required': True},
            {'code': 'right_ovary', 'label': 'Right Ovary', 'type': 'textarea', 'required': False},
            {'code': 'left_ovary', 'label': 'Left Ovary', 'type': 'textarea', 'required': False},
            {'code': 'adnexa', 'label': 'Adnexa', 'type': 'textarea', 'required': False},
            {'code': 'cul_de_sac', 'label': 'Cul-de-sac', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['uterus', 'endometrium', 'impression']
    },
    {
        'code': 'GYN_PELVIC_FR',
        'name': 'Échographie Pelvienne',
        'template_type': 'GYN',
        'category': 'pelvic',
        'language': 'fr',
        'fields': [
            {'code': 'uterus', 'label': 'Utérus', 'type': 'textarea', 'required': True},
            {'code': 'endometrium', 'label': 'Endomètre', 'type': 'text', 'required': True},
            {'code': 'right_ovary', 'label': 'Ovaire Droit', 'type': 'textarea', 'required': False},
            {'code': 'left_ovary', 'label': 'Ovaire Gauche', 'type': 'textarea', 'required': False},
            {'code': 'adnexa', 'label': 'Annexes', 'type': 'textarea', 'required': False},
            {'code': 'cul_de_sac', 'label': 'Cul-de-sac', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['uterus', 'endometrium', 'impression']
    },
    {
        'code': 'GYN_TVUS_EN',
        'name': 'Transvaginal Ultrasound',
        'template_type': 'GYN',
        'category': 'TVUS',
        'language': 'en',
        'fields': [
            {'code': 'uterus', 'label': 'Uterus', 'type': 'textarea', 'required': True},
            {'code': 'endometrium', 'label': 'Endometrium', 'type': 'text', 'required': True},
            {'code': 'right_ovary', 'label': 'Right Ovary', 'type': 'textarea', 'required': False},
            {'code': 'left_ovary', 'label': 'Left Ovary', 'type': 'textarea', 'required': False},
            {'code': 'cervix', 'label': 'Cervix', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['uterus', 'endometrium', 'impression']
    },
    {
        'code': 'GYN_TVUS_FR',
        'name': 'Échographie Endovaginale',
        'template_type': 'GYN',
        'category': 'TVUS',
        'language': 'fr',
        'fields': [
            {'code': 'uterus', 'label': 'Utérus', 'type': 'textarea', 'required': True},
            {'code': 'endometrium', 'label': 'Endomètre', 'type': 'text', 'required': True},
            {'code': 'right_ovary', 'label': 'Ovaire Droit', 'type': 'textarea', 'required': False},
            {'code': 'left_ovary', 'label': 'Ovaire Gauche', 'type': 'textarea', 'required': False},
            {'code': 'cervix', 'label': 'Col de l\'Utérus', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['uterus', 'endometrium', 'impression']
    },
    {
        'code': 'GYN_FOLLICULAR_EN',
        'name': 'Follicular Monitoring',
        'template_type': 'GYN',
        'category': 'follicular',
        'language': 'en',
        'fields': [
            {'code': 'cycle_day', 'label': 'Cycle Day', 'type': 'number', 'required': True},
            {'code': 'right_ovary_follicles', 'label': 'Right Ovary Follicles', 'type': 'textarea', 'required': False},
            {'code': 'left_ovary_follicles', 'label': 'Left Ovary Follicles', 'type': 'textarea', 'required': False},
            {'code': 'endometrium', 'label': 'Endometrium', 'type': 'text', 'required': True},
            {'code': 'dominant_follicle', 'label': 'Dominant Follicle', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Findings', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['cycle_day', 'endometrium', 'impression']
    },
    {
        'code': 'GYN_FOLLICULAR_FR',
        'name': 'Suivi Folliculaire',
        'template_type': 'GYN',
        'category': 'follicular',
        'language': 'fr',
        'fields': [
            {'code': 'cycle_day', 'label': 'Jour du Cycle', 'type': 'number', 'required': True},
            {'code': 'right_ovary_follicles', 'label': 'Follicules Ovaire Droit', 'type': 'textarea', 'required': False},
            {'code': 'left_ovary_follicles', 'label': 'Follicules Ovaire Gauche', 'type': 'textarea', 'required': False},
            {'code': 'endometrium', 'label': 'Endomètre', 'type': 'text', 'required': True},
            {'code': 'dominant_follicle', 'label': 'Follicule Dominant', 'type': 'text', 'required': False},
            {'code': 'findings', 'label': 'Constations', 'type': 'textarea', 'required': False},
            {'code': 'impression', 'label': 'Impression', 'type': 'textarea', 'required': True}
        ],
        'required_fields': ['cycle_day', 'endometrium', 'impression']
    }
]


def seed_templates():
    """Seed report templates"""
    with app.app_context():
        created = 0
        updated = 0
        
        for template_data in TEMPLATES:
            template = ReportTemplate.query.filter_by(code=template_data['code']).first()
            
            if template:
                # Update existing template
                template.name = template_data['name']
                template.template_type = template_data['template_type']
                template.category = template_data['category']
                template.language = template_data['language']
                template.set_fields(template_data['fields'])
                template.set_required_fields(template_data['required_fields'])
                template.is_active = True
                updated += 1
            else:
                # Create new template
                template = ReportTemplate(
                    code=template_data['code'],
                    name=template_data['name'],
                    template_type=template_data['template_type'],
                    category=template_data['category'],
                    language=template_data['language'],
                    is_active=True
                )
                template.set_fields(template_data['fields'])
                template.set_required_fields(template_data['required_fields'])
                db.session.add(template)
                created += 1
        
        db.session.commit()
        print(f"Seeded {created} new templates, updated {updated} existing templates")


if __name__ == '__main__':
    seed_templates()
