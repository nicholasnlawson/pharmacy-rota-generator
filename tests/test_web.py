"""
Tests for the web interface module.
"""

import pytest
import json
import os
from datetime import datetime

from src.web import app
from src.models import (
    Band, Day, WardArea, Pharmacist, 
    PharmacistPreference, WeeklyRota
)


@pytest.fixture
def client():
    """Fixture providing a Flask test client."""
    # Set testing configuration
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Use temporary file for SQLite database if needed
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        yield client


class TestWebRoutes:
    """Tests for web routes."""
    
    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_pharmacists_route(self, client):
        """Test the pharmacists route."""
        response = client.get('/pharmacists')
        assert response.status_code == 200
    
    def test_add_pharmacist(self, client):
        """Test adding a pharmacist."""
        # Create test data
        test_pharmacist = {
            'name': 'Test Pharmacist',
            'email': 'test@example.com',
            'band': 'BAND7',
            'primary_directorate': 'MEDICINE',
            'itu_trained': 'on',
            'warfarin_trained': 'on',
            'avail_MONDAY': 'on',
            'avail_TUESDAY': 'on',
            'avail_WEDNESDAY': 'on',
            'avail_THURSDAY': 'on',
            'avail_FRIDAY': 'on',
            'pref_MEDICINE': '1',
            'pref_SURGERY': '2'
        }
        
        response = client.post('/pharmacist/add', data=test_pharmacist)
        # Should redirect after successful addition
        assert response.status_code == 302
        
        # TODO: Add verification of database addition once we have access to the data manager
    
    def test_generate_rota(self, client):
        """Test rota generation route."""
        # Create test data for rota generation
        test_data = {
            'start_date': '2025-03-03',  # A Monday
        }
        
        response = client.post('/generate-rota', data=test_data)
        # Should redirect after successful generation
        assert response.status_code == 302
        
        # Check the view rota page
        response = client.get('/view-rota')
        assert response.status_code == 200
        
        # TODO: Add more specific assertions based on rota content


# Integration test that simulates a full user workflow
class TestUserWorkflow:
    """Integration tests for user workflows."""
    
    def test_full_workflow(self, client):
        """Test the full user workflow: add pharmacists and generate rota."""
        # 1. Add multiple pharmacists
        pharmacists = [
            {
                'name': 'John Doe',
                'email': 'john@example.com',
                'band': 'BAND7',
                'primary_directorate': 'MEDICINE',
                'itu_trained': 'on',
                'warfarin_trained': 'on',
                'avail_MONDAY': 'on',
                'avail_TUESDAY': 'on',
                'avail_WEDNESDAY': 'on',
                'avail_THURSDAY': 'on',
                'avail_FRIDAY': 'on',
            },
            {
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'band': 'BAND6',
                'primary_directorate': 'SURGERY',
                'warfarin_trained': 'on',
                'avail_MONDAY': 'on',
                'avail_TUESDAY': 'on',
                'avail_WEDNESDAY': 'on',
                'avail_THURSDAY': 'on',
                'avail_FRIDAY': 'on',
            }
        ]
        
        for pharmacist in pharmacists:
            response = client.post('/pharmacist/add', data=pharmacist)
            assert response.status_code == 302
        
        # 2. Generate rota
        test_data = {
            'start_date': '2025-03-03',  # A Monday
        }
        
        response = client.post('/generate-rota', data=test_data)
        assert response.status_code == 302
        
        # 3. View rota
        response = client.get('/view-rota')
        assert response.status_code == 200
        
        # 4. Export rota (if applicable)
        # response = client.get('/export-rota')
        # assert response.status_code == 200
        # assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        # TODO: Add more assertions for the specific content and functionality
