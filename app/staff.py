from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db
from models.baggage import Baggage
from models.assistance import AssistanceRequest

staff_bp = Blueprint(
    "staff",
    __name__,
    url_prefix="/staff"
)


def staff_only():
    return current_user.is_authenticated and current_user.role == "staff"


@staff_bp.route("/dashboard")
@login_required
def dashboard():

    if not staff_only():
        flash("Staff access required.", "error")
        return redirect(url_for("main.home"))

    baggage = Baggage.query.order_by(
        Baggage.priority_score.desc()
    ).all()

    assistance = AssistanceRequest.query.order_by(
        AssistanceRequest.created_at.desc()
    ).all()

    return render_template(
        "staff/dashboard.html",
        baggage=baggage,
        assistance=assistance
    )


@staff_bp.route("/baggage/<int:baggage_id>/update", methods=["POST"])
@login_required
def update_baggage(baggage_id):

    if not staff_only():
        flash("Staff access required.", "error")
        return redirect(url_for("main.home"))

    baggage = Baggage.query.get_or_404(baggage_id)

    status = request.form.get("status")

    valid_statuses = [
        "Checked-in",
        "Processing",
        "Loaded",
        "Arrived",
        "Claim Ready",
        "Collected"
    ]

    if status in valid_statuses:
        baggage.status = status
        db.session.commit()
        flash("Baggage status updated.", "success")

    return redirect(url_for("staff.dashboard"))


@staff_bp.route("/assistance/<int:request_id>/resolve", methods=["POST"])
@login_required
def resolve_assistance(request_id):

    if not staff_only():
        flash("Staff access required.", "error")
        return redirect(url_for("main.home"))

    req = AssistanceRequest.query.get_or_404(request_id)
    req.status = "Resolved"

    db.session.commit()

    flash("Assistance request resolved.", "success")

    return redirect(url_for("staff.dashboard"))
