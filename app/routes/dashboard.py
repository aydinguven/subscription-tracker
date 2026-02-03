from flask import Blueprint, render_template
from datetime import date, timedelta
from sqlalchemy import func, extract
from app.models import Subscription, Payment, Category
from app.services.currency import CurrencyService

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    """Main dashboard view."""
    today = date.today()
    week_from_now = today + timedelta(days=7)
    
    # Get active subscriptions
    active_subs = Subscription.query.filter_by(is_active=True).all()
    
    # Get exchange rates
    rates = CurrencyService.get_rates()
    
    # Calculate monthly total in TRY
    monthly_total = 0
    for sub in active_subs:
        monthly_amount = sub.amount
        if sub.billing_cycle == 'yearly':
            monthly_amount = sub.amount / 12
        elif sub.billing_cycle == 'weekly':
            monthly_amount = sub.amount * 4.33
        
        monthly_total += CurrencyService.convert_to_primary(monthly_amount, sub.currency, rates)
    
    # Upcoming due this week
    upcoming = Subscription.query.filter(
        Subscription.is_active == True,
        Subscription.next_due_date >= today,
        Subscription.next_due_date <= week_from_now
    ).order_by(Subscription.next_due_date).all()
    
    # Overdue subscriptions
    overdue = Subscription.query.filter(
        Subscription.is_active == True,
        Subscription.next_due_date < today
    ).order_by(Subscription.next_due_date).all()
    
    # Category breakdown
    category_totals = {}
    for sub in active_subs:
        cat_name = sub.category.name if sub.category else 'Uncategorized'
        cat_color = sub.category.color if sub.category else '#6b7280'
        
        monthly_amount = sub.amount
        if sub.billing_cycle == 'yearly':
            monthly_amount = sub.amount / 12
        elif sub.billing_cycle == 'weekly':
            monthly_amount = sub.amount * 4.33
        
        amount_try = CurrencyService.convert_to_primary(monthly_amount, sub.currency, rates)
        
        if cat_name not in category_totals:
            category_totals[cat_name] = {'total': 0, 'color': cat_color}
        category_totals[cat_name]['total'] += amount_try
    
    # Get yearly total from payments
    current_year = today.year
    yearly_payments = Payment.query.filter(
        extract('year', Payment.paid_date) == current_year
    ).all()
    
    yearly_total = sum(
        CurrencyService.convert_to_primary(p.amount, p.currency, rates)
        for p in yearly_payments
    )
    
    # Calculate total savings from discounts
    total_savings = 0
    savings_count = 0
    for p in yearly_payments:
        if p.original_amount and p.original_amount > p.amount:
            savings = p.original_amount - p.amount
            total_savings += CurrencyService.convert_to_primary(savings, p.currency, rates)
            savings_count += 1
    
    # All-time savings
    all_payments = Payment.query.all()
    all_time_savings = 0
    all_time_savings_count = 0
    for p in all_payments:
        if p.original_amount and p.original_amount > p.amount:
            savings = p.original_amount - p.amount
            all_time_savings += CurrencyService.convert_to_primary(savings, p.currency, rates)
            all_time_savings_count += 1
    
    return render_template('dashboard.html',
        active_count=len(active_subs),
        monthly_total=monthly_total,
        yearly_total=yearly_total,
        yearly_savings=total_savings,
        yearly_savings_count=savings_count,
        all_time_savings=all_time_savings,
        all_time_savings_count=all_time_savings_count,
        upcoming=upcoming,
        overdue=overdue,
        category_totals=category_totals,
        rates=rates,
        current_year=current_year
    )
