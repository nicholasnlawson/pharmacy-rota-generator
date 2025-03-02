"""
Data manager for the pharmacy rota generator.

This module handles data persistence, loading and saving pharmacists,
ward requirements, and other configuration data.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime

from models import (
    Band, Day, WardArea, ClinicType, PharmacistPreference,
    Pharmacist, WardRequirement, Clinic
)


class DataManager:
    """Manages data operations for the rota generator."""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the data manager.
        
        Args:
            data_dir: Directory where data files are stored
        """
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.pharmacists_file = os.path.join(self.data_dir, 'pharmacists.json')
        self.ward_requirements_file = os.path.join(self.data_dir, 'ward_requirements.json')
    
    def load_pharmacists(self) -> List[Pharmacist]:
        """
        Load pharmacist data from storage.
        
        Returns:
            List of Pharmacist objects
        """
        if not os.path.exists(self.pharmacists_file):
            return []
            
        try:
            with open(self.pharmacists_file, 'r') as f:
                data = json.load(f)
                
            pharmacists = []
            for item in data:
                # Convert stored enums back to enum objects
                band = Band[item['band']]
                primary_directorate = WardArea[item['primary_directorate']]
                
                # Convert preferences
                preferences = []
                for pref in item.get('preferences', []):
                    preferences.append(PharmacistPreference(
                        ward_area=WardArea[pref['ward_area']],
                        rank=pref['rank']
                    ))
                
                # Convert availability dict
                availability = {}
                for day_str, available in item.get('availability', {}).items():
                    availability[Day[day_str]] = available
                
                pharmacist = Pharmacist(
                    id=item['id'],
                    name=item['name'],
                    email=item['email'],
                    band=band,
                    primary_directorate=primary_directorate,
                    itu_trained=item.get('itu_trained', False),
                    warfarin_trained=item.get('warfarin_trained', False),
                    default_pharmacist=item.get('default_pharmacist', False),
                    preferences=preferences,
                    availability=availability
                )
                pharmacists.append(pharmacist)
                
            return pharmacists
        
        except Exception as e:
            print(f"Error loading pharmacists: {e}")
            return []
    
    def save_pharmacists(self, pharmacists: List[Pharmacist]) -> bool:
        """
        Save pharmacist data to storage.
        
        Args:
            pharmacists: List of Pharmacist objects to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = []
            for pharm in pharmacists:
                # Convert enum objects to strings for JSON serialization
                preferences = [
                    {
                        'ward_area': pref.ward_area.name,
                        'rank': pref.rank
                    }
                    for pref in pharm.preferences
                ]
                
                # Convert availability dict
                availability = {day.name: available for day, available in pharm.availability.items()}
                
                item = {
                    'id': pharm.id,
                    'name': pharm.name,
                    'email': pharm.email,
                    'band': pharm.band.name,
                    'primary_directorate': pharm.primary_directorate.name,
                    'itu_trained': pharm.itu_trained,
                    'warfarin_trained': pharm.warfarin_trained,
                    'default_pharmacist': pharm.default_pharmacist,
                    'preferences': preferences,
                    'availability': availability
                }
                data.append(item)
                
            with open(self.pharmacists_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error saving pharmacists: {e}")
            return False
    
    def add_pharmacist(self, pharmacist: Pharmacist) -> bool:
        """
        Add a new pharmacist to the database.
        
        Args:
            pharmacist: Pharmacist object to add
            
        Returns:
            True if successful, False otherwise
        """
        pharmacists = self.load_pharmacists()
        
        # Check if pharmacist with this ID already exists
        if any(p.id == pharmacist.id for p in pharmacists):
            return False
            
        pharmacists.append(pharmacist)
        return self.save_pharmacists(pharmacists)
    
    def update_pharmacist(self, pharmacist: Pharmacist) -> bool:
        """
        Update an existing pharmacist in the database.
        
        Args:
            pharmacist: Updated Pharmacist object
            
        Returns:
            True if successful, False otherwise
        """
        pharmacists = self.load_pharmacists()
        
        # Find and update the pharmacist
        for i, p in enumerate(pharmacists):
            if p.id == pharmacist.id:
                pharmacists[i] = pharmacist
                return self.save_pharmacists(pharmacists)
                
        return False
    
    def delete_pharmacist(self, pharmacist_id: str) -> bool:
        """
        Delete a pharmacist from the database.
        
        Args:
            pharmacist_id: ID of the pharmacist to delete
            
        Returns:
            True if successful, False otherwise
        """
        pharmacists = self.load_pharmacists()
        
        # Filter out the pharmacist to delete
        updated_pharmacists = [p for p in pharmacists if p.id != pharmacist_id]
        
        if len(updated_pharmacists) < len(pharmacists):
            return self.save_pharmacists(updated_pharmacists)
        
        return False
    
    def export_rota_to_excel(self, rota, file_path: str) -> bool:
        """
        Export a rota to Excel format.
        
        Args:
            rota: Rota object to export
            file_path: Path to save the Excel file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement Excel export formatting
            # This will create a nicely formatted Excel file with ward assignments,
            # dispensary shifts, and clinic assignments
            return True
        except Exception as e:
            print(f"Error exporting rota to Excel: {e}")
            return False
