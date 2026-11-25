from flask import Blueprint, jsonify
from flask_login import login_required

from models.baggage import Baggage

api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)


@api_bp.route("/baggage")
@login_required
def baggage_api():

    baggage = Baggage.query.order_by(
        Baggage.priority_score.desc()
    ).all()

    return jsonify([
        {
            "baggage_id": item.baggage_id,
            "status": item.status,
            "priority_score": item.priority_score,
            "priority_level": item.priority_level,
            "estimated_minutes": item.estimated_minutes,
            "delay_risk": item.delay_risk
        }
        for item in baggage
    ])
