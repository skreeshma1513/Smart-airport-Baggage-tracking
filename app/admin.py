from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from models.user import User
from models.baggage import Baggage
from models.assistance import AssistanceRequest

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


@admin_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "admin":
        flash("Admin access required.", "error")
        return redirect(url_for("main.home"))

    passenger_count = User.query.filter_by(
        role="passenger"
    ).count()

    staff_count = User.query.filter_by(
        role="staff"
    ).count()

    baggage_count = Baggage.query.count()

    assistance_count = AssistanceRequest.query.filter_by(
        status="Pending"
    ).count()

    return render_template(
        "admin/dashboard.html",
        passenger_count=passenger_count,
        staff_count=staff_count,
        baggage_count=baggage_count,
        assistance_count=assistance_count
    )
