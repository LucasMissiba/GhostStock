from __future__ import annotations

from flask_mail import Message
from flask import current_app
from . import mail


def send_email(subject: str, recipients: list[str], body: str) -> None:
    if not recipients:
        return
    try:
        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
    except Exception as exc:                       
        current_app.logger.warning(f"Falha ao enviar e-mail: {exc}")











