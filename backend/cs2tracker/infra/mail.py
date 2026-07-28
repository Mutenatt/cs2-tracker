"""
Envío de mail transaccional (verificación de email, reset de contraseña).
Best-effort: sin CS2_SMTP_HOST configurado, o si el envío falla, imprime el
mensaje a consola en vez de romper el flujo -- mismo criterio que
CS2_STEAM_API_KEY en auth.py (degrada con gracia, nunca rompe el caller).
"""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from cs2tracker.config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        print(f"[mail] SMTP no configurado -- para: {to} | asunto: {subject}\n{body}")
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except Exception as e:
        print(f"[mail] error enviando a {to}: {e}\n{body}")
