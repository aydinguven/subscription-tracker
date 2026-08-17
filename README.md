# SubTracker (Subscription & Recurring Expense Tracker)

A modern, secure, multi-user web application for tracking recurring subscriptions, utility bills, discounts, and payment methods across multiple currencies with automated exchange rate conversion.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)
![Tests](https://img.shields.io/badge/Pytest-Passing-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ Features

- 📊 **Dynamic Dashboard**: Spending trends, category doughnuts, upcoming & overdue bills converted to your chosen primary currency.
- 💱 **Multi-Currency Engine**: Supports TRY, USD, EUR, GBP, CAD, AUD, JPY, CHF with automated live rate syncing and user-configurable base currency.
- 📅 **Renewal Calendar**: Interactive monthly timeline view of upcoming renewals and due dates.
- 🔁 **Flexible Billing Cycles**: Monthly, Yearly, Weekly, Bi-Weekly, Quarterly (3-Month), and Semi-Annual (6-Month) recurrence.
- 💰 **Discounts & Savings Calculator**: Track when you pay less than retail and monitor total money saved.
- 🔔 **Automated Webhook Alerts**: Webhook notifications (Discord, Telegram, Slack, Generic JSON) for subscriptions due soon or overdue.
- 📱 **Progressive Web App (PWA)**: Installable on iOS, Android, and Desktop with offline caching.
- 📤 **Comprehensive Data Export & Import**: Full backups in JSON, multi-sheet Excel (`.xlsx`), and CSV formats.
- ⚡ **Instant Search & Filters**: Live search across subscriptions and payments with custom tag support.
- 🔒 **Hardened Security**: CSRF protection on all forms, IDOR protection across all user relationships, rate limiting, and password hashing.
- 🌙 **Dark & Light Mode**: Fluid, instant theme toggling with zero layout shifts.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+ / Flask 3.1, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter, Flask-Migrate
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Vanilla CSS Design System, HTML5, Lucide Icons, Chart.js, Flatpickr, HTMX
- **Testing**: Pytest & Pytest-Flask
- **Deployment**: Docker, Docker Compose, Gunicorn, Systemd

---

## 🚀 Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/aydinguven/subscription-tracker.git
cd subscription-tracker

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 🧪 Running Automated Tests

```bash
python -m pytest -v
```

---

## 🐳 Docker & Docker Compose

```bash
# Start container in background
docker compose up -d

# View logs
docker compose logs -f
```

---

## 🔔 Scheduled Reminders & Webhook Cron

To run the automated reminder checks periodically (e.g. daily via cron):

```bash
# Crontab example (runs daily at 9:00 AM)
0 9 * * * cd /path/to/subscription-tracker && /path/to/venv/bin/python scripts/check_reminders.py
```

---

## 🌐 Git Remotes (GitHub & git.aydin.cloud)

This repository can be configured to push simultaneously to both GitHub and `git.aydin.cloud`:

```bash
# Add git.aydin.cloud remote
git remote add aydincloud https://git.aydin.cloud/aydin/subscription-tracker.git

# Or configure dual push on 'origin':
git remote set-url --add --push origin https://github.com/aydinguven/subscription-tracker.git
git remote set-url --add --push origin https://git.aydin.cloud/aydin/subscription-tracker.git
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
