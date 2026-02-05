FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY app/ app/
COPY config.py .
COPY run.py .

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV FLASK_ENV=production
ENV DATABASE_PATH=/app/data/subscriptions.db
ENV SECRET_KEY=change-this-in-production

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
