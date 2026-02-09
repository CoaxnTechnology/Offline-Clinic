"""
Internationalization (i18n) Utilities
Multi-language support for templates and UI (PDF spec §5: English & French)
"""
import logging

logger = logging.getLogger(__name__)

# Translation dictionaries
TRANSLATIONS = {
    'en': {
        # Common
        'patient': 'Patient',
        'patient_id': 'Patient ID',
        'patient_name': 'Patient Name',
        'date_of_birth': 'Date of Birth',
        'age': 'Age',
        'gender': 'Gender',
        'prescription': 'Prescription',
        'report': 'Report',
        'appointment': 'Appointment',
        'visit': 'Visit',
        'doctor': 'Doctor',
        'technician': 'Technician',
        'receptionist': 'Receptionist',
        'date': 'Date',
        'time': 'Time',
        'status': 'Status',
        'medicine': 'Medicine',
        'dosage': 'Dosage',
        'duration': 'Duration',
        'notes': 'Notes',
        'prescribed_by': 'Prescribed by',
        'waiting': 'Waiting',
        'with_doctor': 'With Doctor',
        'with_technician': 'With Technician',
        'completed': 'Completed',
        'draft': 'Draft',
        'validated': 'Validated',
        'archived': 'Archived',
        # OB/GYN
        'gestational_age': 'Gestational Age',
        'estimated_due_date': 'Estimated Due Date',
        'crown_rump_length': 'Crown-Rump Length',
        'biparietal_diameter': 'Biparietal Diameter',
        'head_circumference': 'Head Circumference',
        'abdominal_circumference': 'Abdominal Circumference',
        'femur_length': 'Femur Length',
        'estimated_fetal_weight': 'Estimated Fetal Weight',
        'percentile': 'Percentile',
        'first_trimester': '1st Trimester Scan',
        'morphology': 'Morphology Scan',
        'growth': 'Growth Scan',
        'bpp': 'Biophysical Profile',
        'pelvic': 'Pelvic Ultrasound',
        'tvus': 'Transvaginal Ultrasound',
        'follicular': 'Follicular Monitoring',
    },
    'fr': {
        # Common
        'patient': 'Patient',
        'patient_id': 'ID Patient',
        'patient_name': 'Nom du Patient',
        'date_of_birth': 'Date de Naissance',
        'age': 'Âge',
        'gender': 'Sexe',
        'prescription': 'Ordonnance',
        'report': 'Rapport',
        'appointment': 'Rendez-vous',
        'visit': 'Visite',
        'doctor': 'Médecin',
        'technician': 'Technicien',
        'receptionist': 'Réceptionniste',
        'date': 'Date',
        'time': 'Heure',
        'status': 'Statut',
        'medicine': 'Médicament',
        'dosage': 'Posologie',
        'duration': 'Durée',
        'notes': 'Notes',
        'prescribed_by': 'Prescrit par',
        'waiting': 'En Attente',
        'with_doctor': 'Avec le Médecin',
        'with_technician': 'Avec le Technicien',
        'completed': 'Terminé',
        'draft': 'Brouillon',
        'validated': 'Validé',
        'archived': 'Archivé',
        # OB/GYN
        'gestational_age': 'Âge Gestationnel',
        'estimated_due_date': 'Date Prévue d\'Accouchement',
        'crown_rump_length': 'Longueur Cranio-Caudale',
        'biparietal_diameter': 'Diamètre Bipariétal',
        'head_circumference': 'Circonférence Céphalique',
        'abdominal_circumference': 'Circonférence Abdominale',
        'femur_length': 'Longueur du Fémur',
        'estimated_fetal_weight': 'Poids Fœtal Estimé',
        'percentile': 'Percentile',
        'first_trimester': 'Échographie du 1er Trimestre',
        'morphology': 'Échographie Morphologique',
        'growth': 'Échographie de Croissance',
        'bpp': 'Profil Biophysique',
        'pelvic': 'Échographie Pelvienne',
        'tvus': 'Échographie Endovaginale',
        'follicular': 'Suivi Folliculaire',
    }
}


def get_translation(key, language='en', default=None):
    """
    Get translation for a key in the specified language
    
    Args:
        key: Translation key
        language: 'en' or 'fr'
        default: Default value if key not found
    
    Returns:
        str: Translated text
    """
    lang = language.lower() if language else 'en'
    if lang not in TRANSLATIONS:
        lang = 'en'
    
    translations = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
    return translations.get(key, default or key)


def translate_template_fields(template_fields, language='en'):
    """
    Translate template field labels to the specified language
    
    Args:
        template_fields: List of field dicts with 'label' key
        language: 'en' or 'fr'
    
    Returns:
        list: Translated field dicts
    """
    if not template_fields:
        return []
    
    translated = []
    for field in template_fields:
        field_copy = field.copy()
        if 'label' in field_copy:
            # Try to translate label if it's a known key
            label_key = field_copy['label'].lower().replace(' ', '_')
            translated_label = get_translation(label_key, language, field_copy['label'])
            field_copy['label'] = translated_label
        translated.append(field_copy)
    
    return translated
