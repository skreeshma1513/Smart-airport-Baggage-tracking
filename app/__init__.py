from flask import Flask
from config import Config

from models import db, login_manager


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from models.user import User
    from models.passenger import Passenger
    from models.flight import Flight
    from models.baggage import Baggage
    from models.assistance import AssistanceRequest

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main
    from app.auth import auth
    from app.passenger import passenger_bp
    from app.staff import staff_bp
    from app.admin import admin_bp
    from app.api import api_bp

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(passenger_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app