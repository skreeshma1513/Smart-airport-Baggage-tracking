from models import db

class Passenger(db.Model):
    __tablename__ = "passengers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    age = db.Column(db.Integer, nullable=False)
    assistance_required = db.Column(db.Boolean, default=False)
    assistance_type = db.Column(db.String(100))
    mobility_requirement = db.Column(db.Boolean, default=False)
    connection_minutes = db.Column(db.Integer, default=120)

    user = db.relationship("User", backref="passenger_profile")
