"""
Scheduler for the pharmacy rota generator.

This module contains the core logic for generating rotas based on 
pharmacist availability, ward requirements, and other constraints.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from models import (
    Band, Day, WardArea, ClinicType, DispensarySlot, ShiftType,
    Pharmacist, Clinic, DispensaryShift, WardAssignment, 
    ClinicAssignment, LunchCoverAssignment, DailyRota, WeeklyRota
)
from config import (
    DEFAULT_WARD_REQUIREMENTS, DISPENSARY_SLOTS, DEFAULT_CLINICS,
    DEFAULT_LUNCH_START, DEFAULT_LUNCH_END
)

logger = logging.getLogger(__name__)


class RotaScheduler:
    """Class responsible for generating pharmacy rotas."""
    
    def __init__(self, pharmacists: List[Pharmacist], 
                 ward_requirements: Dict = None,
                 clinics: List[Clinic] = None):
        """
        Initialize the scheduler with pharmacist staff and requirements.
        
        Args:
            pharmacists: List of available pharmacists
            ward_requirements: Custom ward requirements (uses defaults if None)
            clinics: Custom clinic list (uses defaults if None)
        """
        self.pharmacists = pharmacists
        self.ward_requirements = ward_requirements or DEFAULT_WARD_REQUIREMENTS
        self.clinics = clinics or DEFAULT_CLINICS
        
    def generate_weekly_rota(self, start_date: datetime) -> WeeklyRota:
        """
        Generate a weekly rota starting from the given date.
        
        Args:
            start_date: Starting date for the rota (should be a Monday)
            
        Returns:
            WeeklyRota object with assignments for the week
        """
        # Initialize the weekly rota
        weekly_rota = WeeklyRota(start_date=start_date)
        
        # Generate rota for each day
        for day in Day:
            daily_rota = self._generate_daily_rota(day, weekly_rota.daily_rotas[day].date)
            weekly_rota.daily_rotas[day] = daily_rota
            
        # Apply additional constraints and optimization
        self._balance_dispensary_shifts(weekly_rota)
        
        return weekly_rota
    
    def _generate_daily_rota(self, day: Day, date: datetime) -> DailyRota:
        """
        Generate a rota for a single day.
        
        Args:
            day: Day of the week
            date: Date for the rota
            
        Returns:
            DailyRota object with assignments for the day
        """
        # Initialize daily rota
        daily_rota = DailyRota(day=day, date=date)
        
        # Get available pharmacists for this day
        available_pharmacists = [p for p in self.pharmacists if p.availability.get(day, False)]
        
        if not available_pharmacists:
            logger.warning(f"No pharmacists available for {day.value}")
            return daily_rota
        
        # 1. Assign clinics first (highest priority, immovable)
        daily_clinics = [clinic for clinic in self.clinics if clinic.day == day]
        self._assign_clinics(daily_rota, daily_clinics, available_pharmacists)
        
        # Get pharmacists who have been assigned to clinics
        assigned_clinic_pharmacists = {assign.pharmacist for assign in daily_rota.clinic_assignments}
        
        # 2. Assign dispensary shifts (must be covered)
        remaining_pharmacists = [p for p in available_pharmacists if p not in assigned_clinic_pharmacists]
        self._assign_dispensary_shifts(daily_rota, remaining_pharmacists)
        
        # Get pharmacists who have been assigned to dispensary
        assigned_dispensary_pharmacists = {shift.assigned_pharmacist for shift in daily_rota.dispensary_shifts 
                                         if shift.assigned_pharmacist is not None}
        
        # 3. Assign lunch coverage for dispensary
        dispensary_pharmacist = self._get_dispensary_pharmacist(daily_rota)
        if dispensary_pharmacist:
            # Find someone to cover lunch
            lunch_cover_candidates = [p for p in available_pharmacists 
                                    if p not in assigned_clinic_pharmacists and 
                                       p != dispensary_pharmacist]
            if lunch_cover_candidates:
                daily_rota.lunch_cover = LunchCoverAssignment(
                    day=day,
                    pharmacist=lunch_cover_candidates[0],
                    start_time=DEFAULT_LUNCH_START,
                    end_time=DEFAULT_LUNCH_END
                )
        
        # 4. Assign ward areas
        already_assigned = assigned_clinic_pharmacists.union(assigned_dispensary_pharmacists)
        if daily_rota.lunch_cover:
            already_assigned.add(daily_rota.lunch_cover.pharmacist)
            
        remaining_pharmacists = [p for p in available_pharmacists if p not in already_assigned]
        
        self._assign_ward_areas(daily_rota, remaining_pharmacists, already_assigned)
        
        return daily_rota
    
    def _assign_clinics(self, daily_rota: DailyRota, clinics: List[Clinic], 
                        available_pharmacists: List[Pharmacist]) -> None:
        """
        Assign pharmacists to clinics.
        
        Args:
            daily_rota: The daily rota to update
            clinics: List of clinics for the day
            available_pharmacists: List of available pharmacists
        """
        # Focus on required clinics first (prioritize PHAR2PSP)
        priority_clinics = sorted(clinics, key=lambda c: 0 if c.clinic_type == ClinicType.PHAR2PSP else 1)
        
        for clinic in priority_clinics:
            # Find appropriate pharmacists for this clinic
            suitable_pharmacists = [p for p in available_pharmacists 
                                  if p.warfarin_trained and 
                                  p not in [a.pharmacist for a in daily_rota.clinic_assignments]]
            
            if suitable_pharmacists:
                assignment = ClinicAssignment(
                    clinic=clinic,
                    day=daily_rota.day,
                    pharmacist=suitable_pharmacists[0]
                )
                daily_rota.clinic_assignments.append(assignment)
    
    def _assign_dispensary_shifts(self, daily_rota: DailyRota, 
                                available_pharmacists: List[Pharmacist]) -> None:
        """
        Assign pharmacists to dispensary shifts.
        
        Args:
            daily_rota: The daily rota to update
            available_pharmacists: List of available pharmacists
        """
        # Filter pharmacists who can cover dispensary (band 6 and 7)
        dispensary_pharmacists = [p for p in available_pharmacists if p.can_cover_dispensary]
        
        # If no suitable pharmacists, fall back to any available pharmacist
        if not dispensary_pharmacists and available_pharmacists:
            dispensary_pharmacists = available_pharmacists
            
        # Check if there's a dedicated dispensary pharmacist first
        dedicated_dispensary = [p for p in dispensary_pharmacists if p.default_pharmacist]
        
        if dedicated_dispensary:
            # Assign all slots to dedicated dispensary pharmacist
            for slot in DISPENSARY_SLOTS:
                shift = DispensaryShift(day=daily_rota.day, slot=slot, 
                                       assigned_pharmacist=dedicated_dispensary[0])
                daily_rota.dispensary_shifts.append(shift)
        else:
            # Assign slots to different pharmacists
            for slot in DISPENSARY_SLOTS:
                # Check if any clinic assignments conflict with this slot
                clinic_conflicts = set()
                for clinic_assignment in daily_rota.clinic_assignments:
                    if slot in clinic_assignment.clinic.conflicting_dispensary_slots:
                        clinic_conflicts.add(clinic_assignment.pharmacist)
                
                # Find pharmacists not assigned to conflicting clinics
                available_for_slot = [p for p in dispensary_pharmacists if p not in clinic_conflicts]
                
                # Exclude pharmacists who already have a dispensary shift today
                already_assigned = {shift.assigned_pharmacist for shift in daily_rota.dispensary_shifts
                                  if shift.assigned_pharmacist is not None}
                
                # Try to avoid giving multiple dispensary shifts to the same pharmacist
                preferred_pharmacists = [p for p in available_for_slot if p not in already_assigned]
                
                if preferred_pharmacists:
                    # Assign to pharmacist who doesn't already have a dispensary shift
                    shift = DispensaryShift(day=daily_rota.day, slot=slot, 
                                           assigned_pharmacist=preferred_pharmacists[0])
                elif available_for_slot:
                    # If necessary, assign to pharmacist who already has a shift
                    shift = DispensaryShift(day=daily_rota.day, slot=slot, 
                                           assigned_pharmacist=available_for_slot[0])
                else:
                    # No suitable pharmacist found for this slot
                    shift = DispensaryShift(day=daily_rota.day, slot=slot)
                    logger.warning(f"No pharmacist available for dispensary {slot.value} on {daily_rota.day.value}")
                
                daily_rota.dispensary_shifts.append(shift)
    
    def _assign_ward_areas(self, daily_rota: DailyRota, unassigned_pharmacists: List[Pharmacist],
                         already_assigned: Set[Pharmacist]) -> None:
        """
        Assign pharmacists to ward areas.
        
        Args:
            daily_rota: The daily rota to update
            unassigned_pharmacists: List of pharmacists not yet assigned
            already_assigned: Set of pharmacists already assigned to other duties
        """
        # Get all pharmacists (including those with other assignments)
        all_pharmacists = unassigned_pharmacists + list(already_assigned)
        
        # Track assignments made to each ward
        ward_assignments = {ward_area: [] for ward_area in WardArea}
        
        # First, assign ITU if required and if trained staff available
        itu_requirement = self.ward_requirements.get((WardArea.ITU, daily_rota.day))
        if itu_requirement and itu_requirement.min_pharmacists > 0:
            itu_trained = [p for p in unassigned_pharmacists if p.can_cover_itu]
            
            if itu_trained:
                assignment = WardAssignment(
                    ward_area=WardArea.ITU,
                    day=daily_rota.day,
                    pharmacist=itu_trained[0]
                )
                daily_rota.ward_assignments.append(assignment)
                unassigned_pharmacists.remove(itu_trained[0])
                ward_assignments[WardArea.ITU].append(itu_trained[0])
        
        # Next, assign pharmacists to their primary directorates if possible
        for pharmacist in list(unassigned_pharmacists):
            primary_area = pharmacist.primary_directorate
            requirement = self.ward_requirements.get((primary_area, daily_rota.day))
            
            # Check if more pharmacists needed in this area
            if requirement and len(ward_assignments[primary_area]) < requirement.ideal_pharmacists:
                assignment = WardAssignment(
                    ward_area=primary_area,
                    day=daily_rota.day,
                    pharmacist=pharmacist
                )
                daily_rota.ward_assignments.append(assignment)
                unassigned_pharmacists.remove(pharmacist)
                ward_assignments[primary_area].append(pharmacist)
        
        # Finally, fill remaining slots based on minimum requirements and preferences
        for ward_area in WardArea:
            requirement = self.ward_requirements.get((ward_area, daily_rota.day))
            if not requirement:
                continue
                
            # Skip ITU (already handled)
            if ward_area == WardArea.ITU:
                continue
                
            # Check if minimum requirements are met
            while len(ward_assignments[ward_area]) < requirement.min_pharmacists and unassigned_pharmacists:
                # Find the best match based on preferences
                best_match = None
                best_rank = float('inf')
                
                for pharmacist in unassigned_pharmacists:
                    # Check preferences for this ward area
                    for pref in pharmacist.preferences:
                        if pref.ward_area == ward_area and pref.rank < best_rank:
                            best_match = pharmacist
                            best_rank = pref.rank
                
                # If no preference found, just take the first available
                if best_match is None and unassigned_pharmacists:
                    best_match = unassigned_pharmacists[0]
                
                if best_match:
                    assignment = WardAssignment(
                        ward_area=ward_area,
                        day=daily_rota.day,
                        pharmacist=best_match
                    )
                    daily_rota.ward_assignments.append(assignment)
                    unassigned_pharmacists.remove(best_match)
                    ward_assignments[ward_area].append(best_match)
                else:
                    break
    
    def _get_dispensary_pharmacist(self, daily_rota: DailyRota) -> Optional[Pharmacist]:
        """
        Get the dedicated dispensary pharmacist for the day, if there is one.
        
        Args:
            daily_rota: The daily rota
            
        Returns:
            The dedicated dispensary pharmacist or None
        """
        # Check if all dispensary shifts are assigned to the same pharmacist
        dispensary_pharmacists = {shift.assigned_pharmacist for shift in daily_rota.dispensary_shifts
                               if shift.assigned_pharmacist is not None}
        
        if len(dispensary_pharmacists) == 1:
            return next(iter(dispensary_pharmacists))
        return None
    
    def _balance_dispensary_shifts(self, weekly_rota: WeeklyRota) -> None:
        """
        Balance dispensary shifts across the week to ensure fair distribution.
        
        Args:
            weekly_rota: The weekly rota to optimize
        """
        # Count dispensary shifts per pharmacist
        shift_counts = {}
        
        for day_rota in weekly_rota.daily_rotas.values():
            for shift in day_rota.dispensary_shifts:
                if shift.assigned_pharmacist:
                    pharmacist_id = shift.assigned_pharmacist.id
                    shift_counts[pharmacist_id] = shift_counts.get(pharmacist_id, 0) + 1
        
        # Identify pharmacists with too many shifts (more than 3 per week)
        overloaded = {pid: count for pid, count in shift_counts.items() if count > 3}
        underloaded = {pid: count for pid, count in shift_counts.items() if count < 2}
        
        if not overloaded or not underloaded:
            return
        
        # Try to redistribute shifts from overloaded to underloaded pharmacists
        for day_rota in weekly_rota.daily_rotas.values():
            if not overloaded:
                break
                
            for shift in day_rota.dispensary_shifts:
                if not shift.assigned_pharmacist:
                    continue
                    
                pharmacist_id = shift.assigned_pharmacist.id
                
                # Check if this pharmacist is overloaded
                if pharmacist_id in overloaded:
                    # Find an underloaded pharmacist who's available this day
                    for p_id, _ in underloaded.items():
                        underloaded_pharmacist = next(
                            (p for p in self.pharmacists if p.id == p_id and p.availability.get(day_rota.day, False)),
                            None
                        )
                        
                        if underloaded_pharmacist:
                            # Reassign the shift
                            shift.assigned_pharmacist = underloaded_pharmacist
                            
                            # Update counts
                            overloaded[pharmacist_id] -= 1
                            if overloaded[pharmacist_id] <= 3:
                                del overloaded[pharmacist_id]
                                
                            underloaded[p_id] += 1
                            if underloaded[p_id] >= 2:
                                del underloaded[p_id]
                                
                            break