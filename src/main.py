"""
Pharmacy Rota Generator

This application generates scheduling rotas for hospital pharmacists,
taking into account staff availability, shift requirements, and fair
distribution of workload.
"""

import argparse
import logging
import pandas as pd
import os
import sys
import uuid
from datetime import datetime, timedelta

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

def setup_arg_parser():
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(description='Pharmacy Rota Generator')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate rota command
    generate_parser = subparsers.add_parser('generate', help='Generate a weekly rota')
    generate_parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                                help='Start date for the rota (format: YYYY-MM-DD)')
    generate_parser.add_argument('--output', type=str, help='Output file path for the generated rota')
    
    # Manage pharmacists commands
    add_parser = subparsers.add_parser('add-pharmacist', help='Add a new pharmacist')
    add_parser.add_argument('--name', type=str, required=True, help='Pharmacist name')
    add_parser.add_argument('--email', type=str, required=True, help='Pharmacist email')
    add_parser.add_argument('--band', type=str, required=True, choices=['BAND6', 'BAND7', 'BAND8'], 
                           help='Pharmacist band level')
    add_parser.add_argument('--primary-directorate', type=str, required=True, 
                           choices=['EAU', 'SURGERY', 'ITU', 'CARE_OF_ELDERLY', 'MEDICINE'],
                           help='Primary ward area')
    add_parser.add_argument('--itu-trained', action='store_true', help='Flag if ITU trained')
    add_parser.add_argument('--warfarin-trained', action='store_true', help='Flag if warfarin trained')
    add_parser.add_argument('--default-pharmacist', action='store_true', 
                           help='Flag if this is the default dispensary pharmacist')
    
    list_parser = subparsers.add_parser('list-pharmacists', help='List all pharmacists')
    
    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', help='Run in interactive mode')
    
    return parser

def generate_rota(args, data_manager):
    """Generate a weekly rota."""
    # Get start date or use next Monday if not provided
    if args.start_date:
        start_date = args.start_date
    else:
        today = datetime.today()
        # Calculate days until next Monday (0 is Monday, 6 is Sunday)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, use next Monday
        start_date = today + timedelta(days=days_until_monday)
    
    logger.info(f"Generating rota starting from {start_date.strftime('%Y-%m-%d')}")
    
    # Load pharmacists
    pharmacists = data_manager.load_pharmacists()
    if not pharmacists:
        logger.error("No pharmacists found. Please add pharmacists first.")
        return False
    
    # Initialize scheduler
    scheduler = RotaScheduler(
        pharmacists=pharmacists,
        ward_requirements=DEFAULT_WARD_REQUIREMENTS,
        clinics=DEFAULT_CLINICS
    )
    
    # Generate rota
    rota = scheduler.generate_weekly_rota(start_date)
    
    # Output to file if specified, otherwise print to console
    if args.output:
        success = data_manager.export_rota_to_excel(rota, args.output)
        if success:
            logger.info(f"Rota exported successfully to {args.output}")
        else:
            logger.error("Failed to export rota")
    else:
        print_rota(rota)
    
    return True

def print_rota(rota):
    """Print a summary of the rota to the console."""
    print(f"\nWeekly Rota: {rota.start_date.strftime('%Y-%m-%d')} to {(rota.start_date + timedelta(days=4)).strftime('%Y-%m-%d')}\n")
    
    for day, daily_rota in rota.daily_rotas.items():
        print(f"\n=== {day.value}: {daily_rota.date.strftime('%Y-%m-%d')} ===")
        
        # Print dispensary shifts
        print("\nDispensary Shifts:")
        for shift in daily_rota.dispensary_shifts:
            pharmacist_name = shift.assigned_pharmacist.name if shift.assigned_pharmacist else "UNASSIGNED"
            print(f"  {shift.slot.value}: {pharmacist_name}")
        
        # Print clinic assignments
        if daily_rota.clinic_assignments:
            print("\nClinic Assignments:")
            for assignment in daily_rota.clinic_assignments:
                print(f"  {assignment.clinic.clinic_type.value}: {assignment.pharmacist.name}")
        
        # Print lunch cover
        if daily_rota.lunch_cover:
            print(f"\nLunch Cover: {daily_rota.lunch_cover.pharmacist.name} " +
                  f"({daily_rota.lunch_cover.start_time.strftime('%H:%M')}-{daily_rota.lunch_cover.end_time.strftime('%H:%M')})")
        
        # Print ward assignments
        print("\nWard Assignments:")
        by_ward = {}
        for assignment in daily_rota.ward_assignments:
            if assignment.ward_area not in by_ward:
                by_ward[assignment.ward_area] = []
            by_ward[assignment.ward_area].append(assignment.pharmacist.name)
        
        for ward, pharmacists in by_ward.items():
            required = DEFAULT_WARD_REQUIREMENTS.get((ward, day))
            min_req = required.min_pharmacists if required else 0
            ideal_req = required.ideal_pharmacists if required else 0
            
            status = "✅" if len(pharmacists) >= min_req else "❌"
            print(f"  {ward.value} ({len(pharmacists)}/{min_req}-{ideal_req}) {status}")
            for name in pharmacists:
                print(f"    - {name}")

def add_pharmacist(args, data_manager):
    """Add a new pharmacist."""
    pharmacist_id = str(uuid.uuid4())
    
    # Parse band and primary directorate
    band = Band[args.band]
    primary_directorate = WardArea[args.primary_directorate]
    
    # Create new pharmacist
    pharmacist = Pharmacist(
        id=pharmacist_id,
        name=args.name,
        email=args.email,
        band=band,
        primary_directorate=primary_directorate,
        itu_trained=args.itu_trained,
        warfarin_trained=args.warfarin_trained,
        default_pharmacist=args.default_pharmacist
    )
    
    # Add to database
    success = data_manager.add_pharmacist(pharmacist)
    if success:
        logger.info(f"Pharmacist {args.name} added successfully")
    else:
        logger.error(f"Failed to add pharmacist {args.name}")
    
    return success

def list_pharmacists(data_manager):
    """List all pharmacists."""
    pharmacists = data_manager.load_pharmacists()
    
    if not pharmacists:
        print("No pharmacists found in the database.")
        return
    
    print("\nPharmacists:")
    print(f"{'ID':<36} | {'Name':<20} | {'Band':<8} | {'Primary Area':<20} | {'ITU':<5} | {'Warfarin':<8}")
    print("-" * 105)
    
    for p in pharmacists:
        print(f"{p.id:<36} | {p.name:<20} | {p.band.value:<8} | {p.primary_directorate.value:<20} | " +
              f"{'Yes' if p.itu_trained else 'No':<5} | {'Yes' if p.warfarin_trained else 'No':<8}")

def interactive_mode(data_manager):
    """Run the application in interactive mode."""
    while True:
        print("\nPharmacy Rota Generator - Interactive Mode")
        print("1. Generate Weekly Rota")
        print("2. Add Pharmacist")
        print("3. List Pharmacists")
        print("4. Exit")
        
        choice = input("\nSelect an option (1-4): ")
        
        if choice == '1':
            # Generate rota
            start_date_str = input("Enter start date (YYYY-MM-DD) or press Enter for next Monday: ")
            output_file = input("Enter output file path or press Enter for console output: ")
            
            args = argparse.Namespace()
            args.start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
            args.output = output_file if output_file else None
            
            generate_rota(args, data_manager)
            
        elif choice == '2':
            # Add pharmacist
            name = input("Pharmacist name: ")
            email = input("Pharmacist email: ")
            
            print("\nBand levels:")
            for band in Band:
                print(f"  {band.name}: {band.value}")
            band = input("Band (BAND6/BAND7/BAND8): ")
            
            print("\nWard areas:")
            for ward in WardArea:
                print(f"  {ward.name}: {ward.value}")
            primary_directorate = input("Primary directorate: ")
            
            itu_trained = input("ITU trained (y/n): ").lower() == 'y'
            warfarin_trained = input("Warfarin trained (y/n): ").lower() == 'y'
            default_pharmacist = input("Default dispensary pharmacist (y/n): ").lower() == 'y'
            
            args = argparse.Namespace()
            args.name = name
            args.email = email
            args.band = band
            args.primary_directorate = primary_directorate
            args.itu_trained = itu_trained
            args.warfarin_trained = warfarin_trained
            args.default_pharmacist = default_pharmacist
            
            add_pharmacist(args, data_manager)
            
        elif choice == '3':
            # List pharmacists
            list_pharmacists(data_manager)
            
        elif choice == '4':
            print("Exiting...")
            break
            
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point for the pharmacy rota generator."""
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    print("Welcome to the Pharmacy Rota Generator!")
    
    # Initialize data manager
    data_manager = DataManager()
    
    if args.command == 'generate':
        generate_rota(args, data_manager)
    elif args.command == 'add-pharmacist':
        add_pharmacist(args, data_manager)
    elif args.command == 'list-pharmacists':
        list_pharmacists(data_manager)
    elif args.command == 'interactive' or args.command is None:
        interactive_mode(data_manager)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()