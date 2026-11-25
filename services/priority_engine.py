def calculate_priority(
    age,
    assistance_required,
    mobility_requirement,
    connection_minutes
):
    score = 0

    if age >= 75:
        score += 25
    elif age >= 65:
        score += 15

    if assistance_required:
        score += 25

    if mobility_requirement:
        score += 30

    if connection_minutes <= 30:
        score += 20
    elif connection_minutes <= 60:
        score += 10

    if score >= 60:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "NORMAL"

    return score, level
