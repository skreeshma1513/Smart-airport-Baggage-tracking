from datetime import datetime
from models import db

class Baggage(db.Model):
    __tablename__ = "baggage"

    id = db.Column(db.Integer, primary_key=True)
    baggage_id = db.Column(db.String(50), unique=True, nullable=False)

    passenger_id = db.Column(
        db.Integer,
        db.ForeignKey("passengers.id"),
        nullable=False
    )

    flight_id = db.Column(
        db.Integer,
        db.ForeignKey("flights.id"),
        nullable=False
    )

    status = db.Column(db.String(50), default="Checked-in")

    priority_score = db.Column(db.Integer, default=0)
    priority_level = db.Column(db.String(30), default="NORMAL")

    estimated_minutes = db.Column(db.Integer, default=20)
    delay_risk = db.Column(db.String(30), default="LOW")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    passenger = db.relationship("Passenger", backref="baggage")
    flight = db.relationship("Flight", backref="baggage")
