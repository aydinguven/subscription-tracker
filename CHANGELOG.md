# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-08-17

### 🔒 Security & Architecture
- **CSRF Protection**: Integrated `Flask-WTF` CSRF protection across all forms and HTMX AJAX requests.
- **IDOR Protection**: Enforced strict ownership validation across subscriptions, categories, payment methods, and payments.
- **Rate Limiting**: Added `Flask-Limiter` on authentication endpoints (`/login`, `/register`).
- **Timezone Modernization**: Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`.
- **Database Optimization**: Added indexes on `(user_id, is_active)`, `(user_id, paid_date)`, and `(user_id, next_due_date)`.
- **Database Migrations**: Integrated `Flask-Migrate` (Alembic) support.

### 💱 Multi-Currency & Settings
- **Dynamic Base Currency**: Users can configure their preferred primary currency (`TRY`, `USD`, `EUR`, `GBP`, `CAD`, `AUD`, `JPY`, `CHF`).
- **Live Conversions**: Dashboard metrics, charts, and yearly reports dynamically convert to the user's primary currency.
- **Currency Service**: Multi-base conversion engine with automated fallback caching and symbol formatting.
- **Settings Dashboard**: Dedicated page for primary currency, display name, password updates, and webhook configuration.

### 🚀 Features & Usability
- **Renewal Calendar View**: Interactive monthly calendar timeline displaying upcoming bills with quick-payment logging.
- **Expanded Billing Cycles**: Support for `weekly`, `bi-weekly`, `monthly`, `quarterly` (3-month), `semi-annual` (6-month), and `yearly`.
- **Instant Search & Sort**: Real-time filtering by text query, category, cycle, status, and custom tag support.
- **Quick-Pay Modal**: One-click payment recording directly from the dashboard and renewal calendar.
- **Excel & CSV Export/Import**: Full multi-sheet Excel (`.xlsx`) and CSV export/import alongside JSON backups.
- **Automated Webhooks**: Notification service supporting Discord, Slack, Telegram, and generic HTTP webhooks for upcoming due dates.
- **Progressive Web App (PWA)**: Mobile-installable application with `manifest.json` and service worker caching.

### 🧪 Quality Assurance & DevOps
- **Automated Test Suite**: Added 19 comprehensive Pytest tests covering auth, IDOR isolation, cycles math, currency conversion, payments, and data imports/exports.
- **CI/CD Pipelines**: GitHub Actions, Forgejo Actions, and Gitea Actions workflows.
- **Docker Compose**: Containerized production environment with health checks and volume persistence.
- **Scheduled Reminders CLI**: `scripts/check_reminders.py` for cron-based webhook alerts.

---

## [1.2.0]
- Multi-user authentication support
- Basic JSON export and import
- Category and payment method management

## [1.1.0]
- Initial release with subscription tracking and SQLite database
