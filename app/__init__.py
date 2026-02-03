from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    
    # Register blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.subscriptions import bp as subscriptions_bp
    from app.routes.payments import bp as payments_bp
    from app.routes.categories import bp as categories_bp
    from app.routes.payment_methods import bp as payment_methods_bp
    from app.routes.api import bp as api_bp
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(payment_methods_bp, url_prefix='/payment-methods')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create tables
    with app.app_context():
        db.create_all()
        # Seed default categories if empty
        from app.models import Category
        if Category.query.count() == 0:
            default_categories = [
                Category(name='Streaming', color='#ef4444', icon='tv'),
                Category(name='Software', color='#6366f1', icon='code'),
                Category(name='Gaming', color='#10b981', icon='gamepad-2'),
                Category(name='Cloud', color='#3b82f6', icon='cloud'),
                Category(name='Music', color='#8b5cf6', icon='music'),
                Category(name='Other', color='#6b7280', icon='box'),
            ]
            for cat in default_categories:
                db.session.add(cat)
            db.session.commit()
    
    return app
