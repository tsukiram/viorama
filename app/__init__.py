# C:\Users\rama\Desktop\viorama_app\viorama\app\__init__.py

from flask import Flask, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize SQLAlchemy instance (single instance)
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Register blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.general import bp as general_bp
    from app.routes.search import bp as search_bp
    from app.routes.saved import bp as saved_bp
    from app.routes.paper import bp as paper_bp
    from app.routes.home import bp as home_bp

    blueprints = [auth_bp, general_bp, search_bp, saved_bp, paper_bp, home_bp]
    for bp in blueprints:
        app.register_blueprint(bp)

    print(f"Registered blueprints: {[bp.name for bp in blueprints]}")

    # Create database tables within app context
    with app.app_context():
        db.create_all()

    # Session validation before each request
    @app.before_request
    def validate_user_session():
        # Skip validation for static files and auth routes
        if request.endpoint and ('static' in request.endpoint or 'auth' in request.endpoint):
            return

        # Check if user_id is in session and valid
        if 'user_id' in session:
            from app.models.models import User
            user = User.query.get(session['user_id'])
            if user is None:
                session.pop('user_id', None)
                return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('auth.login'))

    return app