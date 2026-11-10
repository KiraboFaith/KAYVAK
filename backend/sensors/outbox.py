"""Sends an email now, or keeps it and sends it later if there is no internet."""
from .mailer import is_configured, send_email
from .models import NotificationSetting, QueuedEmail


def send_or_queue(subject, body):
    """Returns 'off', 'not configured', 'sent' or 'queued'."""
    if not NotificationSetting.current().email_enabled:
        return 'off'            # the owner has not agreed to email
    if not is_configured():
        return 'not configured'
    try:
        send_email(subject, body)
        return 'sent'
    except Exception:
        QueuedEmail.objects.create(subject=subject[:200], body=body)
        return 'queued'


def flush_queue():
    """Tries the waiting emails again, oldest first. Returns how many went out."""
    if not NotificationSetting.current().email_enabled or not is_configured():
        return 0
    sent = 0
    for item in QueuedEmail.objects.all():
        text = f'{item.body}\n\n(This message was waiting since {item.created:%d %b %Y, %H:%M}.)'
        try:
            send_email(item.subject, text)
        except Exception:
            break               # still offline: keep the rest for next time
        item.delete()
        sent += 1
    return sent