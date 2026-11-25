import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "smart-airport-development-secret-key"
    )

    # SQLite is used initially so the project can run immediately.
    # You can change this to MySQL later in .env
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///smart_airport.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
