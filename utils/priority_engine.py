"""
AI-Assisted Intelligent Priority Scoring Engine
================================================
This module implements a software-based intelligent priority scoring system
for airport baggage handling. It calculates priority scores based on passenger
category, assistance requirements, and other factors.

NOTE: This is an academic prototype. The priority scores are software-based
recommendations for airport staff. This is NOT a clinically validated or
medically accurate AI system.

Future Integration:
- ESP32 + Barcode Scanner can feed data via REST API
- Priority decisions are returned as JSON for hardware actuators
"""

import random


def calculate_priority(category, assistance_required=None, age=None):
    """
    Calculate priority score based on passenger category and assistance needs.

    Args:
        category (str): Passenger category (Normal, Elderly, Pregnant,
                        Differently-Abled, Special Assistance)
        assistance_required (str): Type of assistance needed
        age (int): Passenger age (used for elderly scoring)

    Returns:
        dict: {score, level, reason}
    """
    score = 0
    reasons = []

    # Category-based scoring
    if category == 'Elderly':
        score += 40
        reasons.append('Elderly passenger requires priority handling')
        if age and age >= 80:
            score += 15
            reasons.append('Age 80+ (additional priority)')
        elif age and age >= 70:
            score += 10
            reasons.append('Age 70+ (additional priority)')
    elif category == 'Pregnant':
        score += 45
        reasons.append('Pregnant passenger requires priority handling')
    elif category == 'Differently-Abled':
        score += 50
        reasons.append('Differently-abled passenger requires priority handling')
    elif category == 'Special Assistance':
        score += 35
        reasons.append('Passenger has requested special assistance')
    else:
        score += 10
        reasons.append('Normal passenger (standard processing)')

    # Assistance-based scoring
    if assistance_required and assistance_required not in ('None', '', 'No'):
        if assistance_required == 'Wheelchair Assistance':
            score += 20
            reasons.append('Wheelchair assistance required')
        elif assistance_required == 'Elderly Assistance':
            score += 15
            reasons.append('Elderly assistance required')
        elif assistance_required == 'Baggage Collection Assistance':
            score += 10
            reasons.append('Baggage collection assistance required')
        elif assistance_required == 'General Assistance':
            score += 10
            reasons.append('General assistance required')
        else:
            score += 10
            reasons.append(f'Assistance required: {assistance_required}')

    # Cap score at 100
    score = min(score, 100)

    # Determine priority level
    if score >= 55:
        level = 'HIGH'
    elif score >= 25:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        'score': score,
        'level': level,
        'reason': '. '.join(reasons) + '.'
    }


def estimate_waiting_time(queue_position, priority_level, status, total_processing=1):
    """
    Estimate waiting time based on queue position and other factors.

    Args:
        queue_position (int): Position in queue (1-based)
        priority_level (str): HIGH, MEDIUM, or LOW
        status (str): Current baggage status
        total_processing (int): Number of baggage currently being processed

    Returns:
        int: Estimated waiting time in minutes
    """
    if status in ('Claim Ready', 'Collected'):
        return 0

    # Base time per position (minutes)
    base_time_per_position = 3

    # Adjust for priority
    priority_multiplier = {
        'HIGH': 0.5,
        'MEDIUM': 0.8,
        'LOW': 1.0
    }

    # Adjust for status
    status_offset = {
        'Checked In': 5,
        'Processing': 2,
        'Loaded': 0,
        'Arrived': 0,
        'Claim Ready': 0,
        'Collected': 0,
        'Delayed': 10
    }

    multiplier = priority_multiplier.get(priority_level, 1.0)
    offset = status_offset.get(status, 3)
    processing_factor = max(1, total_processing)

    wait_time = int((queue_position * base_time_per_position * multiplier + offset) / processing_factor)
    return max(1, min(wait_time, 60))


def calculate_delay_risk(queue_position, status, total_in_queue, flight_delayed=False):
    """
    Calculate delay risk for a baggage item.

    Args:
        queue_position (int): Position in queue
        status (str): Current baggage status
        total_in_queue (int): Total items in queue
        flight_delayed (bool): Whether the flight is delayed

    Returns:
        dict: {risk, reason}
    """
    risk_score = 0
    reasons = []

    # Queue congestion
    if total_in_queue > 20:
        risk_score += 3
        reasons.append('High queue congestion')
    elif total_in_queue > 10:
        risk_score += 2
        reasons.append('Moderate queue congestion')
    else:
        reasons.append('Normal queue levels')

    # Queue position
    if queue_position > 15:
        risk_score += 3
        reasons.append('Far back in queue')
    elif queue_position > 8:
        risk_score += 2
        reasons.append('Mid-queue position')

    # Status-based risk
    if status == 'Delayed':
        risk_score += 4
        reasons.append('Baggage already delayed')
    elif status == 'Checked In':
        risk_score += 1
        reasons.append('Baggage not yet processed')

    # Flight delay
    if flight_delayed:
        risk_score += 3
        reasons.append('Flight is delayed')

    # Determine risk level
    if risk_score >= 6:
        risk = 'HIGH'
    elif risk_score >= 3:
        risk = 'MEDIUM'
    else:
        risk = 'LOW'

    return {
        'risk': risk,
        'reason': '. '.join(reasons) + '.'
    }
