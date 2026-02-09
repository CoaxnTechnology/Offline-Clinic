"""
OB/GYN Calculation Utilities
GA (Gestational Age), EDD (Estimated Due Date), Percentiles (PDF spec §5)
"""
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_ga_from_crl(crl_mm):
    """
    Calculate Gestational Age from Crown-Rump Length (CRL)
    
    Args:
        crl_mm: CRL in millimeters
    
    Returns:
        dict: {'weeks': int, 'days': int, 'total_days': int, 'formatted': str}
    """
    if not crl_mm or crl_mm <= 0:
        return None
    
    # Robinson formula: GA (days) = 8.052 * sqrt(CRL) + 23.73
    # Or Hadlock: GA (days) = 5.608563 + (0.815392 * CRL) + (0.001601 * CRL^2)
    # Using Robinson (more common for early pregnancy)
    ga_days = 8.052 * (crl_mm ** 0.5) + 23.73
    
    weeks = int(ga_days // 7)
    days = int(ga_days % 7)
    
    return {
        'weeks': weeks,
        'days': days,
        'total_days': int(ga_days),
        'formatted': f"{weeks}+{days} weeks"
    }


def calculate_ga_from_lmp(lmp_date):
    """
    Calculate Gestational Age from Last Menstrual Period (LMP)
    
    Args:
        lmp_date: LMP date (datetime.date)
    
    Returns:
        dict: {'weeks': int, 'days': int, 'total_days': int, 'formatted': str}
    """
    if not lmp_date:
        return None
    
    today = datetime.now().date()
    delta = today - lmp_date
    
    if delta.days < 0:
        return None
    
    weeks = delta.days // 7
    days = delta.days % 7
    
    return {
        'weeks': weeks,
        'days': days,
        'total_days': delta.days,
        'formatted': f"{weeks}+{days} weeks"
    }


def calculate_edd_from_lmp(lmp_date):
    """
    Calculate Estimated Due Date from LMP (Naegele's rule: LMP + 280 days)
    
    Args:
        lmp_date: LMP date (datetime.date)
    
    Returns:
        datetime.date: EDD
    """
    if not lmp_date:
        return None
    
    return lmp_date + timedelta(days=280)


def calculate_edd_from_ga(ga_weeks, ga_days=0, reference_date=None):
    """
    Calculate EDD from Gestational Age
    
    Args:
        ga_weeks: GA in weeks
        ga_days: Additional days (0-6)
        reference_date: Date of measurement (default: today)
    
    Returns:
        datetime.date: EDD
    """
    if not reference_date:
        reference_date = datetime.now().date()
    
    total_ga_days = (ga_weeks * 7) + ga_days
    days_to_add = 280 - total_ga_days  # 280 days = 40 weeks full term
    
    return reference_date + timedelta(days=days_to_add)


def get_bpd_percentile(bpd_mm, ga_weeks, gender=None):
    """
    Get BPD (Biparietal Diameter) percentile based on GA
    
    Args:
        bpd_mm: BPD in millimeters
        ga_weeks: Gestational age in weeks
        gender: 'M' or 'F' (optional, for gender-specific charts)
    
    Returns:
        float: Percentile (0-100) or None if out of range
    """
    # Simplified: using approximate reference ranges (would use actual charts in production)
    # Reference: Hadlock charts (approximate)
    if ga_weeks < 12 or ga_weeks > 42:
        return None
    
    # Approximate mean BPD by GA (mm) - simplified linear approximation
    mean_bpd = 10 + (ga_weeks - 12) * 2.5  # Rough approximation
    std_bpd = mean_bpd * 0.1  # ~10% SD
    
    if bpd_mm < mean_bpd - 2 * std_bpd:
        return 5.0  # Below 5th percentile
    elif bpd_mm < mean_bpd - std_bpd:
        return 25.0
    elif bpd_mm < mean_bpd:
        return 50.0
    elif bpd_mm < mean_bpd + std_bpd:
        return 75.0
    elif bpd_mm < mean_bpd + 2 * std_bpd:
        return 95.0
    else:
        return 97.5  # Above 95th percentile


def get_hc_percentile(hc_mm, ga_weeks, gender=None):
    """Get HC (Head Circumference) percentile"""
    if ga_weeks < 12 or ga_weeks > 42:
        return None
    # Similar to BPD - simplified
    mean_hc = 80 + (ga_weeks - 12) * 8
    std_hc = mean_hc * 0.1
    if hc_mm < mean_hc - 2 * std_hc:
        return 5.0
    elif hc_mm < mean_hc - std_hc:
        return 25.0
    elif hc_mm < mean_hc:
        return 50.0
    elif hc_mm < mean_hc + std_hc:
        return 75.0
    else:
        return 95.0


def get_ac_percentile(ac_mm, ga_weeks, gender=None):
    """Get AC (Abdominal Circumference) percentile"""
    if ga_weeks < 12 or ga_weeks > 42:
        return None
    mean_ac = 60 + (ga_weeks - 12) * 6
    std_ac = mean_ac * 0.12
    if ac_mm < mean_ac - 2 * std_ac:
        return 5.0
    elif ac_mm < mean_ac - std_ac:
        return 25.0
    elif ac_mm < mean_ac:
        return 50.0
    elif ac_mm < mean_ac + std_ac:
        return 75.0
    else:
        return 95.0


def get_fl_percentile(fl_mm, ga_weeks, gender=None):
    """Get FL (Femur Length) percentile"""
    if ga_weeks < 12 or ga_weeks > 42:
        return None
    mean_fl = 5 + (ga_weeks - 12) * 1.2
    std_fl = mean_fl * 0.1
    if fl_mm < mean_fl - 2 * std_fl:
        return 5.0
    elif fl_mm < mean_fl - std_fl:
        return 25.0
    elif fl_mm < mean_fl:
        return 50.0
    elif fl_mm < mean_fl + std_fl:
        return 75.0
    else:
        return 95.0


def calculate_efw(bpd_mm, hc_mm, ac_mm, fl_mm, ga_weeks):
    """
    Calculate Estimated Fetal Weight (EFW) using Hadlock formula
    
    Args:
        bpd_mm: Biparietal diameter (mm)
        hc_mm: Head circumference (mm)
        ac_mm: Abdominal circumference (mm)
        fl_mm: Femur length (mm)
        ga_weeks: Gestational age (weeks)
    
    Returns:
        float: EFW in grams
    """
    if not all([bpd_mm, hc_mm, ac_mm, fl_mm]):
        return None
    
    # Hadlock formula: Log10(EFW) = 1.326 - 0.00326*AC*FL + 0.0107*HC + 0.0438*AC + 0.158*FL
    # Converting mm to cm
    ac_cm = ac_mm / 10.0
    hc_cm = hc_mm / 10.0
    fl_cm = fl_mm / 10.0
    
    log_efw = 1.326 - (0.00326 * ac_cm * fl_cm) + (0.0107 * hc_cm) + (0.0438 * ac_cm) + (0.158 * fl_cm)
    efw_grams = 10 ** log_efw
    
    return round(efw_grams, 1)


def get_efw_percentile(efw_grams, ga_weeks, gender=None):
    """Get EFW percentile"""
    if ga_weeks < 20 or ga_weeks > 42:
        return None
    # Approximate mean EFW by GA (grams)
    mean_efw = (ga_weeks - 20) * 200 + 300  # Rough approximation
    std_efw = mean_efw * 0.15
    if efw_grams < mean_efw - 2 * std_efw:
        return 5.0
    elif efw_grams < mean_efw - std_efw:
        return 25.0
    elif efw_grams < mean_efw:
        return 50.0
    elif efw_grams < mean_efw + std_efw:
        return 75.0
    else:
        return 95.0
