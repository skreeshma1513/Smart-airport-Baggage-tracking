from app import create_app
from models import db

from models.user import User
from models.passenger import Passenger
from models.flight import Flight
from models.baggage import Baggage

from services.priority_engine import calculate_priority
from services.prediction import (
    estimate_baggage_time,
    calculate_delay_risk
)

app = create_app()

with app.app_context():

    # Clear old demo data
    Baggage.query.delete()
    Passenger.query.delete()
    Flight.query.delete()
    User.query.delete()

    # Passenger
    passenger_user = User(
        name="Demo Passenger",
        email="passenger@test.com",
        role="passenger"
    )
    passenger_user.set_password("pass123")

    db.session.add(passenger_user)
    db.session.commit()

    profile = Passenger(
        user_id=passenger_user.id,
        age=72,
        assistance_required=True,
        assistance_type="Mobility Assistance",
        mobility_requirement=True,
        connection_minutes=45
    )

    db.session.add(profile)

    # Staff
    staff = User(
        name="Airport Staff",
        email="staff@airport.com",
        role="staff"
    )
    staff.set_password("staff123")

    # Admin
    admin = User(
        name="System Admin",
        email="admin@airport.com",
        role="admin"
    )
    admin.set_password("admin123")

    db.session.add(staff)
    db.session.add(admin)

    # Flight
    flight = Flight(
        flight_number="SA2026",
        origin="Chennai",
        destination="Singapore",
        departure_time="10:30",
        arrival_time="13:00",
        status="Scheduled"
    )

    db.session.add(flight)
    db.session.commit()

    score, level = calculate_priority(
        age=profile.age,
        assistance_required=profile.assistance_required,
        mobility_requirement=profile.mobility_requirement,
        connection_minutes=profile.connection_minutes
    )

    eta = estimate_baggage_time("Checked-in")
    risk = calculate_delay_risk(eta)

    baggage = Baggage(
        baggage_id="BG2026",
        passenger_id=profile.id,
        flight_id=flight.id,
        status="Checked-in",
        priority_score=score,
        priority_level=level,
        estimated_minutes=eta,
        delay_risk=risk
    )

    db.session.add(baggage)
    db.session.commit()

    print("")
    print("======================================")
    print(" DEMO DATA CREATED SUCCESSFULLY")
    print("======================================")
    print("")
    print("Passenger:")
    print("Email: passenger@test.com")
    print("Password: pass123")
    print("")
    print("Staff:")
    print("Email: staff@airport.com")
    print("Password: staff123")
    print("")
    print("Admin:")
    print("Email: admin@airport.com")
    print("Password: admin123")
    print("")
    print("Baggage ID: BG2026")
    print("Priority Score:", score)
    print("Priority Level:", level)
    print("")
