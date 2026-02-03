from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app import db


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), default='#6b7280')  # Hex color
    icon = db.Column(db.String(30), default='box')  # Lucide icon name
    
    subscriptions = db.relationship('Subscription', backref='category', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'icon': self.icon
        }


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "My Bank", "Visa 9365"
    method_type = db.Column(db.String(20), nullable=False)  # bank, credit_card, mobile
    identifier = db.Column(db.String(50), nullable=True)  # Last 4 digits, account hint
    color = db.Column(db.String(7), default='#6b7280')
    icon = db.Column(db.String(30), default='credit-card')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    subscriptions = db.relationship('Subscription', backref='payment_method', lazy='dynamic')
    payments = db.relationship('Payment', backref='payment_method', lazy='dynamic')
    
    @property
    def display_name(self):
        if self.identifier:
            return f"{self.name} ({self.identifier})"
        return self.name
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'method_type': self.method_type,
            'identifier': self.identifier,
            'display_name': self.display_name,
            'color': self.color,
            'icon': self.icon,
            'is_default': self.is_default
        }


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)  # For variable: estimated amount
    currency = db.Column(db.String(3), default='TRY')  # TRY, USD, EUR
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly, weekly
    next_due_date = db.Column(db.Date, nullable=True)
    url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(30), default='receipt')  # Lucide icon name
    is_active = db.Column(db.Boolean, default=True)
    is_variable = db.Column(db.Boolean, default=False)  # For utilities with variable amounts
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    payments = db.relationship('Payment', backref='subscription', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def is_overdue(self):
        if self.next_due_date and self.is_active:
            return self.next_due_date < date.today()
        return False
    
    @property
    def days_until_due(self):
        if self.next_due_date:
            delta = self.next_due_date - date.today()
            return delta.days
        return None
    
    def advance_due_date(self):
        """Advance the due date based on billing cycle."""
        if not self.next_due_date:
            return
        
        if self.billing_cycle == 'weekly':
            self.next_due_date += relativedelta(weeks=1)
        elif self.billing_cycle == 'monthly':
            self.next_due_date += relativedelta(months=1)
        elif self.billing_cycle == 'yearly':
            self.next_due_date += relativedelta(years=1)
    
    @property
    def favicon_url(self):
        """Get favicon URL from the subscription's website using Google's service."""
        if self.url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.url if self.url.startswith('http') else f'https://{self.url}')
                domain = parsed.netloc or parsed.path.split('/')[0]
                if domain:
                    # Google's favicon service - reliable and fast
                    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
            except:
                pass
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'category': self.category.to_dict() if self.category else None,
            'payment_method_id': self.payment_method_id,
            'payment_method': self.payment_method.to_dict() if self.payment_method else None,
            'amount': self.amount,
            'currency': self.currency,
            'billing_cycle': self.billing_cycle,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'url': self.url,
            'notes': self.notes,
            'icon': self.icon,
            'favicon_url': self.favicon_url,
            'is_active': self.is_active,
            'is_variable': self.is_variable,
            'is_overdue': self.is_overdue,
            'days_until_due': self.days_until_due,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)  # Actual amount paid
    original_amount = db.Column(db.Float, nullable=True)  # Expected/normal amount (for discounts)
    currency = db.Column(db.String(3), default='TRY')
    paid_date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def discount(self):
        """Calculate discount amount if original_amount is set."""
        if self.original_amount and self.original_amount > self.amount:
            return self.original_amount - self.amount
        return 0
    
    @property
    def discount_percent(self):
        """Calculate discount percentage."""
        if self.original_amount and self.original_amount > 0:
            return round((self.discount / self.original_amount) * 100, 1)
        return 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'subscription': self.subscription.to_dict() if self.subscription else None,
            'payment_method_id': self.payment_method_id,
            'payment_method': self.payment_method.to_dict() if self.payment_method else None,
            'amount': self.amount,
            'original_amount': self.original_amount,
            'discount': self.discount,
            'discount_percent': self.discount_percent,
            'currency': self.currency,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    primary_currency = db.Column(db.String(3), default='TRY')
    exchange_rates = db.Column(db.JSON, default=dict)  # {'USD': 30.5, 'EUR': 33.2}
    rates_updated_at = db.Column(db.DateTime, nullable=True)
    
    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls(primary_currency='TRY', exchange_rates={})
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def to_dict(self):
        return {
            'id': self.id,
            'primary_currency': self.primary_currency,
            'exchange_rates': self.exchange_rates,
            'rates_updated_at': self.rates_updated_at.isoformat() if self.rates_updated_at else None
        }
