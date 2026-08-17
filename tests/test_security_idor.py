from app import db
from app.models import Subscription, Category, PaymentMethod


def test_user_cannot_access_or_edit_other_user_subscription(client, app, auth_user, other_user):
    """Verify that User 2 cannot access, edit, or delete User 1's subscriptions (IDOR prevention)."""
    with app.app_context():
        sub = Subscription(
            user_id=auth_user,
            name='User 1 Secret Subscription',
            amount=500.0,
            currency='USD'
        )
        db.session.add(sub)
        db.session.commit()
        sub_id = sub.id

    # Client logs in as User 2 (otheruser)
    client.post('/login', data={'username': 'otheruser', 'password': 'password123'})

    # User 2 tries to view User 1's subscription edit page -> 404
    resp_get = client.get(f'/subscriptions/edit/{sub_id}')
    assert resp_get.status_code == 404

    # User 2 tries to POST update User 1's subscription -> 404
    resp_post = client.post(f'/subscriptions/edit/{sub_id}', data={
        'name': 'Hacked Name',
        'amount': '1.0'
    })
    assert resp_post.status_code == 404

    # User 2 tries to delete User 1's subscription -> 404
    resp_del = client.post(f'/subscriptions/delete/{sub_id}')
    assert resp_del.status_code == 404

    # User 1's subscription remains unchanged in the database
    with app.app_context():
        sub_check = db.session.get(Subscription, sub_id)
        assert sub_check is not None
        assert sub_check.name == 'User 1 Secret Subscription'
        assert sub_check.amount == 500.0


def test_user_cannot_link_other_user_category_or_payment_method(client, app, auth_user, other_user):
    """Verify that User 1 cannot link User 2's Category or Payment Method to their own subscription."""
    with app.app_context():
        other_cat = Category(user_id=other_user, name='Other User Private Category', color='#123456')
        other_pm = PaymentMethod(user_id=other_user, name='Other User Credit Card', method_type='credit_card')
        db.session.add_all([other_cat, other_pm])
        db.session.commit()
        other_cat_id = other_cat.id
        other_pm_id = other_pm.id

    # Login as User 1 (testuser)
    client.post('/login', data={'username': 'testuser', 'password': 'password123'})

    # User 1 tries to create a subscription with User 2's category_id and payment_method_id
    client.post('/subscriptions/add', data={
        'name': 'User 1 Subscription',
        'category_id': str(other_cat_id),
        'payment_method_id': str(other_pm_id),
        'amount': '50.0',
        'currency': 'TRY'
    })

    with app.app_context():
        sub = Subscription.query.filter_by(user_id=auth_user, name='User 1 Subscription').first()
        assert sub is not None
        # The IDs must be sanitized to None because they belong to another user
        assert sub.category_id is None
        assert sub.payment_method_id is None
