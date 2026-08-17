from datetime import date
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import extract
from app import db, csrf
from app.models import Subscription, Payment, Category, Settings, PaymentMethod
from app.services.currency import CurrencyService

bp = Blueprint('api', __name__)


@bp.route('/subscriptions')
@login_required
def get_subscriptions():
    """Get all subscriptions as JSON."""
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    return jsonify([s.to_dict() for s in subscriptions])


@bp.route('/subscriptions/<int:id>')
@login_required
def get_subscription(id):
    """Get a single subscription."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return jsonify(subscription.to_dict())


@bp.route('/payments')
@login_required
def get_payments():
    """Get payments with optional filters."""
    year = request.args.get('year', type=int)
    subscription_id = request.args.get('subscription_id', type=int)

    query = Payment.query.filter_by(user_id=current_user.id)

    if year:
        query = query.filter(extract('year', Payment.paid_date) == year)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    payments = query.order_by(Payment.paid_date.desc()).all()
    return jsonify([p.to_dict() for p in payments])


@bp.route('/categories')
@login_required
def get_categories():
    """Get all categories."""
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return jsonify([c.to_dict() for c in categories])


@bp.route('/payment-methods')
@login_required
def get_payment_methods():
    """Get all payment methods."""
    methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.name).all()
    return jsonify([m.to_dict() for m in methods])


@bp.route('/rates')
@login_required
def get_rates():
    """Get current exchange rates."""
    rates = CurrencyService.get_rates(user_id=current_user.id)
    settings = Settings.get_settings(user_id=current_user.id)
    return jsonify({
        'rates': rates,
        'primary_currency': settings.primary_currency,
        'updated_at': settings.rates_updated_at.isoformat() if settings.rates_updated_at else None
    })


@bp.route('/rates/refresh', methods=['POST'])
@login_required
def refresh_rates():
    """Force refresh exchange rates."""
    rates = CurrencyService.get_rates(user_id=current_user.id, force_refresh=True)
    settings = Settings.get_settings(user_id=current_user.id)
    return jsonify({
        'rates': rates,
        'primary_currency': settings.primary_currency,
        'updated_at': settings.rates_updated_at.isoformat() if settings.rates_updated_at else None,
        'message': 'Rates refreshed successfully'
    })


@bp.route('/stats')
@login_required
def get_stats():
    """Get dashboard statistics in primary currency."""
    settings = Settings.get_settings(user_id=current_user.id)
    primary_currency = settings.primary_currency or 'TRY'
    rates = CurrencyService.get_rates(user_id=current_user.id)
    today = date.today()

    active_subs = Subscription.query.filter_by(user_id=current_user.id, is_active=True).all()

    # Monthly total in primary currency
    monthly_total = sum(
        CurrencyService.convert_to_primary(
            sub.monthly_amount, sub.currency, rates=rates, primary_currency=primary_currency
        )
        for sub in active_subs
    )

    # Yearly total from payments
    current_year = today.year
    yearly_payments = Payment.query.filter(
        Payment.user_id == current_user.id,
        extract('year', Payment.paid_date) == current_year
    ).all()
    yearly_total = sum(
        CurrencyService.convert_to_primary(
            p.amount, p.currency, rates=rates, primary_currency=primary_currency
        )
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
            Payment.user_id == current_user.id,
            extract('year', Payment.paid_date) == year,
            extract('month', Payment.paid_date) == month
        ).all()

        total = sum(
            CurrencyService.convert_to_primary(
                p.amount, p.currency, rates=rates, primary_currency=primary_currency
            )
            for p in payments
        )

        monthly_spending.append({
            'month': f"{year}-{month:02d}",
            'total': round(total, 2)
        })

    return jsonify({
        'active_count': len(active_subs),
        'primary_currency': primary_currency,
        'currency_symbol': CurrencyService.get_symbol(primary_currency),
        'monthly_total': round(monthly_total, 2),
        'yearly_total': round(yearly_total, 2),
        'monthly_spending': monthly_spending,
        'rates': rates
    })


@bp.route('/health')
def health():
    """Health check endpoint for container health probes."""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 503
