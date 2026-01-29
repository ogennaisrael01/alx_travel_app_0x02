from django.conf import settings
from django.template.loader import render_to_string

from rest_framework.exceptions import ValidationError, server_error

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Content
from sendgrid import exceptions

SENDGRID_API_SECRET = getattr(settings, "SENDGRID_API_SECRET", None)
SENDGRID_SENDER  = getattr(settings, "SENDGRID_SENDER", None)

def send_email(context: dict):
    if any([SENDGRID_API_SECRET, SENDGRID_SENDER]) is None:
        raise ValidationError("Invalid Request: 'SENDGRID_API_SECRET' and 'SENDGRID_SENDER' are both required for the email notification to go through")
    required_fiedls = ("email", "subject", "template_name")
    if context is None or (context.get(field) for field in required_fiedls) is None:
        raise ValidationError("email context is required. provide accurate payload body")
    
    html_content = render_to_string(context.get("template_name"), context=context)
    try:
        message = Mail(
            from_email=From(SENDGRID_SENDER),
            to_emails=To(context.get("email")),
            subject=context.get("subject"),
            html_content=Content("text/html", html_content)
        )
        client = SendGridAPIClient(api_key=SENDGRID_API_SECRET)
        response = client.send(message=message)
        if response.status_code != 202:
            raise exceptions.SendGridException()
        return response
    except Exception:
        raise 