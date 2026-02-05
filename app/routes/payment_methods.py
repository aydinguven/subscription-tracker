from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import PaymentMethod

bp = Blueprint('payment_methods', __name__)

# Method type options
METHOD_TYPES = [
    ('bank', 'Bank Account', 'landmark'),
    ('credit_card', 'Credit Card', 'credit-card'),
    ('debit_card', 'Debit Card', 'credit-card'),
    ('mobile', 'Mobile Payment', 'smartphone'),
    ('wallet', 'Digital Wallet', 'wallet'),
    ('other', 'Other', 'banknote'),
]


@bp.route('/')
def index():
    """List all payment methods."""
    methods = PaymentMethod.query.order_by(PaymentMethod.name).all()
    return render_template('payment_methods.html', 
        methods=methods,
        method_types=METHOD_TYPES
    )


@bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new payment method."""
    if request.method == 'POST':
        name = request.form.get('name')
        method_type = request.form.get('method_type', 'bank')
        identifier = request.form.get('identifier')
        color = request.form.get('color', '#6b7280')
        icon = request.form.get('icon', 'credit-card')
        is_default = request.form.get('is_default') == 'on'
        
        # If setting as default, unset other defaults
        if is_default:
            PaymentMethod.query.update({PaymentMethod.is_default: False})
        
        method = PaymentMethod(
            name=name,
            method_type=method_type,
            identifier=identifier,
            color=color,
            icon=icon,
            is_default=is_default
        )
        db.session.add(method)
        db.session.commit()
        flash(f'Payment method "{name}" added!', 'success')
        return redirect(url_for('payment_methods.index'))
    
    return render_template('payment_method_form.html',
        method=None,
        method_types=METHOD_TYPES,
        action='Add'
    )


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Edit a payment method."""
    method = PaymentMethod.query.get_or_404(id)
    
    if request.method == 'POST':
        method.name = request.form.get('name')
        method.method_type = request.form.get('method_type', 'bank')
        method.identifier = request.form.get('identifier')
        method.color = request.form.get('color', '#6b7280')
        method.icon = request.form.get('icon', 'credit-card')
        is_default = request.form.get('is_default') == 'on'
        
        # If setting as default, unset other defaults
        if is_default and not method.is_default:
            PaymentMethod.query.filter(PaymentMethod.id != id).update({PaymentMethod.is_default: False})
        method.is_default = is_default
        
        db.session.commit()
        flash(f'Payment method "{method.name}" updated!', 'success')
        return redirect(url_for('payment_methods.index'))
    
    return render_template('payment_method_form.html',
        method=method,
        method_types=METHOD_TYPES,
        action='Edit'
    )


@bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Delete a payment method."""
    method = PaymentMethod.query.get_or_404(id)
    name = method.name
    
    # Unlink subscriptions and payments from this method
    for sub in method.subscriptions:
        sub.payment_method_id = None
    for payment in method.payments:
        payment.payment_method_id = None
    
    db.session.delete(method)
    db.session.commit()
    flash(f'Payment method "{name}" deleted!', 'success')
    return redirect(url_for('payment_methods.index'))


@bp.route('/set-default/<int:id>', methods=['POST'])
def set_default(id):
    """Set a payment method as default."""
    method = PaymentMethod.query.get_or_404(id)
    
    # Unset all defaults
    PaymentMethod.query.update({PaymentMethod.is_default: False})
    
    # Set this one as default
    method.is_default = True
    db.session.commit()
    
    flash(f'"{method.name}" is now your default payment method!', 'success')
    return redirect(url_for('payment_methods.index'))
