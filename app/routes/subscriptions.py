from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.models import Subscription, Category, Payment, PaymentMethod
from app.services.currency import CurrencyService
from app.utils import parse_date

bp = Blueprint('subscriptions', __name__)


@bp.route('/')
@login_required
def index():
    """List all subscriptions."""
    # Get filter parameters
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', 'active')
    currency = request.args.get('currency', 'all')
    
    query = Subscription.query.filter_by(user_id=current_user.id)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
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
    
    subscriptions = query.order_by(Subscription.next_due_date.asc().nullslast()).all()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    rates = CurrencyService.get_rates()
    
    return render_template('subscriptions.html',
        subscriptions=subscriptions,
        categories=categories,
        rates=rates,
        filter_category=category_id,
        filter_status=status,
        filter_currency=currency
    )


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new subscription."""
    if request.method == 'POST':
        name = request.form.get('name')
        category_id = request.form.get('category_id') or None
        payment_method_id = request.form.get('payment_method_id') or None
        amount = float(request.form.get('amount', 0))
        currency = request.form.get('currency', 'TRY')
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        next_due_date = request.form.get('next_due_date')
        url = request.form.get('url')
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        notes = request.form.get('notes')
        icon = request.form.get('icon', 'receipt')
        is_variable = request.form.get('is_variable') == 'on'
        
        subscription = Subscription(
            user_id=current_user.id,
            name=name,
            category_id=int(category_id) if category_id else None,
            payment_method_id=int(payment_method_id) if payment_method_id else None,
            amount=amount,
            currency=currency,
            billing_cycle=billing_cycle,
            next_due_date=parse_date(next_due_date),
            url=url,
            notes=notes,
            icon=icon,
            is_variable=is_variable,
            is_active=True
        )
        
        db.session.add(subscription)
        db.session.commit()
        flash(f'Subscription "{name}" added successfully!', 'success')
        return redirect(url_for('subscriptions.index'))
    
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    return render_template('subscription_form.html',
        subscription=None,
        categories=categories,
        payment_methods=payment_methods,
        action='Add'
    )


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing subscription."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        subscription.name = request.form.get('name')
        subscription.category_id = request.form.get('category_id') or None
        subscription.payment_method_id = request.form.get('payment_method_id') or None
        subscription.amount = float(request.form.get('amount', 0))
        subscription.currency = request.form.get('currency', 'TRY')
        subscription.billing_cycle = request.form.get('billing_cycle', 'monthly')
        next_due_date = request.form.get('next_due_date')
        subscription.next_due_date = parse_date(next_due_date)
        url = request.form.get('url')
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        subscription.url = url
        subscription.notes = request.form.get('notes')
        subscription.icon = request.form.get('icon', 'receipt')
        subscription.is_variable = request.form.get('is_variable') == 'on'
        subscription.is_active = request.form.get('is_active') == 'on'
        
        if subscription.category_id:
            subscription.category_id = int(subscription.category_id)
        if subscription.payment_method_id:
            subscription.payment_method_id = int(subscription.payment_method_id)
        
        db.session.commit()
        flash(f'Subscription "{subscription.name}" updated!', 'success')
        return redirect(url_for('subscriptions.index'))
    
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    return render_template('subscription_form.html',
        subscription=subscription,
        categories=categories,
        payment_methods=payment_methods,
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
    """Mark a subscription as paid and advance due date."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        subscription_id=subscription.id,
        payment_method_id=subscription.payment_method_id,
        amount=subscription.amount,
        currency=subscription.currency,
        paid_date=subscription.next_due_date or date.today(),
        notes=f'Automatic payment for {subscription.name}'
    )
    db.session.add(payment)
    
    # Advance due date
    subscription.advance_due_date()
    db.session.commit()
    
    flash(f'Payment recorded for "{subscription.name}"!', 'success')
    return redirect(url_for('subscriptions.index'))


@bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_active(id):
    """Toggle subscription active status."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    subscription.is_active = not subscription.is_active
    db.session.commit()
    
    status = 'activated' if subscription.is_active else 'deactivated'
    flash(f'Subscription "{subscription.name}" {status}!', 'success')
    return redirect(url_for('subscriptions.index'))
