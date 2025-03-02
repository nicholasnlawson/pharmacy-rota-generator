"""
Web interface for the pharmacy rota generator.

This module provides a Flask web application for interacting with
the pharmacy rota generator system.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
from werkzeug.utils import secure_filename
import pandas as pd

from models import (
    Band, Day, WardArea, ClinicType, PharmacistPreference,
    Pharmacist, Clinic, WeeklyRota
)
from scheduler import RotaScheduler
from data_manager import DataManager
from config import DEFAULT_WARD_REQUIREMENTS, DEFAULT_CLINICS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_pharmacy_rota')

# Initialize data manager
data_manager = DataManager()

# Ensure templates directory exists
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

# Create templates
@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/pharmacists')
def pharmacists():
    """Render the pharmacists management page."""
    all_pharmacists = data_manager.load_pharmacists()
    return render_template('pharmacists.html', pharmacists=all_pharmacists)

@app.route('/pharmacist/add', methods=['GET', 'POST'])
def add_pharmacist():
    """Add a new pharmacist."""
    if request.method == 'POST':
        try:
            # Generate a unique ID
            import uuid
            pharmacist_id = str(uuid.uuid4())
            
            # Get form data
            name = request.form['name']
            email = request.form['email']
            band = Band[request.form['band']]
            primary_directorate = WardArea[request.form['primary_directorate']]
            itu_trained = 'itu_trained' in request.form
            warfarin_trained = 'warfarin_trained' in request.form
            default_pharmacist = 'default_pharmacist' in request.form
            
            # Create preferences list from form data
            preferences = []
            for ward in WardArea:
                pref_key = f'pref_{ward.name}'
                if pref_key in request.form and request.form[pref_key]:
                    rank = int(request.form[pref_key])
                    preferences.append(PharmacistPreference(ward_area=ward, rank=rank))
            
            # Create availability dict from form data
            availability = {}
            for day in Day:
                avail_key = f'avail_{day.name}'
                availability[day] = avail_key in request.form
            
            # Create new pharmacist object
            pharmacist = Pharmacist(
                id=pharmacist_id,
                name=name,
                email=email,
                band=band,
                primary_directorate=primary_directorate,
                itu_trained=itu_trained,
                warfarin_trained=warfarin_trained,
                default_pharmacist=default_pharmacist,
                preferences=preferences,
                availability=availability
            )
            
            # Save to database
            success = data_manager.add_pharmacist(pharmacist)
            
            if success:
                flash('Pharmacist added successfully!', 'success')
                return redirect(url_for('pharmacists'))
            else:
                flash('Error adding pharmacist.', 'error')
                
        except Exception as e:
            logger.error(f"Error adding pharmacist: {e}")
            flash(f'Error: {str(e)}', 'error')
        
    return render_template('add_pharmacist.html', bands=Band, wards=WardArea, days=Day)

@app.route('/pharmacist/edit/<pharmacist_id>', methods=['GET', 'POST'])
def edit_pharmacist(pharmacist_id):
    """Edit an existing pharmacist."""
    # Load all pharmacists
    all_pharmacists = data_manager.load_pharmacists()
    
    # Find the target pharmacist
    pharmacist = next((p for p in all_pharmacists if p.id == pharmacist_id), None)
    
    if not pharmacist:
        flash('Pharmacist not found.', 'error')
        return redirect(url_for('pharmacists'))
    
    if request.method == 'POST':
        try:
            # Update pharmacist data
            pharmacist.name = request.form['name']
            pharmacist.email = request.form['email']
            pharmacist.band = Band[request.form['band']]
            pharmacist.primary_directorate = WardArea[request.form['primary_directorate']]
            pharmacist.itu_trained = 'itu_trained' in request.form
            pharmacist.warfarin_trained = 'warfarin_trained' in request.form
            pharmacist.default_pharmacist = 'default_pharmacist' in request.form
            
            # Update preferences
            pharmacist.preferences = []
            for ward in WardArea:
                pref_key = f'pref_{ward.name}'
                if pref_key in request.form and request.form[pref_key]:
                    rank = int(request.form[pref_key])
                    pharmacist.preferences.append(PharmacistPreference(ward_area=ward, rank=rank))
            
            # Update availability
            for day in Day:
                avail_key = f'avail_{day.name}'
                pharmacist.availability[day] = avail_key in request.form
            
            # Save changes
            success = data_manager.update_pharmacist(pharmacist)
            
            if success:
                flash('Pharmacist updated successfully!', 'success')
                return redirect(url_for('pharmacists'))
            else:
                flash('Error updating pharmacist.', 'error')
                
        except Exception as e:
            logger.error(f"Error updating pharmacist: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('edit_pharmacist.html', pharmacist=pharmacist, 
                          bands=Band, wards=WardArea, days=Day)

@app.route('/pharmacist/delete/<pharmacist_id>', methods=['POST'])
def delete_pharmacist(pharmacist_id):
    """Delete a pharmacist."""
    success = data_manager.delete_pharmacist(pharmacist_id)
    
    if success:
        flash('Pharmacist deleted successfully!', 'success')
    else:
        flash('Error deleting pharmacist.', 'error')
        
    return redirect(url_for('pharmacists'))

@app.route('/generate_rota', methods=['GET', 'POST'])
def generate_rota():
    """Generate a rota based on form inputs."""
    if request.method == 'POST':
        try:
            # Get start date from form
            start_date_str = request.form['start_date']
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            
            # Load pharmacists
            pharmacists = data_manager.load_pharmacists()
            
            if not pharmacists:
                flash('No pharmacists found. Please add pharmacists first.', 'error')
                return redirect(url_for('index'))
            
            # Initialize scheduler
            scheduler = RotaScheduler(
                pharmacists=pharmacists,
                ward_requirements=DEFAULT_WARD_REQUIREMENTS,
                clinics=DEFAULT_CLINICS
            )
            
            # Generate rota
            rota = scheduler.generate_weekly_rota(start_date)
            
            # Save to session for display
            # We'll convert it to a simple dict structure
            rota_dict = rota_to_dict(rota)
            session['current_rota'] = rota_dict
            
            flash('Rota generated successfully!', 'success')
            return redirect(url_for('view_rota'))
            
        except Exception as e:
            logger.error(f"Error generating rota: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    # Default start date to next Monday
    today = datetime.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, use next Monday
    default_start_date = (today + timedelta(days=days_until_monday)).strftime('%Y-%m-%d')
    
    return render_template('generate_rota.html', default_start_date=default_start_date)

@app.route('/view_rota')
def view_rota():
    """View the currently generated rota."""
    if 'current_rota' not in session:
        flash('No rota has been generated yet.', 'error')
        return redirect(url_for('generate_rota'))
    
    rota_dict = session['current_rota']
    return render_template('view_rota.html', rota=rota_dict)

@app.route('/export_rota', methods=['POST'])
def export_rota():
    """Export the current rota to Excel."""
    if 'current_rota' not in session:
        flash('No rota has been generated yet.', 'error')
        return redirect(url_for('generate_rota'))
    
    # TODO: Implement Excel export
    # For now, we'll just return a success message
    flash('Rota export functionality coming soon!', 'info')
    return redirect(url_for('view_rota'))

def rota_to_dict(rota):
    """Convert a WeeklyRota object to a dictionary for use in templates."""
    result = {
        'start_date': rota.start_date.strftime('%Y-%m-%d'),
        'end_date': (rota.start_date + timedelta(days=4)).strftime('%Y-%m-%d'),
        'days': {}
    }
    
    for day, daily_rota in rota.daily_rotas.items():
        day_dict = {
            'date': daily_rota.date.strftime('%Y-%m-%d'),
            'dispensary_shifts': [],
            'clinic_assignments': [],
            'ward_assignments': {},
            'lunch_cover': None
        }
        
        # Add dispensary shifts
        for shift in daily_rota.dispensary_shifts:
            shift_dict = {
                'slot': shift.slot.value,
                'pharmacist': shift.assigned_pharmacist.name if shift.assigned_pharmacist else 'UNASSIGNED'
            }
            day_dict['dispensary_shifts'].append(shift_dict)
        
        # Add clinic assignments
        for assignment in daily_rota.clinic_assignments:
            clinic_dict = {
                'clinic_type': assignment.clinic.clinic_type.value,
                'pharmacist': assignment.pharmacist.name
            }
            day_dict['clinic_assignments'].append(clinic_dict)
        
        # Add lunch cover
        if daily_rota.lunch_cover:
            day_dict['lunch_cover'] = {
                'pharmacist': daily_rota.lunch_cover.pharmacist.name,
                'start_time': daily_rota.lunch_cover.start_time.strftime('%H:%M'),
                'end_time': daily_rota.lunch_cover.end_time.strftime('%H:%M')
            }
        
        # Add ward assignments
        by_ward = {}
        for assignment in daily_rota.ward_assignments:
            ward_name = assignment.ward_area.value
            if ward_name not in by_ward:
                by_ward[ward_name] = []
            by_ward[ward_name].append(assignment.pharmacist.name)
        
        for ward_name, pharmacists in by_ward.items():
            ward_area = next((w for w in WardArea if w.value == ward_name), None)
            required = DEFAULT_WARD_REQUIREMENTS.get((ward_area, day)) if ward_area else None
            
            min_req = required.min_pharmacists if required else 0
            ideal_req = required.ideal_pharmacists if required else 0
            
            day_dict['ward_assignments'][ward_name] = {
                'pharmacists': pharmacists,
                'min_required': min_req,
                'ideal_required': ideal_req,
                'status': len(pharmacists) >= min_req
            }
        
        result['days'][day.value] = day_dict
    
    return result

if __name__ == '__main__':
    app.run(debug=True)
