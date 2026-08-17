import logging
import requests
from datetime import datetime, timezone, timedelta
from flask import current_app
from app import db
from app.models import Settings

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service to handle multi-currency conversion, caching, and rate fetching."""

    # Base fallback rates relative to USD (USD = 1.0)
    FALLBACK_RATES_TO_USD = {
        'USD': 1.0,
        'EUR': 0.92,
        'TRY': 36.0,
        'GBP': 0.79,
        'CAD': 1.38,
        'AUD': 1.55,
        'JPY': 152.0,
        'CHF': 0.88,
    }

    CURRENCY_SYMBOLS = {
        'TRY': '₺',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'CAD': 'CA$',
        'AUD': 'AU$',
        'JPY': '¥',
        'CHF': 'CHF ',
    }

    @classmethod
    def get_symbol(cls, currency):
        """Get symbol for a given currency code."""
        return cls.CURRENCY_SYMBOLS.get(currency.upper() if currency else 'TRY', f"{currency} ")

    @classmethod
    def get_rates(cls, user_id=None, force_refresh=False):
        """Get exchange rates dictionary, fetching from API if stale or missing."""
        try:
            settings = Settings.get_settings(user_id=user_id)
        except Exception:
            settings = None

        now = datetime.now(timezone.utc)
        cache_hours = 12
        if current_app:
            cache_hours = current_app.config.get('EXCHANGE_RATE_CACHE_HOURS', 12)

        should_refresh = force_refresh
        if not should_refresh:
            if not settings or not settings.exchange_rates or not settings.rates_updated_at:
                should_refresh = True
            else:
                updated_at = settings.rates_updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if now - updated_at > timedelta(hours=cache_hours):
                    should_refresh = True

        if should_refresh:
            new_rates = cls._fetch_rates_from_api()
            if new_rates and settings:
                settings.exchange_rates = new_rates
                settings.rates_updated_at = now
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.warning(f"Could not persist rates to database: {e}")
                return new_rates

        if settings and settings.exchange_rates:
            return settings.exchange_rates

        return cls.FALLBACK_RATES_TO_USD

    @classmethod
    def _fetch_rates_from_api(cls):
        """Fetch exchange rates from API with free fallback."""
        api_key = None
        if current_app:
            api_key = current_app.config.get('EXCHANGE_RATE_API_KEY')

        if api_key and current_app:
            try:
                url_template = current_app.config.get(
                    'EXCHANGE_RATE_API_URL',
                    'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}'
                )
                url = url_template.format(api_key=api_key, base='USD')
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                data = response.json()
                if data.get('result') == 'success':
                    return data.get('conversion_rates', cls.FALLBACK_RATES_TO_USD)
            except Exception as e:
                logger.error(f"ExchangeRate-API failed: {e}")

        # Fallback to Frankfurter free API (Base: USD)
        try:
            response = requests.get(
                'https://api.frankfurter.app/latest?from=USD',
                timeout=8
            )
            response.raise_for_status()
            data = response.json()
            rates = data.get('rates', {})
            rates['USD'] = 1.0
            return rates
        except Exception as e:
            logger.warning(f"Frankfurter API fallback failed: {e}")

        return cls.FALLBACK_RATES_TO_USD

    @classmethod
    def convert(cls, amount, from_currency, to_currency, rates=None):
        """Convert amount from one currency to another using USD-relative exchange rates."""
        if not amount:
            return 0.0

        from_curr = from_currency.upper() if from_currency else 'TRY'
        to_curr = to_currency.upper() if to_currency else 'TRY'

        if from_curr == to_curr:
            return float(amount)

        if rates is None:
            rates = cls.get_rates()

        # Rates are relative to USD (1 USD = X Currency)
        # To convert: amount in from_curr -> USD -> to_curr
        rate_from = rates.get(from_curr, cls.FALLBACK_RATES_TO_USD.get(from_curr, 1.0))
        rate_to = rates.get(to_curr, cls.FALLBACK_RATES_TO_USD.get(to_curr, 1.0))

        if rate_from <= 0:
            rate_from = 1.0

        # Amount in USD = amount / rate_from
        amount_usd = amount / rate_from
        # Amount in to_curr = amount_usd * rate_to
        return amount_usd * rate_to

    @classmethod
    def convert_to_primary(cls, amount, from_currency, user_id=None, rates=None, primary_currency=None):
        """Convert amount to the user's primary currency."""
        if not primary_currency:
            try:
                settings = Settings.get_settings(user_id=user_id)
                primary_currency = settings.primary_currency or 'TRY'
            except Exception:
                primary_currency = 'TRY'

        return cls.convert(amount, from_currency, primary_currency, rates=rates)

    @classmethod
    def format_currency(cls, amount, currency='TRY'):
        """Format an amount with the appropriate currency symbol and decimal formatting."""
        if amount is None:
            return ""
        curr = currency.upper() if currency else 'TRY'
        symbol = cls.get_symbol(curr)
        return f"{symbol}{float(amount):,.2f}"
