from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_app(app: Flask):
    """Initializes the database and creates tables if they don't exist."""
    db.init_app(app)
    with app.app_context():
        db.create_all()