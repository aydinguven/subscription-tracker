from app.models import User, Settings


def test_update_settings(auth_client, app, auth_user):
    """Test updating user settings (primary currency, display name, notification days)."""
    response = auth_client.post('/settings/', data={
        'primary_currency': 'USD',
        'display_name': 'Aydin Chief',
        'webhook_url': 'https://discord.com/api/webhooks/12345/abcdef',
        'notify_days_before': '5'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        settings = Settings.query.filter_by(user_id=auth_user).first()
        assert settings is not None
        assert settings.primary_currency == 'USD'
        assert settings.webhook_url == 'https://discord.com/api/webhooks/12345/abcdef'
        assert settings.notify_days_before == 5

        user = User.query.get(auth_user)
        assert user.display_name == 'Aydin Chief'


def test_change_password(auth_client, app, auth_user):
    """Test password change in settings."""
    # Successful password change
    response = auth_client.post('/settings/change-password', data={
        'current_password': 'password123',
        'new_password': 'brandnewpassword',
        'confirm_password': 'brandnewpassword'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        user = User.query.get(auth_user)
        assert user.check_password('brandnewpassword') is True
