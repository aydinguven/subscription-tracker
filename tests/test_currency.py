from app.services.currency import CurrencyService


def test_currency_conversion():
    """Test converting between currencies with custom rates."""
    custom_rates = {
        'USD': 1.0,
        'EUR': 0.90,
        'TRY': 36.0,
        'GBP': 0.80
    }

    # Same currency
    assert CurrencyService.convert(100.0, 'USD', 'USD', rates=custom_rates) == 100.0

    # USD to TRY: 100 USD * 36 = 3600 TRY
    val_try = CurrencyService.convert(100.0, 'USD', 'TRY', rates=custom_rates)
    assert val_try == 3600.0

    # TRY to USD: 3600 TRY / 36 = 100 USD
    val_usd = CurrencyService.convert(3600.0, 'TRY', 'USD', rates=custom_rates)
    assert val_usd == 100.0

    # EUR to GBP: (100 / 0.90) * 0.80 = approx 88.888
    val_gbp = CurrencyService.convert(100.0, 'EUR', 'GBP', rates=custom_rates)
    assert round(val_gbp, 2) == 88.89


def test_currency_formatting():
    """Test currency symbol resolution and formatting."""
    assert CurrencyService.format_currency(1234.5, 'USD') == '$1,234.50'
    assert CurrencyService.format_currency(1234.5, 'EUR') == '€1,234.50'
    assert CurrencyService.format_currency(1234.5, 'TRY') == '₺1,234.50'
    assert CurrencyService.format_currency(1234.5, 'GBP') == '£1,234.50'
