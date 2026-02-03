from flask import Blueprint, jsonify, request
from datetime import date
from sqlalchemy import extract
from app import db
from app.models import Subscription, Payment, Category, Settings, PaymentMethod
from app.services.currency import CurrencyService

bp = Blueprint('api', __name__)


@bp.route('/subscriptions')
def get_subscriptions():
    """Get all subscriptions as JSON."""
    subscriptions = Subscription.query.all()
    return jsonify([s.to_dict() for s in subscriptions])


@bp.route('/subscriptions/<int:id>')
def get_subscription(id):
    """Get a single subscription."""
    subscription = Subscription.query.get_or_404(id)
    return jsonify(subscription.to_dict())


@bp.route('/payments')
def get_payments():
    """Get payments with optional filters."""
    year = request.args.get('year', type=int)
    subscription_id = request.args.get('subscription_id', type=int)
    
    query = Payment.query
    
    if year:
        query = query.filter(extract('year', Payment.paid_date) == year)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)
    
    payments = query.order_by(Payment.paid_date.desc()).all()
    return jsonify([p.to_dict() for p in payments])


@bp.route('/categories')
def get_categories():
    """Get all categories."""
    categories = Category.query.order_by(Category.name).all()
    return jsonify([c.to_dict() for c in categories])


@bp.route('/payment-methods')
def get_payment_methods():
    """Get all payment methods."""
    methods = PaymentMethod.query.order_by(PaymentMethod.name).all()
    return jsonify([m.to_dict() for m in methods])


@bp.route('/rates')
def get_rates():
    """Get current exchange rates."""
    rates = CurrencyService.get_rates()
    settings = Settings.get_settings()
    return jsonify({
        'rates': rates,
        'updated_at': settings.rates_updated_at.isoformat() if settings.rates_updated_at else None
    })


@bp.route('/rates/refresh', methods=['POST'])
def refresh_rates():
    """Force refresh exchange rates."""
    rates = CurrencyService.get_rates(force_refresh=True)
    settings = Settings.get_settings()
    return jsonify({
        'rates': rates,
        'updated_at': settings.rates_updated_at.isoformat() if settings.rates_updated_at else None,
        'message': 'Rates refreshed successfully'
    })


@bp.route('/stats')
def get_stats():
    """Get dashboard statistics."""
    rates = CurrencyService.get_rates()
    today = date.today()
    
    # Active subscriptions
    active_subs = Subscription.query.filter_by(is_active=True).all()
    
    # Monthly total
    monthly_total = 0
    for sub in active_subs:
        monthly_amount = sub.amount
        if sub.billing_cycle == 'yearly':
            monthly_amount = sub.amount / 12
        elif sub.billing_cycle == 'weekly':
            monthly_amount = sub.amount * 4.33
        monthly_total += CurrencyService.convert_to_primary(monthly_amount, sub.currency, rates)
    
    # Yearly total from payments
    current_year = today.year
    yearly_payments = Payment.query.filter(
        extract('year', Payment.paid_date) == current_year
    ).all()
    yearly_total = sum(
        CurrencyService.convert_to_primary(p.amount, p.currency, rates)
        for p in yearly_payments
    )
    
    # Monthly spending chart data (last 12 months)
    monthly_spending = []
    for i in range(11, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        
        payments = Payment.query.filter(
            extract('year', Payment.paid_date) == year,
            extract('month', Payment.paid_date) == month
        ).all()
        
        total = sum(
            CurrencyService.convert_to_primary(p.amount, p.currency, rates)
            for p in payments
        )
        
        monthly_spending.append({
            'month': f"{year}-{month:02d}",
            'total': round(total, 2)
        })
    
    return jsonify({
        'active_count': len(active_subs),
        'monthly_total': round(monthly_total, 2),
        'yearly_total': round(yearly_total, 2),
        'monthly_spending': monthly_spending,
        'rates': rates
    })
