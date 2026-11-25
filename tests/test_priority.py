from services.priority_engine import calculate_priority

def test_high_priority():
    score, level = calculate_priority(
        age=80,
        assistance_required=True,
        mobility_requirement=True,
        connection_minutes=20
    )

    assert score >= 60
    assert level == "HIGH"


def test_normal_priority():
    score, level = calculate_priority(
        age=30,
        assistance_required=False,
        mobility_requirement=False,
        connection_minutes=120
    )

    assert level == "NORMAL"
