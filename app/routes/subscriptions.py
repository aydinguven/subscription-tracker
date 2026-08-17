from calendar import monthrange
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Subscription, Category, Payment, PaymentMethod, Settings
from app.services.currency import CurrencyService
from app.utils import parse_date

bp = Blueprint('subscriptions', __name__)

BILLING_CYCLES = [
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
    ('weekly', 'Weekly'),
    ('bi-weekly', 'Bi-Weekly (Every 2 Weeks)'),
    ('quarterly', 'Quarterly (Every 3 Months)'),
    ('semi-annual', 'Semi-Annual (Every 6 Months)')
]


@bp.route('/')
@login_required
def index():
    """List all subscriptions with search, filter, and sorting."""
    category_id = request.args.get('category', type=int)
    payment_method_id = request.args.get('payment_method', type=int)
    status = request.args.get('status', 'active')
    currency = request.args.get('currency', 'all')
    billing_cycle = request.args.get('billing_cycle', 'all')
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'next_due_date')
    order = request.args.get('order', 'asc')

    query = Subscription.query.filter_by(user_id=current_user.id)

    # Search filter
    if search_query:
        query = query.filter(
            db.or_(
                Subscription.name.ilike(f'%{search_query}%'),
                Subscription.notes.ilike(f'%{search_query}%'),
                Subscription.tags.ilike(f'%{search_query}%')
            )
        )

    if category_id:
        query = query.filter_by(category_id=category_id)

    if payment_method_id:
        query = query.filter_by(payment_method_id=payment_method_id)

    if billing_cycle != 'all':
        query = query.filter_by(billing_cycle=billing_cycle)

    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    elif status == 'overdue':
        query = query.filter(
            Subscription.is_active == True,
            Subscription.next_due_date < date.today()
        )

    if currency != 'all':
        query = query.filter_by(currency=currency)

    # Sorting
    if sort_by == 'amount':
        sort_column = Subscription.amount
    elif sort_by == 'name':
        sort_column = Subscription.name
    elif sort_by == 'created_at':
        sort_column = Subscription.created_at
    else:
        sort_column = Subscription.next_due_date

    if order == 'desc':
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullslast())

    subscriptions = query.all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    settings = Settings.get_settings(user_id=current_user.id)
    rates = CurrencyService.get_rates(user_id=current_user.id)

    # Summary statistics for filtered subscriptions in user's primary currency
    filtered_monthly_total = sum(
        CurrencyService.convert_to_primary(
            s.monthly_amount, s.currency, rates=rates, primary_currency=settings.primary_currency
        )
        for s in subscriptions if s.is_active
    )

    return render_template('subscriptions.html',
        subscriptions=subscriptions,
        categories=categories,
        payment_methods=payment_methods,
        billing_cycles=BILLING_CYCLES,
        rates=rates,
        primary_currency=settings.primary_currency,
        filtered_monthly_total=filtered_monthly_total,
        filter_category=category_id,
        filter_payment_method=payment_method_id,
        filter_status=status,
        filter_currency=currency,
        filter_cycle=billing_cycle,
        search_query=search_query,
        sort_by=sort_by,
        order=order
    )


@bp.route('/calendar')
@login_required
def calendar_view():
    """Monthly calendar view of subscription renewals."""
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    # Validate year and month
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    first_day, num_days = monthrange(year, month)
    # first_day: Monday is 0 and Sunday is 6
    calendar_start_weekday = first_day

    # Group subscriptions due in this month
    active_subs = Subscription.query.filter_by(user_id=current_user.id, is_active=True).all()
    settings = Settings.get_settings(user_id=current_user.id)
    rates = CurrencyService.get_rates(user_id=current_user.id)

    day_events = {d: [] for d in range(1, num_days + 1)}

    for s in active_subs:
        if s.next_due_date and s.next_due_date.year == year and s.next_due_date.month == month:
            day_events[s.next_due_date.day].append(s)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    current_month_name = date(year, month, 1).strftime('%B %Y')

    return render_template('calendar.html',
        year=year,
        month=month,
        num_days=num_days,
        calendar_start_weekday=calendar_start_weekday,
        day_events=day_events,
        current_month_name=current_month_name,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        today=today,
        primary_currency=settings.primary_currency,
        rates=rates
    )


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new subscription with IDOR validation."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id_raw = request.form.get('category_id')
        payment_method_id_raw = request.form.get('payment_method_id')
        amount_raw = request.form.get('amount', '0')
        currency = request.form.get('currency', 'TRY').upper()
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        next_due_date_raw = request.form.get('next_due_date')
        url = request.form.get('url', '').strip()
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        notes = request.form.get('notes', '').strip()
        tags = request.form.get('tags', '').strip()
        icon = request.form.get('icon', 'receipt').strip()
        is_variable = request.form.get('is_variable') == 'on'

        if not name:
            flash('Subscription name is required', 'error')
            return redirect(url_for('subscriptions.add'))

        try:
            amount = float(amount_raw)
        except ValueError:
            amount = 0.0

        # Validate category belongs to user (IDOR prevention)
        category_id = None
        if category_id_raw:
            cat = Category.query.filter_by(id=int(category_id_raw), user_id=current_user.id).first()
            if cat:
                category_id = cat.id

        # Validate payment method belongs to user (IDOR prevention)
        payment_method_id = None
        if payment_method_id_raw:
            pm = PaymentMethod.query.filter_by(id=int(payment_method_id_raw), user_id=current_user.id).first()
            if pm:
                payment_method_id = pm.id

        subscription = Subscription(
            user_id=current_user.id,
            name=name,
            category_id=category_id,
            payment_method_id=payment_method_id,
            amount=amount,
            currency=currency,
            billing_cycle=billing_cycle,
            next_due_date=parse_date(next_due_date_raw),
            url=url or None,
            notes=notes or None,
            tags=tags or None,
            icon=icon or 'receipt',
            is_variable=is_variable,
            is_active=True
        )

        db.session.add(subscription)
        db.session.commit()
        flash(f'Subscription "{name}" added successfully!', 'success')
        return redirect(url_for('subscriptions.index'))

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    settings = Settings.get_settings(user_id=current_user.id)

    return render_template('subscription_form.html',
        subscription=None,
        categories=categories,
        payment_methods=payment_methods,
        billing_cycles=BILLING_CYCLES,
        primary_currency=settings.primary_currency,
        action='Add'
    )


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing subscription with IDOR validation."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        subscription.name = request.form.get('name', '').strip()
        amount_raw = request.form.get('amount', '0')
        try:
            subscription.amount = float(amount_raw)
        except ValueError:
            pass

        subscription.currency = request.form.get('currency', 'TRY').upper()
        subscription.billing_cycle = request.form.get('billing_cycle', 'monthly')
        subscription.next_due_date = parse_date(request.form.get('next_due_date'))

        url = request.form.get('url', '').strip()
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        subscription.url = url or None
        subscription.notes = request.form.get('notes', '').strip() or None
        subscription.tags = request.form.get('tags', '').strip() or None
        subscription.icon = request.form.get('icon', 'receipt').strip()
        subscription.is_variable = request.form.get('is_variable') == 'on'
        subscription.is_active = request.form.get('is_active') == 'on'

        # Validate category ownership
        category_id_raw = request.form.get('category_id')
        if category_id_raw:
            cat = Category.query.filter_by(id=int(category_id_raw), user_id=current_user.id).first()
            subscription.category_id = cat.id if cat else None
        else:
            subscription.category_id = None

        # Validate payment method ownership
        pm_id_raw = request.form.get('payment_method_id')
        if pm_id_raw:
            pm = PaymentMethod.query.filter_by(id=int(pm_id_raw), user_id=current_user.id).first()
            subscription.payment_method_id = pm.id if pm else None
        else:
            subscription.payment_method_id = None

        db.session.commit()
        flash(f'Subscription "{subscription.name}" updated!', 'success')
        return redirect(url_for('subscriptions.index'))

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    settings = Settings.get_settings(user_id=current_user.id)

    return render_template('subscription_form.html',
        subscription=subscription,
        categories=categories,
        payment_methods=payment_methods,
        billing_cycles=BILLING_CYCLES,
        primary_currency=settings.primary_currency,
        action='Edit'
    )


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a subscription."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = subscription.name
    db.session.delete(subscription)
    db.session.commit()
    flash(f'Subscription "{name}" deleted!', 'success')
    return redirect(url_for('subscriptions.index'))


@bp.route('/pay/<int:id>', methods=['POST'])
@login_required
def mark_paid(id):
    """Mark subscription as paid with support for custom paid and original amounts."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    amount_raw = request.form.get('amount')
    original_amount_raw = request.form.get('original_amount')
    paid_date_raw = request.form.get('paid_date')
    notes = request.form.get('notes')

    paid_amount = float(amount_raw) if amount_raw else subscription.amount
    original_amount = float(original_amount_raw) if original_amount_raw else None
    paid_date = parse_date(paid_date_raw) if paid_date_raw else (subscription.next_due_date or date.today())

    payment = Payment(
        user_id=current_user.id,
        subscription_id=subscription.id,
        payment_method_id=subscription.payment_method_id,
        amount=paid_amount,
        original_amount=original_amount,
        currency=subscription.currency,
        paid_date=paid_date,
        notes=notes or f'Payment for {subscription.name}'
    )
    db.session.add(payment)

    # Advance subscription due date
    subscription.advance_due_date()
    db.session.commit()

    flash(f'Payment recorded for "{subscription.name}"!', 'success')
    return redirect(request.referrer or url_for('subscriptions.index'))


@bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_active(id):
    """Toggle subscription active status."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    subscription.is_active = not subscription.is_active
    db.session.commit()

    status = 'activated' if subscription.is_active else 'deactivated'
    flash(f'Subscription "{subscription.name}" {status}!', 'success')
    return redirect(request.referrer or url_for('subscriptions.index'))
