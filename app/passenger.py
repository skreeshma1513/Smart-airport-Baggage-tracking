from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db
from models.passenger import Passenger
from models.baggage import Baggage
from models.assistance import AssistanceRequest

passenger_bp = Blueprint(
    "passenger",
    __name__,
    url_prefix="/passenger"
)


@passenger_bp.route("/dashboard")
@login_required
def dashboard():

    profile = Passenger.query.filter_by(
        user_id=current_user.id
    ).first()

    baggage = []

    if profile:
        baggage = Baggage.query.filter_by(
            passenger_id=profile.id
        ).all()

    return render_template(
        "passenger/dashboard.html",
        profile=profile,
        baggage=baggage
    )


@passenger_bp.route("/baggage/<int:baggage_id>")
@login_required
def baggage_details(baggage_id):

    profile = Passenger.query.filter_by(
        user_id=current_user.id
    ).first()

    if not profile:
        flash("Passenger profile not found.", "error")
        return redirect(url_for("passenger.dashboard"))

    baggage = Baggage.query.filter_by(
        id=baggage_id,
        passenger_id=profile.id
    ).first_or_404()

    return render_template(
        "passenger/baggage.html",
        baggage=baggage
    )


@passenger_bp.route("/assistance", methods=["GET", "POST"])
@login_required
def assistance():

    profile = Passenger.query.filter_by(
        user_id=current_user.id
    ).first()

    if not profile:
        flash("Passenger profile not found.", "error")
        return redirect(url_for("passenger.dashboard"))

    if request.method == "POST":

        request_type = request.form.get("request_type")
        location = request.form.get("location")

        if not request_type or not location:
            flash("Please complete all fields.", "error")
        else:
            req = AssistanceRequest(
                passenger_id=profile.id,
                request_type=request_type,
                location=location
            )

            db.session.add(req)
            db.session.commit()

            flash("Assistance request submitted.", "success")

    requests = AssistanceRequest.query.filter_by(
        passenger_id=profile.id
    ).order_by(
        AssistanceRequest.created_at.desc()
    ).all()

    return render_template(
        "passenger/assistance.html",
        requests=requests
    )


@passenger_bp.route("/notifications")
@login_required
def notifications():
    return render_template(
        "passenger/notifications.html"
    )
