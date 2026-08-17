#!/usr/bin/env python3
"""
Notification Reminders Script.

Checks for subscriptions due in the next X days or overdue,
and sends webhook notifications to configured endpoints (Discord, Slack, Telegram, Generic).

Usage:
    python scripts/check_reminders.py [--dry-run]
"""

import sys
import os
from datetime import date, timedelta

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Subscription, Settings
from app.services.notifications import NotificationService


def run_reminders(dry_run=False):
    app = create_app()
    with app.app_context():
        today = date.today()
        users = User.query.all()
        print(f"Checking reminders for {len(users)} users on {today.isoformat()}...")

        total_alerts = 0
        for user in users:
            settings = Settings.query.filter_by(user_id=user.id).first()
            if not settings or not settings.webhook_url:
                continue

            notify_days = settings.notify_days_before or 3
            target_due_date = today + timedelta(days=notify_days)

            # Find subscriptions due soon or overdue
            due_subs = Subscription.query.filter(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
                Subscription.next_due_date.isnot(None),
                Subscription.next_due_date <= target_due_date
            ).order_by(Subscription.next_due_date.asc()).all()

            if not due_subs:
                continue

            overdue_subs = [s for s in due_subs if s.next_due_date < today]
            upcoming_subs = [s for s in due_subs if s.next_due_date >= today]

            title = f"Subscription Reminder ({len(due_subs)} upcoming/overdue)"
            summary_lines = []
            if overdue_subs:
                summary_lines.append(f"⚠️ {len(overdue_subs)} subscription(s) are overdue!")
            if upcoming_subs:
                summary_lines.append(f"📅 {len(upcoming_subs)} subscription(s) due within {notify_days} days.")

            message = "\n".join(summary_lines)

            print(f"[{user.username}] {len(due_subs)} subscriptions to notify via {settings.webhook_url[:30]}...")

            if not dry_run:
                success, resp = NotificationService.send_webhook(
                    webhook_url=settings.webhook_url,
                    title=title,
                    message=message,
                    subscriptions=due_subs
                )
                if success:
                    print(f"  ✓ Notification delivered for user '{user.username}'")
                    total_alerts += 1
                else:
                    print(f"  ✗ Failed for user '{user.username}': {resp}")
            else:
                print("  [DRY RUN] Notification skipped.")
                total_alerts += 1

        print(f"Reminder run complete. Total alerts dispatched: {total_alerts}")


if __name__ == '__main__':
    dry_run_mode = '--dry-run' in sys.argv
    run_reminders(dry_run=dry_run_mode)
