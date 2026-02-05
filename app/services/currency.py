import requests
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Settings


class CurrencyService:
    """Service to handle currency conversion and exchange rate fetching."""
    
    # Fallback rates if API is unavailable (approximate as of 2024)
    FALLBACK_RATES = {
        'USD': 32.0,
        'EUR': 34.5,
        'TRY': 1.0
    }
    
    @classmethod
    def get_rates(cls, force_refresh=False):
        """Get exchange rates, fetching from API if needed."""
        settings = Settings.get_settings()
        
        # Check if we need to refresh rates
        should_refresh = force_refresh or not settings.exchange_rates or not settings.rates_updated_at
        
        if not should_refresh and settings.rates_updated_at:
            cache_hours = current_app.config.get('EXCHANGE_RATE_CACHE_HOURS', 24)
            if datetime.utcnow() - settings.rates_updated_at > timedelta(hours=cache_hours):
                should_refresh = True
        
        if should_refresh:
            new_rates = cls._fetch_rates_from_api()
            if new_rates:
                settings.exchange_rates = new_rates
                settings.rates_updated_at = datetime.utcnow()
                db.session.commit()
        
        return settings.exchange_rates or cls.FALLBACK_RATES
    
    @classmethod
    def _fetch_rates_from_api(cls):
        """Fetch exchange rates from the API."""
        api_key = current_app.config.get('EXCHANGE_RATE_API_KEY')
        
        if not api_key:
            # Try free alternative API without key
            return cls._fetch_from_free_api()
        
        url = current_app.config['EXCHANGE_RATE_API_URL'].format(
            api_key=api_key,
            base='TRY'
        )
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('result') == 'success':
                rates = data.get('conversion_rates', {})
                # We want rates TO TRY, so we need to invert
                # The API gives us TRY to other currencies
                return {
                    'USD': 1 / rates.get('USD', 0.03125) if rates.get('USD') else 32.0,
                    'EUR': 1 / rates.get('EUR', 0.029) if rates.get('EUR') else 34.5,
                    'TRY': 1.0
                }
        except Exception as e:
            current_app.logger.error(f"Failed to fetch exchange rates: {e}")
        
        return cls._fetch_from_free_api()
    
    @classmethod
    def _fetch_from_free_api(cls):
        """Fetch from a free API as fallback."""
        try:
            # Using frankfurter.app as free fallback (no key needed)
            response = requests.get(
                'https://api.frankfurter.app/latest?from=USD&to=TRY,EUR',
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            rates = data.get('rates', {})
            usd_to_try = rates.get('TRY', 32.0)
            usd_to_eur = rates.get('EUR', 0.93)
            
            # Calculate rates to TRY
            return {
                'USD': usd_to_try,
                'EUR': usd_to_try / usd_to_eur if usd_to_eur else 34.5,
                'TRY': 1.0
            }
        except Exception as e:
            current_app.logger.error(f"Failed to fetch from free API: {e}")
            return cls.FALLBACK_RATES
    
    @classmethod
    def convert_to_primary(cls, amount, from_currency, rates=None):
        """Convert an amount to the primary currency (TRY)."""
        if from_currency == 'TRY':
            return amount
        
        if rates is None:
            rates = cls.get_rates()
        
        rate = rates.get(from_currency, 1.0)
        return amount * rate
    
    @classmethod
    def format_currency(cls, amount, currency):
        """Format an amount with currency symbol."""
        symbols = {
            'TRY': '₺',
            'USD': '$',
            'EUR': '€'
        }
        symbol = symbols.get(currency, currency)
        return f"{symbol}{amount:,.2f}"
