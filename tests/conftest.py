import pytest
from app import create_app, db, seed_default_categories
from app.models import User, Category, PaymentMethod, Subscription, Payment, Settings
from config import TestingConfig


@pytest.fixture
def app():
    """Create and configure a fresh app instance for testing."""
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """An anonymous test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def auth_user(app):
    """Create a standard test user."""
    with app.app_context():
        user = User(username='testuser', display_name='Test User')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        seed_default_categories(user.id)
        return user.id


@pytest.fixture
def other_user(app):
    """Create a second test user for IDOR isolation tests."""
    with app.app_context():
        user = User(username='otheruser', display_name='Other User')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        seed_default_categories(user.id)
        return user.id


@pytest.fixture
def auth_client(app, auth_user):
    """A test client logged in as auth_user."""
    c = app.test_client()
    c.post('/login', data={'username': 'testuser', 'password': 'password123'})
    return c


@pytest.fixture
def other_client(app, other_user):
    """A test client logged in as other_user."""
    c = app.test_client()
    c.post('/login', data={'username': 'otheruser', 'password': 'password123'})
    return c
