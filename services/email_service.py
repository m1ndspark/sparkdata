import os
import requests

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME", "Papillon House Bookkeeping")

def send_recap_email(to_email: str, subject: str, body: str):
    """Send a recap email via SendGrid SMTP API."""
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY not set")

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}]
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in (200, 202):
        raise Exception(f"SendGrid error {response.status_code}: {response.text}")
    return True
