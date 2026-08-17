from datetime import date
from app import db
from app.models import Subscription


def test_calendar_view(auth_client, app, auth_user):
    """Test calendar route and rendering of events."""
    with app.app_context():
        sub = Subscription(
            user_id=auth_user,
            name='Calendar Test Sub',
            amount=29.99,
            currency='USD',
            billing_cycle='monthly',
            next_due_date=date(2026, 8, 20)
        )
        db.session.add(sub)
        db.session.commit()

    response = auth_client.get('/subscriptions/calendar?year=2026&month=8')
    assert response.status_code == 200
    assert b'Calendar Test Sub' in response.data
    assert b'August 2026' in response.data
