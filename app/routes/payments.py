from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import extract
from dateutil.relativedelta import relativedelta
from app import db
from app.models import Payment, Subscription, PaymentMethod, Settings
from app.services.currency import CurrencyService
from app.utils import parse_date

bp = Blueprint('payments', __name__)


@bp.route('/')
@login_required
def index():
    """List all payments with filters and primary currency summaries."""
    subscription_id = request.args.get('subscription', type=int)
    year = request.args.get('year', date.today().year, type=int)
    currency = request.args.get('currency', 'all')
    search_query = request.args.get('q', '').strip()

    query = Payment.query.filter_by(user_id=current_user.id)

    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    if year:
        query = query.filter(extract('year', Payment.paid_date) == year)

    if currency != 'all':
        query = query.filter_by(currency=currency)

    if search_query:
        query = query.join(Subscription).filter(
            db.or_(
                Subscription.name.ilike(f'%{search_query}%'),
                Payment.notes.ilike(f'%{search_query}%')
            )
        )

    payments = query.order_by(Payment.paid_date.desc()).all()
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.name).all()
    settings = Settings.get_settings(user_id=current_user.id)
    rates = CurrencyService.get_rates(user_id=current_user.id)

    # Calculate totals by currency
    currency_totals = {}
    total_savings = 0.0
    for payment in payments:
        if payment.currency not in currency_totals:
            currency_totals[payment.currency] = 0.0
        currency_totals[payment.currency] += payment.amount

        if payment.discount > 0:
            total_savings += CurrencyService.convert_to_primary(
                payment.discount, payment.currency, rates=rates, primary_currency=settings.primary_currency
            )

    # Grand total converted to user's primary currency
    grand_total = sum(
        CurrencyService.convert_to_primary(
            amount, curr, rates=rates, primary_currency=settings.primary_currency
        )
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
        primary_currency=settings.primary_currency,
        currency_totals=currency_totals,
        grand_total=grand_total,
        total_savings=total_savings,
        filter_subscription=subscription_id,
        filter_year=year,
        filter_currency=currency,
        search_query=search_query,
        available_years=available_years
    )


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a manual payment with IDOR validation."""
    if request.method == 'POST':
        subscription_id_raw = request.form.get('subscription_id')
        payment_method_id_raw = request.form.get('payment_method_id')
        amount_raw = request.form.get('amount', '0')
        original_amount_raw = request.form.get('original_amount')
        currency = request.form.get('currency', 'TRY').upper()
        paid_date_raw = request.form.get('paid_date')
        notes = request.form.get('notes', '').strip()
        advance_date = request.form.get('advance_date') == 'on'

        # Verify subscription belongs to user (IDOR prevention)
        subscription = None
        if subscription_id_raw:
            subscription = Subscription.query.filter_by(
                id=int(subscription_id_raw), user_id=current_user.id
            ).first()

        if not subscription:
            flash('Valid subscription is required', 'error')
            return redirect(url_for('payments.add'))

        # Verify payment method belongs to user
        payment_method_id = None
        if payment_method_id_raw:
            pm = PaymentMethod.query.filter_by(
                id=int(payment_method_id_raw), user_id=current_user.id
            ).first()
            if pm:
                payment_method_id = pm.id

        try:
            amount = float(amount_raw)
        except ValueError:
            amount = 0.0

        original_amount = float(original_amount_raw) if original_amount_raw else None
        paid_date = parse_date(paid_date_raw) or date.today()

        payment = Payment(
            user_id=current_user.id,
            subscription_id=subscription.id,
            payment_method_id=payment_method_id or subscription.payment_method_id,
            amount=amount,
            original_amount=original_amount,
            currency=currency,
            paid_date=paid_date,
            notes=notes or None
        )
        db.session.add(payment)

        if advance_date:
            subscription.advance_due_date()

        db.session.commit()
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('payments.index'))

    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    settings = Settings.get_settings(user_id=current_user.id)

    return render_template('payment_form.html',
        payment=None,
        subscriptions=subscriptions,
        payment_methods=payment_methods,
        primary_currency=settings.primary_currency,
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
    """Yearly payment analytics dynamic to primary currency."""
    year = request.args.get('year', date.today().year, type=int)
    settings = Settings.get_settings(user_id=current_user.id)
    rates = CurrencyService.get_rates(user_id=current_user.id)
    current_year = date.today().year
    current_month = date.today().month

    payments = Payment.query.filter(
        Payment.user_id == current_user.id,
        extract('year', Payment.paid_date) == year
    ).all()

    # Monthly breakdown
    monthly_totals = {}
    for month in range(1, 13):
        monthly_totals[month] = {
            'total_primary': 0.0,
            'monthly_primary': 0.0,
            'other_primary': 0.0,
            'predicted_monthly': 0.0,
            'predicted_other': 0.0,
            'currencies': {}
        }

    for payment in payments:
        month = payment.paid_date.month
        curr = payment.currency
        monthly_totals[month]['currencies'][curr] = monthly_totals[month]['currencies'].get(curr, 0.0) + payment.amount

        amount_primary = CurrencyService.convert_to_primary(
            payment.amount, payment.currency, rates=rates, primary_currency=settings.primary_currency
        )
        monthly_totals[month]['total_primary'] += amount_primary

        billing_cycle = payment.subscription.billing_cycle if payment.subscription else 'monthly'
        if billing_cycle == 'monthly':
            monthly_totals[month]['monthly_primary'] += amount_primary
        else:
            monthly_totals[month]['other_primary'] += amount_primary

    # Predictions for current year
    if year == current_year:
        active_subscriptions = Subscription.query.filter_by(
            user_id=current_user.id, is_active=True
        ).all()

        for sub in active_subscriptions:
            if not sub.next_due_date:
                continue

            amount_primary = CurrencyService.convert_to_primary(
                sub.amount, sub.currency, rates=rates, primary_currency=settings.primary_currency
            )

            # Cycle interval
            if sub.billing_cycle == 'weekly':
                delta = relativedelta(weeks=1)
            elif sub.billing_cycle == 'bi-weekly':
                delta = relativedelta(weeks=2)
            elif sub.billing_cycle == 'monthly':
                delta = relativedelta(months=1)
            elif sub.billing_cycle == 'quarterly':
                delta = relativedelta(months=3)
            elif sub.billing_cycle == 'semi-annual':
                delta = relativedelta(months=6)
            elif sub.billing_cycle == 'yearly':
                delta = relativedelta(years=1)
            else:
                delta = relativedelta(months=1)

            check_date = sub.next_due_date
            while check_date.year == year:
                if check_date.month > current_month:
                    if sub.billing_cycle == 'monthly':
                        monthly_totals[check_date.month]['predicted_monthly'] += amount_primary
                    else:
                        monthly_totals[check_date.month]['predicted_other'] += amount_primary
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
            category_totals[cat_name] = {'total': 0.0, 'color': cat_color}

        category_totals[cat_name]['total'] += CurrencyService.convert_to_primary(
            payment.amount, payment.currency, rates=rates, primary_currency=settings.primary_currency
        )

    grand_total = sum(m['total_primary'] for m in monthly_totals.values())

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
        primary_currency=settings.primary_currency,
        current_month=current_month,
        is_current_year=(year == current_year)
    )
