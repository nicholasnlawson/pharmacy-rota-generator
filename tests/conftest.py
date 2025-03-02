"""
Shared test fixtures and configuration.
"""

import pytest
import os
import sys
from datetime import datetime, time

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import (
    Day, Band, WardArea, ClinicType, 
    Pharmacist, Clinic, PharmacistPreference
)
from src.web import app


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
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


@pytest.fixture
def client():
    """Fixture providing a Flask test client."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client
