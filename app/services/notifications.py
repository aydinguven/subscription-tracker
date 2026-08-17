import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending webhook notifications (Discord, Telegram, Slack, Generic)."""

    @classmethod
    def send_webhook(cls, webhook_url, title, message, subscriptions=None):
        """Send webhook notification to user's configured webhook URL."""
        if not webhook_url:
            return False, "No webhook URL configured."

        payload = cls._format_payload(webhook_url, title, message, subscriptions)

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            return True, "Notification sent successfully."
        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook_url}: {e}")
            return False, str(e)

    @classmethod
    def _format_payload(cls, url, title, message, subscriptions=None):
        """Format payload based on target webhook provider."""
        url_lower = url.lower()

        # Discord Webhook
        if 'discord.com/api/webhooks' in url_lower:
            fields = []
            if subscriptions:
                for s in subscriptions:
                    fields.append({
                        "name": s.name,
                        "value": f"{s.currency} {s.amount:.2f} — Due {s.next_due_date.strftime('%b %d, %Y') if s.next_due_date else 'N/A'}",
                        "inline": True
                    })

            return {
                "username": "Subscription Tracker",
                "avatar_url": "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/wallet.png",
                "embeds": [{
                    "title": f"🔔 {title}",
                    "description": message,
                    "color": 0x6366F1,  # Indigo accent
                    "fields": fields,
                    "footer": {"text": "SubTracker Automated Alert"}
                }]
            }

        # Slack Webhook
        elif 'hooks.slack.com' in url_lower:
            slack_text = f"*{title}*\n{message}"
            if subscriptions:
                for s in subscriptions:
                    slack_text += f"\n• *{s.name}*: {s.currency} {s.amount:.2f} (Due: {s.next_due_date})"
            return {"text": slack_text}

        # Generic Webhook
        else:
            return {
                "title": title,
                "message": message,
                "subscriptions": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "amount": s.amount,
                        "currency": s.currency,
                        "next_due_date": s.next_due_date.isoformat() if s.next_due_date else None,
                        "days_until_due": s.days_until_due
                    }
                    for s in (subscriptions or [])
                ]
            }
