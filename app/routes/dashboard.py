from datetime import date, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import extract
from app.models import Subscription, Payment, Settings
from app.services.currency import CurrencyService

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    """Main dashboard view with primary currency conversions."""
    today = date.today()
    week_from_now = today + timedelta(days=7)

    # User Settings and Exchange Rates
    settings = Settings.get_settings(user_id=current_user.id)
    primary_currency = settings.primary_currency or 'TRY'
    rates = CurrencyService.get_rates(user_id=current_user.id)

    # Active subscriptions for current user
    active_subs = Subscription.query.filter_by(user_id=current_user.id, is_active=True).all()

    # Calculate monthly total in primary currency
    monthly_total = 0.0
    for sub in active_subs:
        monthly_total += CurrencyService.convert_to_primary(
            sub.monthly_amount, sub.currency, rates=rates, primary_currency=primary_currency
        )

    # Upcoming due this week
    upcoming = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True,
        Subscription.next_due_date >= today,
        Subscription.next_due_date <= week_from_now
    ).order_by(Subscription.next_due_date).all()

    # Overdue subscriptions
    overdue = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True,
        Subscription.next_due_date < today
    ).order_by(Subscription.next_due_date).all()

    # Category breakdown (monthly)
    category_totals = {}
    for sub in active_subs:
        cat_name = sub.category.name if sub.category else 'Uncategorized'
        cat_color = sub.category.color if sub.category else '#6b7280'

        amount_converted = CurrencyService.convert_to_primary(
            sub.monthly_amount, sub.currency, rates=rates, primary_currency=primary_currency
        )

        if cat_name not in category_totals:
            category_totals[cat_name] = {'total': 0.0, 'color': cat_color}
        category_totals[cat_name]['total'] += amount_converted

    # Current year spending from payments
    current_year = today.year
    yearly_payments = Payment.query.filter(
        Payment.user_id == current_user.id,
        extract('year', Payment.paid_date) == current_year
    ).all()

    yearly_total = sum(
        CurrencyService.convert_to_primary(
            p.amount, p.currency, rates=rates, primary_currency=primary_currency
        )
        for p in yearly_payments
    )

    # All-time savings from discounts
    all_payments = Payment.query.filter_by(user_id=current_user.id).all()
    all_time_savings = 0.0
    all_time_savings_count = 0
    for p in all_payments:
        if p.discount > 0:
            all_time_savings += CurrencyService.convert_to_primary(
                p.discount, p.currency, rates=rates, primary_currency=primary_currency
            )
            all_time_savings_count += 1

    return render_template('dashboard.html',
        active_count=len(active_subs),
        monthly_total=monthly_total,
        yearly_total=yearly_total,
        all_time_savings=all_time_savings,
        all_time_savings_count=all_time_savings_count,
        upcoming=upcoming,
        overdue=overdue,
        category_totals=category_totals,
        primary_currency=primary_currency,
        rates=rates,
        current_year=current_year
    )
