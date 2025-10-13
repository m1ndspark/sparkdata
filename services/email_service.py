import os
import requests

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME", "Papillon House Bookkeeping")

TEMPLATE_PATH = "utils/email_templates/chatbot_recap_template.html"


def send_recap_email(to_email: str, first_name: str, recap_body: str):
    """Send recap email via SendGrid using the HTML template."""
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY not set")

    # Load HTML template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html_template = f.read()

    # Replace placeholders
    html_body = (
        html_template.replace("{{first_name}}", first_name)
        .replace("{{recap_body}}", recap_body)
    )

    # Fallback plain text
    text_body = f"Hi {first_name},\n\n{recap_body}\n\n– Papillon House Bookkeeping"

    # Prepare SendGrid request
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": "Your Papillon House Consultation Recap",
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in (200, 202):
        raise Exception(f"SendGrid error {response.status_code}: {response.text}")

    return True

