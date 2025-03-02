"""
Tests for the models module.
"""

import pytest
from datetime import time, datetime, timedelta

from src.models import (
    Day, Band, WardArea, ClinicType, DispensarySlot, ShiftType,
    Pharmacist, Clinic, PharmacistPreference
)

class TestPharmacist:
    """Tests for the Pharmacist class."""
    
    def test_pharmacist_init(self):
        """Test Pharmacist initialization."""
        pharmacist = Pharmacist(
            id="p1",
            name="John Doe",
            email="john@example.com",
            band=Band.BAND7,
            primary_directorate=WardArea.MEDICINE,
            itu_trained=True,
            warfarin_trained=True
        )
        
        assert pharmacist.id == "p1"
        assert pharmacist.name == "John Doe"
        assert pharmacist.email == "john@example.com"
        assert pharmacist.band == Band.BAND7
        assert pharmacist.primary_directorate == WardArea.MEDICINE
        assert pharmacist.itu_trained is True
        assert pharmacist.warfarin_trained is True
        assert pharmacist.default_pharmacist is False
        
        # Test default availability
        for day in Day:
            assert pharmacist.availability[day] is True
    
    def test_pharmacist_properties(self):
        """Test Pharmacist property methods."""
        band6_pharm = Pharmacist(
            id="p2",
            name="Jane Smith",
            email="jane@example.com",
            band=Band.BAND6,
            primary_directorate=WardArea.SURGERY
        )
        
        band8_pharm = Pharmacist(
            id="p3",
            name="Bob Miller",
            email="bob@example.com",
            band=Band.BAND8,
            primary_directorate=WardArea.ITU,
            itu_trained=True
        )
        
        # Test can_cover_dispensary
        assert band6_pharm.can_cover_dispensary is True
        assert band8_pharm.can_cover_dispensary is False
        
        # Test can_cover_itu
        assert band6_pharm.can_cover_itu is False
        assert band8_pharm.can_cover_itu is True
        
        # Test can_cover_warfarin
        warfarin_pharm = Pharmacist(
            id="p4",
            name="Alice Jones",
            email="alice@example.com",
            band=Band.BAND7,
            primary_directorate=WardArea.MEDICINE,
            warfarin_trained=True
        )
        
        assert band6_pharm.can_cover_warfarin is False
        assert warfarin_pharm.can_cover_warfarin is True


class TestClinic:
    """Tests for the Clinic class."""
    
    def test_clinic_duration(self):
        """Test clinic duration calculations."""
        clinic = Clinic(
            clinic_type=ClinicType.PHAR2PSP,
            day=Day.TUESDAY,
            start_time=time(13, 0),  # 1pm
            end_time=time(15, 0),    # 3pm
            travel_time_before=timedelta(minutes=30),
            travel_time_after=timedelta(minutes=30)
        )
        
        # Total duration should be 3 hours (2h clinic + 30min before + 30min after)
        expected_duration = timedelta(hours=3)
        assert clinic.total_duration == expected_duration
    
    def test_conflicting_dispensary_slots(self):
        """Test detection of conflicting dispensary slots."""
        # Clinic from 1pm-3pm with 30min travel time before and after
        clinic = Clinic(
            clinic_type=ClinicType.PHAR2PSP,
            day=Day.TUESDAY,
            start_time=time(13, 0),  # 1pm
            end_time=time(15, 0),    # 3pm
            travel_time_before=timedelta(minutes=30),
            travel_time_after=timedelta(minutes=30)
        )
        
        # Should conflict with 11am-1pm, 1pm-3pm, and 3pm-5pm slots
        expected_conflicts = {
            DispensarySlot.SLOT_11_1,  # Conflicts with travel before
            DispensarySlot.SLOT_1_3,   # Direct conflict
            DispensarySlot.SLOT_3_5    # Conflicts with travel after
        }
        
        assert clinic.conflicting_dispensary_slots == expected_conflicts
