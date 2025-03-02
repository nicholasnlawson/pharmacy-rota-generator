"""
Data models for the pharmacy rota generator.

This file contains classes that represent the core data structures
used in the application, such as Pharmacist, Shift, and Rota.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional
from enum import Enum

class ShiftType(Enum):
    """Types of shifts that can be assigned."""
    MORNING = "Morning"
    AFTERNOON = "Afternoon"
    NIGHT = "Night"
    ON_CALL = "On-Call"

@dataclass
class Pharmacist:
    """Represents a pharmacist staff member."""
    id: str
    name: str
    role: str
    max_hours_per_week: float = 40.0
    skills: List[str] = None
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []

@dataclass
class Shift:
    """Represents a single shift that needs to be filled."""
    date: datetime
    shift_type: ShiftType
    required_role: str
    assigned_pharmacist: Optional[Pharmacist] = None
    
    @property
    def is_assigned(self) -> bool:
        """Check if this shift has been assigned to a pharmacist."""
        return self.assigned_pharmacist is not None