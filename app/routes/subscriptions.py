from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from app import db
from app.models import Subscription, Category, Payment, PaymentMethod
from app.services.currency import CurrencyService

bp = Blueprint('subscriptions', __name__)


@bp.route('/')
def index():
    """List all subscriptions."""
    # Get filter parameters
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', 'all')
    currency = request.args.get('currency', 'all')
    
    query = Subscription.query
    
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
    categories = Category.query.order_by(Category.name).all()
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
        notes = request.form.get('notes')
        icon = request.form.get('icon', 'receipt')
        is_variable = request.form.get('is_variable') == 'on'
        
        subscription = Subscription(
            name=name,
            category_id=int(category_id) if category_id else None,
            payment_method_id=int(payment_method_id) if payment_method_id else None,
            amount=amount,
            currency=currency,
            billing_cycle=billing_cycle,
            next_due_date=date.fromisoformat(next_due_date) if next_due_date else None,
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
    
    categories = Category.query.order_by(Category.name).all()
    payment_methods = PaymentMethod.query.order_by(PaymentMethod.name).all()
    return render_template('subscription_form.html',
        subscription=None,
        categories=categories,
        payment_methods=payment_methods,
        action='Add'
    )


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Edit an existing subscription."""
    subscription = Subscription.query.get_or_404(id)
    
    if request.method == 'POST':
        subscription.name = request.form.get('name')
        subscription.category_id = request.form.get('category_id') or None
        subscription.payment_method_id = request.form.get('payment_method_id') or None
        subscription.amount = float(request.form.get('amount', 0))
        subscription.currency = request.form.get('currency', 'TRY')
        subscription.billing_cycle = request.form.get('billing_cycle', 'monthly')
        next_due_date = request.form.get('next_due_date')
        subscription.next_due_date = date.fromisoformat(next_due_date) if next_due_date else None
        subscription.url = request.form.get('url')
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
    
    categories = Category.query.order_by(Category.name).all()
    payment_methods = PaymentMethod.query.order_by(PaymentMethod.name).all()
    return render_template('subscription_form.html',
        subscription=subscription,
        categories=categories,
        payment_methods=payment_methods,
        action='Edit'
    )


@bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Delete a subscription."""
    subscription = Subscription.query.get_or_404(id)
    name = subscription.name
    db.session.delete(subscription)
    db.session.commit()
    flash(f'Subscription "{name}" deleted!', 'success')
    return redirect(url_for('subscriptions.index'))


@bp.route('/pay/<int:id>', methods=['POST'])
def mark_paid(id):
    """Mark a subscription as paid and advance due date."""
    subscription = Subscription.query.get_or_404(id)
    
    # Create payment record
    payment = Payment(
        subscription_id=subscription.id,
        payment_method_id=subscription.payment_method_id,
        amount=subscription.amount,
        currency=subscription.currency,
        paid_date=date.today(),
        notes=f'Automatic payment for {subscription.name}'
    )
    db.session.add(payment)
    
    # Advance due date
    subscription.advance_due_date()
    db.session.commit()
    
    flash(f'Payment recorded for "{subscription.name}"!', 'success')
    return redirect(url_for('subscriptions.index'))


@bp.route('/toggle/<int:id>', methods=['POST'])
def toggle_active(id):
    """Toggle subscription active status."""
    subscription = Subscription.query.get_or_404(id)
    subscription.is_active = not subscription.is_active
    db.session.commit()
    
    status = 'activated' if subscription.is_active else 'deactivated'
    flash(f'Subscription "{subscription.name}" {status}!', 'success')
    return redirect(url_for('subscriptions.index'))
