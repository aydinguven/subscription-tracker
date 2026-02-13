from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import extract, func
from app import db
from app.models import Payment, Subscription, PaymentMethod
from app.services.currency import CurrencyService
from app.utils import parse_date

bp = Blueprint('payments', __name__)


@bp.route('/')
@login_required
def index():
    """List all payments with filters."""
    subscription_id = request.args.get('subscription', type=int)
    year = request.args.get('year', date.today().year, type=int)
    currency = request.args.get('currency', 'all')
    
    query = Payment.query.filter_by(user_id=current_user.id)
    
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)
    
    if year:
        query = query.filter(extract('year', Payment.paid_date) == year)
    
    if currency != 'all':
        query = query.filter_by(currency=currency)
    
    payments = query.order_by(Payment.paid_date.desc()).all()
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.name).all()
    rates = CurrencyService.get_rates()
    
    # Calculate totals by currency
    currency_totals = {}
    for payment in payments:
        if payment.currency not in currency_totals:
            currency_totals[payment.currency] = 0
        currency_totals[payment.currency] += payment.amount
    
    # Calculate grand total in TRY
    grand_total = sum(
        CurrencyService.convert_to_primary(amount, curr, rates)
        for curr, amount in currency_totals.items()
    )
    
    # Get available years for current user
    years_query = db.session.query(
        extract('year', Payment.paid_date).label('year')
    ).filter(
        Payment.user_id == current_user.id
    ).distinct().order_by(extract('year', Payment.paid_date).desc()).all()
    available_years = [int(y.year) for y in years_query if y.year]
    
    if not available_years:
        available_years = [date.today().year]
    
    return render_template('payments.html',
        payments=payments,
        subscriptions=subscriptions,
        rates=rates,
        currency_totals=currency_totals,
        grand_total=grand_total,
        filter_subscription=subscription_id,
        filter_year=year,
        filter_currency=currency,
        available_years=available_years
    )


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a manual payment."""
    if request.method == 'POST':
        subscription_id = request.form.get('subscription_id')
        payment_method_id = request.form.get('payment_method_id')
        amount = float(request.form.get('amount', 0))
        original_amount_str = request.form.get('original_amount')
        original_amount = float(original_amount_str) if original_amount_str else None
        currency = request.form.get('currency', 'TRY')
        paid_date = request.form.get('paid_date')
        notes = request.form.get('notes')
        
        payment = Payment(
            user_id=current_user.id,
            subscription_id=int(subscription_id) if subscription_id else None,
            payment_method_id=int(payment_method_id) if payment_method_id else None,
            amount=amount,
            original_amount=original_amount,
            currency=currency,
            paid_date=parse_date(paid_date) or date.today(),
            notes=notes
        )
        
        db.session.add(payment)
        
        # Advance subscription's due date
        if subscription_id:
            subscription = Subscription.query.filter_by(
                id=int(subscription_id), user_id=current_user.id
            ).first()
            if subscription:
                subscription.advance_due_date()
        
        db.session.commit()
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('payments.index'))
    
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    return render_template('payment_form.html',
        payment=None,
        subscriptions=subscriptions,
        payment_methods=payment_methods,
        action='Add'
    )


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a payment."""
    payment = Payment.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(payment)
    db.session.commit()
    flash('Payment deleted!', 'success')
    return redirect(url_for('payments.index'))


@bp.route('/yearly')
@login_required
def yearly_report():
    """Yearly payment summary."""
    from dateutil.relativedelta import relativedelta
    
    year = request.args.get('year', date.today().year, type=int)
    rates = CurrencyService.get_rates()
    current_year = date.today().year
    current_month = date.today().month
    
    payments = Payment.query.filter(
        Payment.user_id == current_user.id,
        extract('year', Payment.paid_date) == year
    ).all()
    
    # Monthly breakdown with billing cycle separation
    monthly_totals = {}
    for month in range(1, 13):
        monthly_totals[month] = {
            'TRY': 0, 'USD': 0, 'EUR': 0, 'total_try': 0,
            'monthly_try': 0,  # Monthly billing cycle payments
            'other_try': 0,    # Yearly, quarterly, etc. payments
            'predicted_monthly': 0,  # Predicted monthly payments
            'predicted_other': 0     # Predicted yearly/quarterly payments
        }
    
    for payment in payments:
        month = payment.paid_date.month
        monthly_totals[month][payment.currency] = monthly_totals[month].get(payment.currency, 0) + payment.amount
        amount_try = CurrencyService.convert_to_primary(
            payment.amount, payment.currency, rates
        )
        monthly_totals[month]['total_try'] += amount_try
        
        # Separate by billing cycle
        billing_cycle = payment.subscription.billing_cycle if payment.subscription else 'monthly'
        if billing_cycle == 'monthly':
            monthly_totals[month]['monthly_try'] += amount_try
        else:
            monthly_totals[month]['other_try'] += amount_try
    
    # Calculate predictions for future months (current year only)
    if year == current_year:
        active_subscriptions = Subscription.query.filter_by(
            user_id=current_user.id, is_active=True
        ).all()
        
        for sub in active_subscriptions:
            if not sub.next_due_date:
                continue
            
            amount_try = CurrencyService.convert_to_primary(sub.amount, sub.currency, rates)
            
            # Calculate all payment dates for remaining months of the year
            check_date = sub.next_due_date
            
            # Get the billing cycle interval
            if sub.billing_cycle == 'weekly':
                delta = relativedelta(weeks=1)
            elif sub.billing_cycle == 'monthly':
                delta = relativedelta(months=1)
            elif sub.billing_cycle == 'quarterly':
                delta = relativedelta(months=3)
            elif sub.billing_cycle == 'yearly':
                delta = relativedelta(years=1)
            else:
                delta = relativedelta(months=1)  # Default to monthly
            
            # Project payments through end of year
            while check_date.year == year:
                if check_date.month > current_month:
                    # This is a future payment - add to predictions
                    if sub.billing_cycle == 'monthly':
                        monthly_totals[check_date.month]['predicted_monthly'] += amount_try
                    else:
                        monthly_totals[check_date.month]['predicted_other'] += amount_try
                check_date = check_date + delta
    
    # Category breakdown
    category_totals = {}
    for payment in payments:
        if payment.subscription and payment.subscription.category:
            cat_name = payment.subscription.category.name
            cat_color = payment.subscription.category.color
        else:
            cat_name = 'Uncategorized'
            cat_color = '#6b7280'
        
        if cat_name not in category_totals:
            category_totals[cat_name] = {'total': 0, 'color': cat_color}
        
        category_totals[cat_name]['total'] += CurrencyService.convert_to_primary(
            payment.amount, payment.currency, rates
        )
    
    # Grand total
    grand_total = sum(m['total_try'] for m in monthly_totals.values())
    
    # Available years for current user
    years_query = db.session.query(
        extract('year', Payment.paid_date).label('year')
    ).filter(
        Payment.user_id == current_user.id
    ).distinct().order_by(extract('year', Payment.paid_date).desc()).all()
    available_years = [int(y.year) for y in years_query if y.year]
    
    if not available_years:
        available_years = [date.today().year]
    
    return render_template('yearly_report.html',
        year=year,
        monthly_totals=monthly_totals,
        category_totals=category_totals,
        grand_total=grand_total,
        available_years=available_years,
        rates=rates,
        current_month=current_month,
        is_current_year=(year == current_year)
    )
