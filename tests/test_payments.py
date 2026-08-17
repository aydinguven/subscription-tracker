from datetime import date
from app import db
from app.models import Subscription, Payment


def test_record_payment_with_discount(auth_client, app, auth_user):
    """Test payment creation and automatic discount & savings calculations."""
    with app.app_context():
        sub = Subscription(
            user_id=auth_user,
            name='Cloud Storage',
            amount=100.0,
            currency='USD',
            billing_cycle='monthly',
            next_due_date=date(2026, 8, 1)
        )
        db.session.add(sub)
        db.session.commit()
        sub_id = sub.id

    # Record payment with discount ($80 paid out of $100 normal price)
    response = auth_client.post('/payments/add', data={
        'subscription_id': str(sub_id),
        'amount': '80.00',
        'original_amount': '100.00',
        'currency': 'USD',
        'paid_date': '2026-08-01',
        'notes': '20% Summer promo discount',
        'advance_date': 'on'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        payment = Payment.query.filter_by(user_id=auth_user, subscription_id=sub_id).first()
        assert payment is not None
        assert payment.amount == 80.0
        assert payment.original_amount == 100.0
        assert payment.discount == 20.0
        assert payment.discount_percent == 20.0

        # Verify subscription due date advanced
        sub = Subscription.query.get(sub_id)
        assert sub.next_due_date == date(2026, 9, 1)
