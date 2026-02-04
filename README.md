# Subscription Manager

A personal Flask web application for tracking subscriptions, payments, and utilities.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- 📊 **Dashboard** - Overview with spending charts and upcoming payments
- 💳 **Subscriptions** - Track recurring subscriptions with auto-icon detection
- 🔄 **Variable Utilities** - Support for bills with varying amounts (electricity, water, etc.)
- 💰 **Discount Tracking** - Record when you pay less than normal price
- 🐷 **Savings Calculator** - Track total money saved from discounts
- 💱 **Multi-Currency** - TRY, USD, EUR with auto-fetched exchange rates
- 🏷️ **Categories** - Organize with custom colors and icons
- 💳 **Payment Methods** - Track which card/account is used
- 🌐 **Favicon Support** - Automatically fetches brand logos from URLs
- 📤 **Export/Import** - Backup and restore your data
- 🌙 **Dark/Light Theme** - Toggle between themes

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite + SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript
- **Charts**: Chart.js
- **Icons**: Lucide Icons

---

## Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/aydinguven/subscription-manager.git
cd subscription-manager

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python run.py
```

Open http://127.0.0.1:5000

---

## Linux Installation (Production)

### One-Line Install

```bash
sudo ./setup.sh
```

### Custom Installation

```bash
sudo ./setup.sh --dir /opt/myapp --port 8080
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dir <path>` | Installation directory | `/opt/subscription-tracker` |
| `--port <port>` | Port to run on | `5000` |
| `--no-service` | Don't create systemd service | - |
| `--non-interactive` | Skip prompts | - |

### After Installation

```bash
# Start the service
sudo systemctl start subscription-tracker

# Stop the service
sudo systemctl stop subscription-tracker

# View logs
sudo journalctl -u subscription-tracker -f

# Check status
sudo systemctl status subscription-tracker
```

### Uninstall

```bash
sudo ./uninstall.sh
```

---

## Docker (Optional)

```bash
# Build
docker build -t subscription-tracker .

# Run
docker run -d -p 5000:5000 -v subtracker-data:/app/data subscription-tracker
```

---

## Configuration

Environment variables (set in `.env` or system environment):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `DATABASE_PATH` | SQLite database path | `./data/subscriptions.db` |
| `FLASK_ENV` | Environment mode | `development` |
| `PORT` | Server port | `5000` |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Dashboard statistics |
| `/api/rates` | GET | Exchange rates |
| `/api/categories` | GET | All categories |
| `/api/payment-methods` | GET | All payment methods |
| `/data/export` | GET/POST | Export data |
| `/data/import` | GET/POST | Import data |

---

## Screenshots

Coming soon...

---

## License

MIT License - see [LICENSE](LICENSE) for details.
