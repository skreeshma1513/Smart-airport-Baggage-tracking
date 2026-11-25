def estimate_baggage_time(status):
    values = {
        "Checked-in": 25,
        "Processing": 20,
        "Loaded": 15,
        "Arrived": 8,
        "Claim Ready": 2,
        "Collected": 0
    }

    return values.get(status, 15)


def calculate_delay_risk(estimated_minutes):
    if estimated_minutes >= 25:
        return "HIGH"
    elif estimated_minutes >= 15:
        return "MEDIUM"
    return "LOW"
