from datetime import datetime
from models import db

class AssistanceRequest(db.Model):
    __tablename__ = "assistance_requests"

    id = db.Column(db.Integer, primary_key=True)

    passenger_id = db.Column(
        db.Integer,
        db.ForeignKey("passengers.id"),
        nullable=False
    )

    request_type = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(30), default="Pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    passenger = db.relationship(
        "Passenger",
        backref="assistance_requests"
    )
