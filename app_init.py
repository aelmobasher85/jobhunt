from flask import Flask
from routes import register_routes
from models import db

# The app initialization must be done in this module to avoid circular dependency problems.

def create_initialized_flask_app():
    # DO NOT INSTANTIATE THE FLASK APP IN ANOTHER MODULE.
    app = Flask(__name__, static_folder='static')

    # Initialize database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///upwork_alerts.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    return app