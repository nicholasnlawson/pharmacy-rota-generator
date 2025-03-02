"""
Tests for the scheduler module.
"""

import pytest
from datetime import datetime, time, timedelta

from src.models import (
    Day, Band, WardArea, ClinicType, DispensarySlot,
    Pharmacist, Clinic, WeeklyRota, DailyRota
)
from src.scheduler import RotaScheduler
from src.config import DEFAULT_WARD_REQUIREMENTS, DEFAULT_CLINICS


@pytest.fixture
def test_pharmacists():
    """Fixture providing test pharmacist data."""
    return [
        Pharmacist(
            id="p1", 
            name="John Doe",
            email="john@example.com",
            band=Band.BAND7,
            primary_directorate=WardArea.MEDICINE,
            itu_trained=True,
            warfarin_trained=True
        ),
        Pharmacist(
            id="p2",
            name="Jane Smith",
            email="jane@example.com",
            band=Band.BAND6,
            primary_directorate=WardArea.SURGERY,
            warfarin_trained=True
        ),
        Pharmacist(
            id="p3",
            name="Bob Miller",
            email="bob@example.com",
            band=Band.BAND8,
            primary_directorate=WardArea.ITU,
            itu_trained=True
        ),
        Pharmacist(
            id="p4",
            name="Alice Jones",
            email="alice@example.com",
            band=Band.BAND7,
            primary_directorate=WardArea.CARE_OF_ELDERLY,
            default_pharmacist=True
        ),
    ]


@pytest.fixture
def test_clinics():
    """Fixture providing test clinic data."""
    return [
        Clinic(
            clinic_type=ClinicType.PHAR2PSP,
            day=Day.TUESDAY,
            start_time=time(13, 0),
            end_time=time(15, 0)
        ),
        Clinic(
            clinic_type=ClinicType.PHARM1A,
            day=Day.MONDAY,
            start_time=time(9, 0),
            end_time=time(13, 0)
        )
    ]


class TestRotaScheduler:
    """Tests for the RotaScheduler class."""
    
    def test_scheduler_init(self, test_pharmacists, test_clinics):
        """Test RotaScheduler initialization."""
        scheduler = RotaScheduler(
            pharmacists=test_pharmacists,
            clinics=test_clinics
        )
        
        assert scheduler.pharmacists == test_pharmacists
        assert scheduler.clinics == test_clinics
        assert scheduler.ward_requirements == DEFAULT_WARD_REQUIREMENTS
    
    def test_daily_rota_generation(self, test_pharmacists, test_clinics):
        """Test daily rota generation."""
        scheduler = RotaScheduler(
            pharmacists=test_pharmacists,
            clinics=test_clinics
        )
        
        # Generate a daily rota for Monday
        monday_date = datetime(2025, 3, 3)  # A Monday
        daily_rota = scheduler._generate_daily_rota(Day.MONDAY, monday_date)
        
        # Verify basic structure
        assert daily_rota.day == Day.MONDAY
        assert daily_rota.date == monday_date
        
        # Verify clinic assignments
        clinic_assignments = daily_rota.clinic_assignments
        assert len(clinic_assignments) > 0  # Should have assigned the Monday clinic
        
        # Verify dispensary shifts
        dispensary_shifts = daily_rota.dispensary_shifts
        assert len(dispensary_shifts) > 0  # Should have assigned dispensary shifts
        
        # The default pharmacist should be assigned to dispensary if available
        default_pharm = next((p for p in test_pharmacists if p.default_pharmacist), None)
        if default_pharm and default_pharm.availability.get(Day.MONDAY, False):
            for shift in dispensary_shifts:
                assert shift.assigned_pharmacist == default_pharm
    
    def test_weekly_rota_generation(self, test_pharmacists, test_clinics):
        """Test weekly rota generation."""
        scheduler = RotaScheduler(
            pharmacists=test_pharmacists,
            clinics=test_clinics
        )
        
        # Generate a weekly rota
        start_date = datetime(2025, 3, 3)  # A Monday
        weekly_rota = scheduler.generate_weekly_rota(start_date)
        
        # Verify structure
        assert weekly_rota.start_date == start_date
        
        # Should have a daily rota for each weekday
        for day in Day:
            assert day in weekly_rota.daily_rotas
            assert isinstance(weekly_rota.daily_rotas[day], DailyRota)
            
            # Basic validation for each daily rota
            daily_rota = weekly_rota.daily_rotas[day]
            assert daily_rota.day == day
            assert daily_rota.date.weekday() == list(Day).index(day)
    
    def test_pharmacist_assignment_constraints(self, test_pharmacists):
        """Test that pharmacists are assigned according to constraints."""
        # Create a specific set of test data to test constraints
        clinics = [
            Clinic(
                clinic_type=ClinicType.PHAR2PSP,
                day=Day.TUESDAY,
                start_time=time(13, 0),
                end_time=time(15, 0)
            )
        ]
        
        # Reset availability to test specific days
        for pharm in test_pharmacists:
            pharm.availability = {day: False for day in Day}
            pharm.availability[Day.TUESDAY] = True
        
        # Make only one pharmacist warfarin trained
        warfarin_pharm = test_pharmacists[0]
        for pharm in test_pharmacists:
            pharm.warfarin_trained = (pharm == warfarin_pharm)
        
        scheduler = RotaScheduler(
            pharmacists=test_pharmacists,
            clinics=clinics
        )
        
        # Generate a rota for Tuesday
        tuesday_date = datetime(2025, 3, 4)  # A Tuesday
        daily_rota = scheduler._generate_daily_rota(Day.TUESDAY, tuesday_date)
        
        # The clinic should be assigned to the warfarin trained pharmacist
        clinic_assignments = daily_rota.clinic_assignments
        assert len(clinic_assignments) == 1
        assert clinic_assignments[0].pharmacist == warfarin_pharm
