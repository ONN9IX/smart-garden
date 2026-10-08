"""Provider-neutral account email delivery with a standard-library SMTP implementation."""

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from app.core.config import get_settings


class EmailSender(Protocol):
    def send(self, *, recipient: str, subject: str, text: str) -> None: ...


@dataclass
class InMemoryEmailSender:
    messages: list[dict[str, str]]

    def send(self, *, recipient: str, subject: str, text: str) -> None:
        self.messages.append({"recipient": recipient, "subject": subject, "text": text})


class DisabledEmailSender:
    def send(self, *, recipient: str, subject: str, text: str) -> None:
        raise RuntimeError("Email delivery is disabled")


class SMTPEmailSender:
    def send(self, *, recipient: str, subject: str, text: str) -> None:
        settings = get_settings()
        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)


def get_email_sender() -> EmailSender:
    return SMTPEmailSender() if get_settings().email_delivery == "smtp" else DisabledEmailSender()

