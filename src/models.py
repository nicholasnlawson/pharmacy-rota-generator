"""
Data models for the pharmacy rota generator.

This file contains classes that represent the core data structures
used in the application, such as Pharmacist, Shift, Ward, Clinic, and Rota.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import List, Dict, Optional, Set

class Day(Enum):
    """Days of the week."""
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"

class Band(Enum):
    """Pharmacist band levels."""
    BAND6 = "Band 6"
    BAND7 = "Band 7"
    BAND8 = "Band 8"

class WardArea(Enum):
    """Hospital ward areas that need pharmacist coverage."""
    EAU = "Emergency Assessment Unit"
    SURGERY = "Surgery"
    ITU = "Intensive Treatment Unit"
    CARE_OF_ELDERLY = "Care of the Elderly"
    MEDICINE = "Medicine"

class ClinicType(Enum):
    """Types of clinics requiring pharmacist coverage."""
    PHAR2PSP = "PHAR2PSP"  # Tuesday 1pm-3pm
    PHARM3A = "PHARM3A"    # Wednesday 9am-1:30pm
    PHARM1A = "PHARM1A"    # Monday 9am-1pm
    PHAR2PGC = "PHAR2PGC"  # Tuesday 1pm-3pm
    PHARM4A = "PHARM4A"    # Thursday 9am-12pm
    PHAR5AFC = "PHAR5AFC"  # Friday 9am-1pm

class ShiftType(Enum):
    """Types of shifts that can be assigned."""
    DISPENSARY = "Dispensary"
    WARD = "Ward"
    CLINIC = "Clinic"
    LUNCH_COVER = "Lunch Cover"

class DispensarySlot(Enum):
    """Dispensary shift time slots."""
    SLOT_9_11 = "9am-11am"
    SLOT_11_1 = "11am-1pm"
    SLOT_1_3 = "1pm-3pm"
    SLOT_3_5 = "3pm-5pm"

@dataclass
class PharmacistPreference:
    """Represents a pharmacist's preference for ward areas."""
    ward_area: WardArea
    rank: int  # 1-5, 1 being highest preference

@dataclass
class Pharmacist:
    """Represents a pharmacist staff member."""
    id: str
    name: str
    email: str
    band: Band
    primary_directorate: WardArea
    itu_trained: bool = False
    warfarin_trained: bool = False
    default_pharmacist: bool = False
    preferences: List[PharmacistPreference] = field(default_factory=list)
    availability: Dict[Day, bool] = field(default_factory=dict)
    
    def __post_init__(self):
        # Initialize default availability (all weekdays available)
        if not self.availability:
            self.availability = {day: True for day in Day}
    
    @property
    def can_cover_dispensary(self) -> bool:
        """Determine if the pharmacist can cover dispensary shifts based on band."""
        return self.band in [Band.BAND6, Band.BAND7]
    
    @property
    def can_cover_itu(self) -> bool:
        """Determine if the pharmacist can cover ITU shifts."""
        return self.itu_trained
    
    @property
    def can_cover_warfarin(self) -> bool:
        """Determine if the pharmacist can cover warfarin clinics."""
        return self.warfarin_trained

@dataclass
class Clinic:
    """Represents a warfarin clinic."""
    clinic_type: ClinicType
    day: Day
    start_time: time
    end_time: time
    travel_time_before: timedelta = timedelta(minutes=30)
    travel_time_after: timedelta = timedelta(minutes=30)
    
    @property
    def total_duration(self) -> timedelta:
        """Calculate the total duration including travel time."""
        clinic_duration = datetime.combine(datetime.today(), self.end_time) - datetime.combine(datetime.today(), self.start_time)
        return clinic_duration + self.travel_time_before + self.travel_time_after
    
    @property
    def conflicting_dispensary_slots(self) -> Set[DispensarySlot]:
        """Return dispensary slots that conflict with this clinic."""
        conflicts = set()
        
        # Start time including travel before
        start_with_travel = datetime.combine(datetime.today(), self.start_time) - self.travel_time_before
        # End time including travel after
        end_with_travel = datetime.combine(datetime.today(), self.end_time) + self.travel_time_after
        
        # Check conflicts with each dispensary slot
        slot_times = {
            DispensarySlot.SLOT_9_11: (time(9, 0), time(11, 0)),
            DispensarySlot.SLOT_11_1: (time(11, 0), time(13, 0)),
            DispensarySlot.SLOT_1_3: (time(13, 0), time(15, 0)),
            DispensarySlot.SLOT_3_5: (time(15, 0), time(17, 0)),
        }
        
        for slot, (slot_start, slot_end) in slot_times.items():
            slot_start_dt = datetime.combine(datetime.today(), slot_start)
            slot_end_dt = datetime.combine(datetime.today(), slot_end)
            
            # Check if there's any overlap
            if not (end_with_travel <= slot_start_dt or start_with_travel >= slot_end_dt):
                conflicts.add(slot)
                
        return conflicts

@dataclass
class WardRequirement:
    """Represents the staffing requirement for a ward area."""
    ward_area: WardArea
    day: Day
    min_pharmacists: int
    ideal_pharmacists: int

@dataclass
class DispensaryShift:
    """Represents a dispensary shift."""
    day: Day
    slot: DispensarySlot
    assigned_pharmacist: Optional[Pharmacist] = None
    
    @property
    def is_assigned(self) -> bool:
        """Check if this shift has been assigned to a pharmacist."""
        return self.assigned_pharmacist is not None

@dataclass
class WardAssignment:
    """Represents a pharmacist assigned to a ward area."""
    ward_area: WardArea
    day: Day
    pharmacist: Pharmacist

@dataclass
class ClinicAssignment:
    """Represents a pharmacist assigned to a clinic."""
    clinic: Clinic
    day: Day
    pharmacist: Pharmacist

@dataclass
class LunchCoverAssignment:
    """Represents a pharmacist assigned to lunch cover."""
    day: Day
    pharmacist: Pharmacist
    start_time: time = time(12, 30)
    end_time: time = time(13, 15)

@dataclass
class DailyRota:
    """Represents a single day's rota."""
    day: Day
    date: datetime
    dispensary_shifts: List[DispensaryShift] = field(default_factory=list)
    ward_assignments: List[WardAssignment] = field(default_factory=list)
    clinic_assignments: List[ClinicAssignment] = field(default_factory=list)
    lunch_cover: Optional[LunchCoverAssignment] = None

@dataclass
class WeeklyRota:
    """Represents a full week's rota."""
    start_date: datetime
    daily_rotas: Dict[Day, DailyRota] = field(default_factory=dict)
    
    def __post_init__(self):
        # Initialize empty daily rotas for each day if not provided
        if not self.daily_rotas:
            current_date = self.start_date
            for day in Day:
                self.daily_rotas[day] = DailyRota(day=day, date=current_date)
                current_date += timedelta(days=1)