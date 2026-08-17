from datetime import date
from dateutil.relativedelta import relativedelta
from app.models import Subscription, Category, PaymentMethod


def test_add_subscription(auth_client, app, auth_user):
    """Test creating a subscription with cycle and custom parameters."""
    with app.app_context():
        cat = Category.query.filter_by(user_id=auth_user, name='Streaming').first()
        cat_id = cat.id if cat else None

    response = auth_client.post('/subscriptions/add', data={
        'name': 'Netflix Premium',
        'category_id': str(cat_id) if cat_id else '',
        'amount': '199.99',
        'currency': 'TRY',
        'billing_cycle': 'monthly',
        'next_due_date': '2026-09-01',
        'url': 'netflix.com',
        'tags': 'entertainment, 4k',
        'notes': 'Family plan'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        sub = Subscription.query.filter_by(user_id=auth_user, name='Netflix Premium').first()
        assert sub is not None
        assert sub.amount == 199.99
        assert sub.currency == 'TRY'
        assert sub.billing_cycle == 'monthly'
        assert sub.monthly_amount == 199.99
        assert sub.yearly_amount == 199.99 * 12
        assert 'entertainment' in sub.tag_list
        assert sub.url == 'https://netflix.com'


def test_subscription_billing_cycles_calculations(app, auth_user):
    """Test normalized monthly and yearly math across all supported cycles."""
    with app.app_context():
        # Quarterly
        sub_qtr = Subscription(
            user_id=auth_user, name='Quarterly Sub', amount=300.0,
            billing_cycle='quarterly', next_due_date=date(2026, 1, 1)
        )
        assert sub_qtr.monthly_amount == 100.0
        assert sub_qtr.yearly_amount == 1200.0
        sub_qtr.advance_due_date()
        assert sub_qtr.next_due_date == date(2026, 4, 1)

        # Semi-Annual
        sub_semi = Subscription(
            user_id=auth_user, name='Semi Sub', amount=600.0,
            billing_cycle='semi-annual', next_due_date=date(2026, 1, 1)
        )
        assert sub_semi.monthly_amount == 100.0
        assert sub_semi.yearly_amount == 1200.0
        sub_semi.advance_due_date()
        assert sub_semi.next_due_date == date(2026, 7, 1)

        # Yearly
        sub_yr = Subscription(
            user_id=auth_user, name='Yearly Sub', amount=1200.0,
            billing_cycle='yearly', next_due_date=date(2026, 1, 1)
        )
        assert sub_yr.monthly_amount == 100.0
        assert sub_yr.yearly_amount == 1200.0
        sub_yr.advance_due_date()
        assert sub_yr.next_due_date == date(2027, 1, 1)


def test_toggle_and_delete_subscription(auth_client, app, auth_user):
    """Test toggling active status and deleting a subscription."""
    with app.app_context():
        from app import db
        sub = Subscription(user_id=auth_user, name='Temp Sub', amount=50.0, is_active=True)
        db.session.add(sub)
        db.session.commit()
        sub_id = sub.id

    # Toggle to inactive
    auth_client.post(f'/subscriptions/toggle/{sub_id}')
    with app.app_context():
        sub = Subscription.query.get(sub_id)
        assert sub.is_active is False

    # Delete
    auth_client.post(f'/subscriptions/delete/{sub_id}')
    with app.app_context():
        sub = Subscription.query.get(sub_id)
        assert sub is None
