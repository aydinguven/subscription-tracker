import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'subscriptions.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Currency settings
    PRIMARY_CURRENCY = 'TRY'
    SUPPORTED_CURRENCIES = ['TRY', 'USD', 'EUR']
    
    # Exchange rate API (free tier)
    # Get your free API key at: https://www.exchangerate-api.com/
    EXCHANGE_RATE_API_KEY = os.environ.get('EXCHANGE_RATE_API_KEY') or ''
    EXCHANGE_RATE_API_URL = 'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}'
    EXCHANGE_RATE_CACHE_HOURS = 24
