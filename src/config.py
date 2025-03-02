"""
Configuration settings for the pharmacy rota generator.

This file contains default settings and constraints for the hospital pharmacy rota,
including ward requirements, clinic schedules, and dispensary shifts.
"""

from datetime import time
from typing import Dict, List, Tuple

from models import (
    Band, Day, WardArea, ClinicType, DispensarySlot,
    WardRequirement, Clinic
)

# Default ward requirements by day
# Format: (ward, day): (min_pharmacists, ideal_pharmacists)
DEFAULT_WARD_REQUIREMENTS = {
    # EAU requirements
    (WardArea.EAU, Day.MONDAY): WardRequirement(WardArea.EAU, Day.MONDAY, 1, 2),
    (WardArea.EAU, Day.TUESDAY): WardRequirement(WardArea.EAU, Day.TUESDAY, 1, 2),
    (WardArea.EAU, Day.WEDNESDAY): WardRequirement(WardArea.EAU, Day.WEDNESDAY, 1, 2),
    (WardArea.EAU, Day.THURSDAY): WardRequirement(WardArea.EAU, Day.THURSDAY, 1, 2),
    (WardArea.EAU, Day.FRIDAY): WardRequirement(WardArea.EAU, Day.FRIDAY, 1, 2),
    
    # SURGERY requirements
    (WardArea.SURGERY, Day.MONDAY): WardRequirement(WardArea.SURGERY, Day.MONDAY, 1, 2),
    (WardArea.SURGERY, Day.TUESDAY): WardRequirement(WardArea.SURGERY, Day.TUESDAY, 1, 2),
    (WardArea.SURGERY, Day.WEDNESDAY): WardRequirement(WardArea.SURGERY, Day.WEDNESDAY, 1, 2),
    (WardArea.SURGERY, Day.THURSDAY): WardRequirement(WardArea.SURGERY, Day.THURSDAY, 1, 2),
    (WardArea.SURGERY, Day.FRIDAY): WardRequirement(WardArea.SURGERY, Day.FRIDAY, 1, 2),
    
    # ITU requirements (optional, depends on trained staff availability)
    (WardArea.ITU, Day.MONDAY): WardRequirement(WardArea.ITU, Day.MONDAY, 0, 1),
    (WardArea.ITU, Day.TUESDAY): WardRequirement(WardArea.ITU, Day.TUESDAY, 0, 1),
    (WardArea.ITU, Day.WEDNESDAY): WardRequirement(WardArea.ITU, Day.WEDNESDAY, 0, 1),
    (WardArea.ITU, Day.THURSDAY): WardRequirement(WardArea.ITU, Day.THURSDAY, 0, 1),
    (WardArea.ITU, Day.FRIDAY): WardRequirement(WardArea.ITU, Day.FRIDAY, 0, 1),
    
    # CARE_OF_ELDERLY requirements
    (WardArea.CARE_OF_ELDERLY, Day.MONDAY): WardRequirement(WardArea.CARE_OF_ELDERLY, Day.MONDAY, 1, 2),
    (WardArea.CARE_OF_ELDERLY, Day.TUESDAY): WardRequirement(WardArea.CARE_OF_ELDERLY, Day.TUESDAY, 1, 2),
    (WardArea.CARE_OF_ELDERLY, Day.WEDNESDAY): WardRequirement(WardArea.CARE_OF_ELDERLY, Day.WEDNESDAY, 1, 2),
    (WardArea.CARE_OF_ELDERLY, Day.THURSDAY): WardRequirement(WardArea.CARE_OF_ELDERLY, Day.THURSDAY, 1, 2),
    (WardArea.CARE_OF_ELDERLY, Day.FRIDAY): WardRequirement(WardArea.CARE_OF_ELDERLY, Day.FRIDAY, 1, 2),
    
    # MEDICINE requirements
    (WardArea.MEDICINE, Day.MONDAY): WardRequirement(WardArea.MEDICINE, Day.MONDAY, 4, 6),
    (WardArea.MEDICINE, Day.TUESDAY): WardRequirement(WardArea.MEDICINE, Day.TUESDAY, 4, 6),
    (WardArea.MEDICINE, Day.WEDNESDAY): WardRequirement(WardArea.MEDICINE, Day.WEDNESDAY, 3, 6),
    (WardArea.MEDICINE, Day.THURSDAY): WardRequirement(WardArea.MEDICINE, Day.THURSDAY, 3, 6),
    (WardArea.MEDICINE, Day.FRIDAY): WardRequirement(WardArea.MEDICINE, Day.FRIDAY, 4, 6),
}

# Dispensary slots configuration
DISPENSARY_SLOTS = [
    DispensarySlot.SLOT_9_11,  # 9am-11am
    DispensarySlot.SLOT_11_1,  # 11am-1pm
    DispensarySlot.SLOT_1_3,   # 1pm-3pm
    DispensarySlot.SLOT_3_5,   # 3pm-5pm
]

# Clinic definitions - regular clinics that need coverage
DEFAULT_CLINICS = [
    # Tuesday warfarin clinic (primary clinic) - requires travel time
    Clinic(
        clinic_type=ClinicType.PHAR2PSP,
        day=Day.TUESDAY,
        start_time=time(13, 0),
        end_time=time(15, 0),
    ),
    
    # Monday warfarin clinic (optional coverage)
    Clinic(
        clinic_type=ClinicType.PHARM1A,
        day=Day.MONDAY,
        start_time=time(9, 0),
        end_time=time(13, 0),
    ),
    
    # Tuesday afternoon second clinic (optional coverage)
    Clinic(
        clinic_type=ClinicType.PHAR2PGC,
        day=Day.TUESDAY,
        start_time=time(13, 0),
        end_time=time(15, 0),
    ),
    
    # Wednesday morning clinic (optional coverage)
    Clinic(
        clinic_type=ClinicType.PHARM3A,
        day=Day.WEDNESDAY,
        start_time=time(9, 0),
        end_time=time(13, 30),
    ),
    
    # Thursday morning clinic (optional coverage) 
    Clinic(
        clinic_type=ClinicType.PHARM4A,
        day=Day.THURSDAY,
        start_time=time(9, 0),
        end_time=time(12, 0),
    ),
    
    # Friday morning clinic (optional coverage)
    Clinic(
        clinic_type=ClinicType.PHAR5AFC,
        day=Day.FRIDAY,
        start_time=time(9, 0),
        end_time=time(13, 0),
    ),
]

# Default lunch time - typical but can be adjusted
DEFAULT_LUNCH_START = time(12, 30)
DEFAULT_LUNCH_END = time(13, 15)  # 45 minutes total
