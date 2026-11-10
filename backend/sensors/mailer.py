"""Sends one email through your own mail account (SMTP). Passwords come from backend/.env,
never from the code, so they never reach GitHub."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / '.env'   # backend/.env


class MailNotConfigured(Exception):
    pass


def load_env(path=ENV_FILE):
    """Reads KEY=value lines from backend/.env into the environment (if the file exists)."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())


def mail_settings():
    """The mail settings, or None when something is missing."""
    load_env()
    user = os.environ.get('KAYVAK_SMTP_USER', '')
    password = os.environ.get('KAYVAK_SMTP_PASSWORD', '')
    to = os.environ.get('KAYVAK_EMAIL_TO', user)
    if not (user and password and to):
        return None
    return {
        'host': os.environ.get('KAYVAK_SMTP_HOST', 'smtp.gmail.com'),
        'port': int(os.environ.get('KAYVAK_SMTP_PORT', '465')),
        'user': user,
        'password': password,
        'to': to,
    }


def is_configured():
    return mail_settings() is not None


def send_email(subject, body):
    """Sends the email. Raises an error if it cannot (no internet, wrong password, ...)."""
    cfg = mail_settings()
    if cfg is None:
        raise MailNotConfigured('Fill in backend/.env first (see backend/.env.example).')
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = cfg['user']
    msg['To'] = cfg['to']
    msg.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg['host'], cfg['port'], context=context, timeout=20) as server:
        server.login(cfg['user'], cfg['password'])
        server.send_message(msg)