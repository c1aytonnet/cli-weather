from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any, Dict

from .weather import fetch_weather_report, format_weather_report


class EmailConfigurationError(RuntimeError):
    pass


def validate_email_config(config: Dict[str, Any]) -> None:
    required = ["recipient", "sender", "smtp_host", "smtp_port"]
    missing = [field for field in required if not config.get(field)]
    if missing:
        raise EmailConfigurationError(
            "Missing email configuration values: " + ", ".join(sorted(missing))
        )


def send_weather_email(config: Dict[str, Any], location: str | None = None, recipient: str | None = None) -> str:
    validate_email_config(config)
    resolved_location = location or config.get("location")
    resolved_recipient = recipient or config.get("recipient")
    if not resolved_location:
        raise EmailConfigurationError("No location was provided and no default location is configured.")
    if not resolved_recipient:
        raise EmailConfigurationError("No email recipient was provided and no default recipient is configured.")
    recipients = _parse_recipients(resolved_recipient)
    if not recipients:
        raise EmailConfigurationError("At least one valid email recipient is required.")

    report = fetch_weather_report(
        resolved_location,
        provider=config.get("provider", "metno"),
        visualcrossing_api_key=config.get("visualcrossing_api_key", ""),
    )
    body = format_weather_report(report)
    message = EmailMessage()
    message["Subject"] = f"Weather report for {report['location']}"
    message["From"] = config["sender"]
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    smtp_host = config["smtp_host"]
    smtp_port = int(config["smtp_port"])
    smtp_username = config.get("smtp_username")
    smtp_password = config.get("smtp_password")
    use_ssl = bool(config.get("smtp_ssl"))
    use_starttls = bool(config.get("smtp_starttls"))

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            if smtp_username:
                server.login(smtp_username, smtp_password or "")
            server.send_message(message, to_addrs=recipients)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            if use_starttls:
                server.starttls()
                server.ehlo()
            if smtp_username:
                server.login(smtp_username, smtp_password or "")
            server.send_message(message, to_addrs=recipients)

    return body


def _parse_recipients(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
