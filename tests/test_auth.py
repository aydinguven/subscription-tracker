import pytest
from app.models import User, Category, Settings


def test_register_success(client, app):
    """Test user registration successfully creates user, default categories, and settings."""
    response = client.post('/register', data={
        'username': 'newuser',
        'display_name': 'New User',
        'password': 'secretpassword',
        'confirm_password': 'secretpassword'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.display_name == 'New User'
        assert user.check_password('secretpassword') is True

        categories = Category.query.filter_by(user_id=user.id).all()
        assert len(categories) > 0

        settings = Settings.query.filter_by(user_id=user.id).first()
        assert settings is not None
        assert settings.primary_currency == 'TRY'


def test_register_password_mismatch(client):
    """Test registration failure on password mismatch."""
    response = client.post('/register', data={
        'username': 'mismatchuser',
        'password': 'password1',
        'confirm_password': 'password2'
    }, follow_redirects=True)

    assert b'Passwords do not match' in response.data


def test_login_success(client, auth_user):
    """Test successful login and redirection."""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Dashboard' in response.data


def test_login_invalid_credentials(client, auth_user):
    """Test login failure on bad password."""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)

    assert b'Invalid username or password' in response.data


def test_logout(auth_client):
    """Test user logout."""
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign In' in response.data or b'Login' in response.data
