from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


def utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    payment_methods = db.relationship('PaymentMethod', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('Settings', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#6b7280')  # Hex color
    icon = db.Column(db.String(30), default='box')  # Lucide icon name

    subscriptions = db.relationship('Subscription', backref='category', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_category_user_name'),
    )

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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "My Bank", "Visa 9365"
    method_type = db.Column(db.String(20), nullable=False)  # bank, credit_card, debit_card, mobile, wallet, other
    identifier = db.Column(db.String(50), nullable=True)  # Last 4 digits, account hint
    color = db.Column(db.String(7), default='#6b7280')
    icon = db.Column(db.String(30), default='credit-card')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id', ondelete='SET NULL'), nullable=True, index=True)
    amount = db.Column(db.Float, nullable=False)  # For variable: estimated amount
    currency = db.Column(db.String(3), default='TRY')  # TRY, USD, EUR, GBP, etc.
    billing_cycle = db.Column(db.String(20), default='monthly')  # weekly, bi-weekly, monthly, quarterly, semi-annual, yearly
    next_due_date = db.Column(db.Date, nullable=True, index=True)
    url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(30), default='receipt')  # Lucide icon name
    tags = db.Column(db.String(255), nullable=True)  # Comma-separated tags (e.g. "personal,entertainment")
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_variable = db.Column(db.Boolean, default=False)  # For utilities with variable amounts
    created_at = db.Column(db.DateTime, default=utc_now)

    payments = db.relationship('Payment', backref='subscription', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('ix_subscriptions_user_active', 'user_id', 'is_active'),
        db.Index('ix_subscriptions_user_due', 'user_id', 'next_due_date'),
    )

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

    @property
    def monthly_amount(self):
        """Calculate normalized monthly amount based on billing cycle."""
        if self.billing_cycle == 'weekly':
            return (self.amount * 52.0) / 12.0
        elif self.billing_cycle == 'bi-weekly':
            return (self.amount * 26.0) / 12.0
        elif self.billing_cycle == 'quarterly':
            return self.amount / 3.0
        elif self.billing_cycle == 'semi-annual':
            return self.amount / 6.0
        elif self.billing_cycle == 'yearly':
            return self.amount / 12.0
        return self.amount

    @property
    def yearly_amount(self):
        """Calculate normalized yearly amount based on billing cycle."""
        if self.billing_cycle == 'weekly':
            return self.amount * 52.0
        elif self.billing_cycle == 'bi-weekly':
            return self.amount * 26.0
        elif self.billing_cycle == 'monthly':
            return self.amount * 12.0
        elif self.billing_cycle == 'quarterly':
            return self.amount * 4.0
        elif self.billing_cycle == 'semi-annual':
            return self.amount * 2.0
        elif self.billing_cycle == 'yearly':
            return self.amount
        return self.amount * 12.0

    def advance_due_date(self):
        """Advance the due date based on billing cycle."""
        if not self.next_due_date:
            return

        if self.billing_cycle == 'weekly':
            self.next_due_date += relativedelta(weeks=1)
        elif self.billing_cycle == 'bi-weekly':
            self.next_due_date += relativedelta(weeks=2)
        elif self.billing_cycle == 'monthly':
            self.next_due_date += relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            self.next_due_date += relativedelta(months=3)
        elif self.billing_cycle == 'semi-annual':
            self.next_due_date += relativedelta(months=6)
        elif self.billing_cycle == 'yearly':
            self.next_due_date += relativedelta(years=1)

    @property
    def tag_list(self):
        """Return tags as a clean list of trimmed strings."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def favicon_url(self):
        """Get favicon URL from the subscription's website using Google's service."""
        if self.url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self.url if self.url.startswith('http') else f'https://{self.url}')
                domain = parsed.netloc or parsed.path.split('/')[0]
                if domain:
                    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
            except Exception:
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
            'amount': round(self.amount, 2),
            'currency': self.currency,
            'billing_cycle': self.billing_cycle,
            'monthly_amount': round(self.monthly_amount, 2),
            'yearly_amount': round(self.yearly_amount, 2),
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'url': self.url,
            'notes': self.notes,
            'icon': self.icon,
            'tags': self.tag_list,
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id', ondelete='SET NULL'), nullable=True, index=True)
    amount = db.Column(db.Float, nullable=False)  # Actual amount paid
    original_amount = db.Column(db.Float, nullable=True)  # Expected/normal amount (for discounts)
    currency = db.Column(db.String(3), default='TRY')
    paid_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index('ix_payments_user_paid_date', 'user_id', 'paid_date'),
    )

    @property
    def discount(self):
        """Calculate discount amount if original_amount is set."""
        if self.original_amount and self.original_amount > self.amount:
            return self.original_amount - self.amount
        return 0.0

    @property
    def discount_percent(self):
        """Calculate discount percentage."""
        if self.original_amount and self.original_amount > 0:
            return round((self.discount / self.original_amount) * 100.0, 1)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'subscription': self.subscription.to_dict() if self.subscription else None,
            'payment_method_id': self.payment_method_id,
            'payment_method': self.payment_method.to_dict() if self.payment_method else None,
            'amount': round(self.amount, 2),
            'original_amount': round(self.original_amount, 2) if self.original_amount else None,
            'discount': round(self.discount, 2),
            'discount_percent': self.discount_percent,
            'currency': self.currency,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Settings(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, unique=True, index=True)
    primary_currency = db.Column(db.String(3), default='TRY')
    exchange_rates = db.Column(db.JSON, default=dict)  # {'USD': 35.0, 'EUR': 38.0, 'GBP': 44.0, 'TRY': 1.0}
    rates_updated_at = db.Column(db.DateTime, nullable=True)
    theme = db.Column(db.String(10), default='dark')  # dark, light, system
    webhook_url = db.Column(db.String(255), nullable=True)  # Discord, Telegram, generic webhook
    notify_days_before = db.Column(db.Integer, default=3)  # Days before due date to trigger notification

    @classmethod
    def get_settings(cls, user_id=None):
        """Get settings for a user or create default."""
        if user_id:
            settings = cls.query.filter_by(user_id=user_id).first()
            if not settings:
                settings = cls(
                    user_id=user_id,
                    primary_currency='TRY',
                    exchange_rates={},
                    theme='dark',
                    notify_days_before=3
                )
                db.session.add(settings)
                db.session.commit()
            return settings

        # Fallback for unauthenticated or system queries
        settings = cls.query.first()
        if not settings:
            settings = cls(
                user_id=None,
                primary_currency='TRY',
                exchange_rates={},
                theme='dark',
                notify_days_before=3
            )
            db.session.add(settings)
            db.session.commit()
        return settings

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'primary_currency': self.primary_currency,
            'exchange_rates': self.exchange_rates or {},
            'rates_updated_at': self.rates_updated_at.isoformat() if self.rates_updated_at else None,
            'theme': self.theme,
            'webhook_url': self.webhook_url,
            'notify_days_before': self.notify_days_before
        }
