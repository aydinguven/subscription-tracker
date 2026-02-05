from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date, datetime
from sqlalchemy import extract, func
from app import db
from app.models import Payment, Subscription, PaymentMethod
from app.services.currency import CurrencyService

bp = Blueprint('payments', __name__)


def parse_date(date_string):
    """Parse date string from various formats."""
    if not date_string:
        return None
    
    date_string = date_string.strip()
    
    try:
        return date.fromisoformat(date_string)
    except ValueError:
        pass
    
    formats = [
        '%d %b %y', '%d %b %Y', '%d/%m/%Y', '%d/%m/%y',
        '%d-%m-%Y', '%d-%m-%y', '%m/%d/%Y', '%m/%d/%y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse date: '{date_string}'")


@bp.route('/')
def index():
    """List all payments with filters."""
    subscription_id = request.args.get('subscription', type=int)
    year = request.args.get('year', date.today().year, type=int)
    currency = request.args.get('currency', 'all')
    
    query = Payment.query
    
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)
    
    if year:
        query = query.filter(extract('year', Payment.paid_date) == year)
    
    if currency != 'all':
        query = query.filter_by(currency=currency)
    
    payments = query.order_by(Payment.paid_date.desc()).all()
    subscriptions = Subscription.query.order_by(Subscription.name).all()
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
    
    # Get available years
    years_query = db.session.query(
        extract('year', Payment.paid_date).label('year')
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
            subscription_id=int(subscription_id) if subscription_id else None,
            payment_method_id=int(payment_method_id) if payment_method_id else None,
            amount=amount,
            original_amount=original_amount,
            currency=currency,
            paid_date=parse_date(paid_date) or date.today(),
            notes=notes
        )
        
        db.session.add(payment)
        db.session.commit()
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('payments.index'))
    
    subscriptions = Subscription.query.order_by(Subscription.name).all()
    payment_methods = PaymentMethod.query.order_by(PaymentMethod.name).all()
    return render_template('payment_form.html',
        payment=None,
        subscriptions=subscriptions,
        payment_methods=payment_methods,
        action='Add'
    )


@bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Delete a payment."""
    payment = Payment.query.get_or_404(id)
    db.session.delete(payment)
    db.session.commit()
    flash('Payment deleted!', 'success')
    return redirect(url_for('payments.index'))


@bp.route('/yearly')
def yearly_report():
    """Yearly payment summary."""
    year = request.args.get('year', date.today().year, type=int)
    rates = CurrencyService.get_rates()
    
    payments = Payment.query.filter(
        extract('year', Payment.paid_date) == year
    ).all()
    
    # Monthly breakdown
    monthly_totals = {}
    for month in range(1, 13):
        monthly_totals[month] = {'TRY': 0, 'USD': 0, 'EUR': 0, 'total_try': 0}
    
    for payment in payments:
        month = payment.paid_date.month
        monthly_totals[month][payment.currency] = monthly_totals[month].get(payment.currency, 0) + payment.amount
        monthly_totals[month]['total_try'] += CurrencyService.convert_to_primary(
            payment.amount, payment.currency, rates
        )
    
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
    
    # Available years
    years_query = db.session.query(
        extract('year', Payment.paid_date).label('year')
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
        rates=rates
    )
