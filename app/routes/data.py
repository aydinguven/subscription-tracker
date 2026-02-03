from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from datetime import date, datetime
import json
from app import db
from app.models import Subscription, Payment, Category, PaymentMethod

bp = Blueprint('data', __name__)


@bp.route('/export', methods=['GET', 'POST'])
def export_data():
    """Export data to JSON file."""
    if request.method == 'POST':
        # Get selected items to export
        export_categories = request.form.get('categories') == 'on'
        export_payment_methods = request.form.get('payment_methods') == 'on'
        export_subscriptions = request.form.get('subscriptions') == 'on'
        export_payments = request.form.get('payments') == 'on'
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
        
        if export_categories:
            data['categories'] = [
                {
                    'name': c.name,
                    'color': c.color,
                    'icon': c.icon
                }
                for c in Category.query.all()
            ]
        
        if export_payment_methods:
            data['payment_methods'] = [
                {
                    'name': m.name,
                    'method_type': m.method_type,
                    'identifier': m.identifier,
                    'color': m.color,
                    'icon': m.icon,
                    'is_default': m.is_default
                }
                for m in PaymentMethod.query.all()
            ]
        
        if export_subscriptions:
            data['subscriptions'] = [
                {
                    'name': s.name,
                    'category_name': s.category.name if s.category else None,
                    'payment_method_name': s.payment_method.name if s.payment_method else None,
                    'amount': s.amount,
                    'currency': s.currency,
                    'billing_cycle': s.billing_cycle,
                    'next_due_date': s.next_due_date.isoformat() if s.next_due_date else None,
                    'url': s.url,
                    'notes': s.notes,
                    'icon': s.icon,
                    'is_active': s.is_active,
                    'is_variable': s.is_variable
                }
                for s in Subscription.query.all()
            ]
        
        if export_payments:
            data['payments'] = [
                {
                    'subscription_name': p.subscription.name if p.subscription else None,
                    'payment_method_name': p.payment_method.name if p.payment_method else None,
                    'amount': p.amount,
                    'original_amount': p.original_amount,
                    'currency': p.currency,
                    'paid_date': p.paid_date.isoformat() if p.paid_date else None,
                    'notes': p.notes
                }
                for p in Payment.query.all()
            ]
        
        # Return as downloadable JSON file
        json_str = json.dumps(data, indent=2)
        filename = f"subscription_tracker_export_{date.today().isoformat()}.json"
        
        return Response(
            json_str,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    
    # GET - show export form
    stats = {
        'categories': Category.query.count(),
        'payment_methods': PaymentMethod.query.count(),
        'subscriptions': Subscription.query.count(),
        'payments': Payment.query.count()
    }
    return render_template('export.html', stats=stats)


@bp.route('/import', methods=['GET', 'POST'])
def import_data():
    """Import data from JSON file."""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file selected', 'error')
            return redirect(url_for('data.import_data'))
        
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            flash('Invalid JSON file', 'error')
            return redirect(url_for('data.import_data'))
        
        # Get import options
        import_categories = request.form.get('categories') == 'on'
        import_payment_methods = request.form.get('payment_methods') == 'on'
        import_subscriptions = request.form.get('subscriptions') == 'on'
        import_payments = request.form.get('payments') == 'on'
        skip_existing = request.form.get('skip_existing') == 'on'
        
        imported = {'categories': 0, 'payment_methods': 0, 'subscriptions': 0, 'payments': 0}
        
        # Import categories first (needed for subscriptions)
        if import_categories and 'categories' in data:
            for cat_data in data['categories']:
                existing = Category.query.filter_by(name=cat_data['name']).first()
                if existing:
                    if skip_existing:
                        continue
                    # Update existing
                    existing.color = cat_data.get('color', existing.color)
                    existing.icon = cat_data.get('icon', existing.icon)
                else:
                    cat = Category(
                        name=cat_data['name'],
                        color=cat_data.get('color', '#6b7280'),
                        icon=cat_data.get('icon', 'folder')
                    )
                    db.session.add(cat)
                imported['categories'] += 1
            db.session.commit()
        
        # Import payment methods
        if import_payment_methods and 'payment_methods' in data:
            for pm_data in data['payment_methods']:
                existing = PaymentMethod.query.filter_by(name=pm_data['name']).first()
                if existing:
                    if skip_existing:
                        continue
                    existing.method_type = pm_data.get('method_type', existing.method_type)
                    existing.identifier = pm_data.get('identifier', existing.identifier)
                    existing.color = pm_data.get('color', existing.color)
                    existing.icon = pm_data.get('icon', existing.icon)
                else:
                    pm = PaymentMethod(
                        name=pm_data['name'],
                        method_type=pm_data.get('method_type', 'other'),
                        identifier=pm_data.get('identifier'),
                        color=pm_data.get('color', '#6b7280'),
                        icon=pm_data.get('icon', 'credit-card'),
                        is_default=pm_data.get('is_default', False)
                    )
                    db.session.add(pm)
                imported['payment_methods'] += 1
            db.session.commit()
        
        # Import subscriptions
        if import_subscriptions and 'subscriptions' in data:
            for sub_data in data['subscriptions']:
                existing = Subscription.query.filter_by(name=sub_data['name']).first()
                if existing and skip_existing:
                    continue
                
                # Find category and payment method by name
                category = None
                if sub_data.get('category_name'):
                    category = Category.query.filter_by(name=sub_data['category_name']).first()
                
                payment_method = None
                if sub_data.get('payment_method_name'):
                    payment_method = PaymentMethod.query.filter_by(name=sub_data['payment_method_name']).first()
                
                if existing:
                    existing.category_id = category.id if category else None
                    existing.payment_method_id = payment_method.id if payment_method else None
                    existing.amount = sub_data.get('amount', existing.amount)
                    existing.currency = sub_data.get('currency', existing.currency)
                    existing.billing_cycle = sub_data.get('billing_cycle', existing.billing_cycle)
                    if sub_data.get('next_due_date'):
                        existing.next_due_date = date.fromisoformat(sub_data['next_due_date'])
                    existing.url = sub_data.get('url', existing.url)
                    existing.notes = sub_data.get('notes', existing.notes)
                    existing.icon = sub_data.get('icon', existing.icon)
                    existing.is_active = sub_data.get('is_active', existing.is_active)
                    existing.is_variable = sub_data.get('is_variable', existing.is_variable)
                else:
                    sub = Subscription(
                        name=sub_data['name'],
                        category_id=category.id if category else None,
                        payment_method_id=payment_method.id if payment_method else None,
                        amount=sub_data.get('amount', 0),
                        currency=sub_data.get('currency', 'TRY'),
                        billing_cycle=sub_data.get('billing_cycle', 'monthly'),
                        next_due_date=date.fromisoformat(sub_data['next_due_date']) if sub_data.get('next_due_date') else None,
                        url=sub_data.get('url'),
                        notes=sub_data.get('notes'),
                        icon=sub_data.get('icon', 'receipt'),
                        is_active=sub_data.get('is_active', True),
                        is_variable=sub_data.get('is_variable', False)
                    )
                    db.session.add(sub)
                imported['subscriptions'] += 1
            db.session.commit()
        
        # Import payments
        if import_payments and 'payments' in data:
            for pay_data in data['payments']:
                # Find subscription and payment method by name
                subscription = None
                if pay_data.get('subscription_name'):
                    subscription = Subscription.query.filter_by(name=pay_data['subscription_name']).first()
                
                if not subscription:
                    continue  # Skip payments without valid subscription
                
                payment_method = None
                if pay_data.get('payment_method_name'):
                    payment_method = PaymentMethod.query.filter_by(name=pay_data['payment_method_name']).first()
                
                payment = Payment(
                    subscription_id=subscription.id,
                    payment_method_id=payment_method.id if payment_method else None,
                    amount=pay_data.get('amount', 0),
                    original_amount=pay_data.get('original_amount'),
                    currency=pay_data.get('currency', 'TRY'),
                    paid_date=date.fromisoformat(pay_data['paid_date']) if pay_data.get('paid_date') else date.today(),
                    notes=pay_data.get('notes')
                )
                db.session.add(payment)
                imported['payments'] += 1
            db.session.commit()
        
        flash(f"Import complete! Categories: {imported['categories']}, Payment Methods: {imported['payment_methods']}, Subscriptions: {imported['subscriptions']}, Payments: {imported['payments']}", 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('import.html')
