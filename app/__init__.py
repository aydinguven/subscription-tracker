from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = ''


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.subscriptions import bp as subscriptions_bp
    from app.routes.payments import bp as payments_bp
    from app.routes.categories import bp as categories_bp
    from app.routes.payment_methods import bp as payment_methods_bp
    from app.routes.data import bp as data_bp
    from app.routes.api import bp as api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(payment_methods_bp, url_prefix='/payment-methods')
    app.register_blueprint(data_bp, url_prefix='/data')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app


def seed_default_categories(user_id):
    """Seed default categories for a new user."""
    from app.models import Category
    
    existing = Category.query.filter_by(user_id=user_id).count()
    if existing == 0:
        default_categories = [
            Category(user_id=user_id, name='Streaming', color='#ef4444', icon='tv'),
            Category(user_id=user_id, name='Software', color='#6366f1', icon='code'),
            Category(user_id=user_id, name='Gaming', color='#10b981', icon='gamepad-2'),
            Category(user_id=user_id, name='Cloud', color='#3b82f6', icon='cloud'),
            Category(user_id=user_id, name='Music', color='#8b5cf6', icon='music'),
            Category(user_id=user_id, name='Other', color='#6b7280', icon='box'),
        ]
        for cat in default_categories:
            db.session.add(cat)
        db.session.commit()
