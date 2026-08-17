from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Settings, Subscription
from app.services.currency import CurrencyService
from app.services.notifications import NotificationService

bp = Blueprint('settings', __name__)

AVAILABLE_CURRENCIES = [
    ('TRY', 'Turkish Lira (₺)'),
    ('USD', 'US Dollar ($)'),
    ('EUR', 'Euro (€)'),
    ('GBP', 'British Pound (£)'),
    ('CAD', 'Canadian Dollar (CA$)'),
    ('AUD', 'Australian Dollar (AU$)'),
    ('JPY', 'Japanese Yen (¥)'),
    ('CHF', 'Swiss Franc (CHF)'),
]


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """User preferences & settings."""
    settings = Settings.get_settings(user_id=current_user.id)

    if request.method == 'POST':
        primary_currency = request.form.get('primary_currency', 'TRY').upper()
        display_name = request.form.get('display_name', '').strip()
        webhook_url = request.form.get('webhook_url', '').strip()
        notify_days_before = request.form.get('notify_days_before', type=int) or 3

        settings.primary_currency = primary_currency
        settings.webhook_url = webhook_url or None
        settings.notify_days_before = max(1, min(30, notify_days_before))

        if display_name:
            current_user.display_name = display_name
        else:
            current_user.display_name = None

        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings.html',
        settings=settings,
        currencies=AVAILABLE_CURRENCIES
    )


@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change account password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('settings.index'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('settings.index'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('settings.index'))

    current_user.set_password(new_password)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('settings.index'))


@bp.route('/test-webhook', methods=['POST'])
@login_required
def test_webhook():
    """Dispatch a test notification to user's configured webhook URL."""
    settings = Settings.get_settings(user_id=current_user.id)
    if not settings.webhook_url:
        flash('Please configure and save a Webhook URL first.', 'error')
        return redirect(url_for('settings.index'))

    # Grab 2 sample active subscriptions for demonstration
    sample_subs = Subscription.query.filter_by(user_id=current_user.id, is_active=True).limit(3).all()

    success, message = NotificationService.send_webhook(
        webhook_url=settings.webhook_url,
        title="SubTracker Test Alert",
        message=f"Hello {current_user.display_name or current_user.username}! This is a test notification from your Subscription Tracker.",
        subscriptions=sample_subs
    )

    if success:
        flash('✓ Test webhook delivered successfully!', 'success')
    else:
        flash(f'✗ Failed to deliver webhook: {message}', 'error')

    return redirect(url_for('settings.index'))
