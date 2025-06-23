"""Notification service - Email/SMS/Push notifications.

Env vars:
    MAILGUN_API_KEY - for email notifications
    MAILGUN_DOMAIN - mailgun domain
    SMS_RU_API_KEY - for SMS notifications
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bot.services.db import Application, User

# Check if notification services are configured
EMAIL_ENABLED = bool(os.getenv("MAILGUN_API_KEY")
                     and os.getenv("MAILGUN_DOMAIN"))
SMS_ENABLED = bool(os.getenv("SMS_RU_API_KEY"))

if not EMAIL_ENABLED:
    print("⚠️ Email notifications disabled: MAILGUN credentials not set")

if not SMS_ENABLED:
    print("⚠️ SMS notifications disabled: SMS_RU_API_KEY not set")


async def notify_client_application_received(user: "User", app: "Application") -> None:
    """Notify client that application was received."""
    print(f"📧 [NOTIFY] Application #{app.id} received for user {user.tg_id}")

    # Email notification
    if EMAIL_ENABLED and user.email:
        try:
            await _send_email(
                to=user.email,
                subject="Заявка принята к рассмотрению",
                text=f"Ваша заявка #{app.id} успешно принята. Мы свяжемся с вами в ближайшее время."
            )
        except Exception as e:
            print(f"⚠️ Email error: {e}")

    # SMS notification
    if SMS_ENABLED and user.phone and user.preferred_contact == "sms":
        try:
            await _send_sms(
                phone=user.phone,
                text=f"Заявка #{app.id} принята. Ожидайте звонка."
            )
        except Exception as e:
            print(f"⚠️ SMS error: {e}")


async def notify_client_status_update(user: "User", app: "Application", status: str) -> None:
    """Notify client about application status change."""
    print(
        f"📧 [NOTIFY] Status update #{app.id}: {status} for user {user.tg_id}")

    status_messages = {
        "processing": "Ваша заявка взята в работу",
        "completed": "Ваша заявка выполнена",
        "cancelled": "Ваша заявка отменена"
    }

    message = status_messages.get(status, f"Статус заявки изменен: {status}")

    # Email notification
    if EMAIL_ENABLED and user.email:
        try:
            await _send_email(
                to=user.email,
                subject=f"Обновление по заявке #{app.id}",
                text=f"{message}. Заявка #{app.id}."
            )
        except Exception as e:
            print(f"⚠️ Email error: {e}")


async def notify_client_payment_required(user: "User", app: "Application", amount: float, payment_link: str) -> None:
    """Notify client that payment is required."""
    print(
        f"💳 [NOTIFY] Payment required #{app.id}: {amount} RUB for user {user.tg_id}")

    # Email notification
    if EMAIL_ENABLED and user.email:
        try:
            await _send_email(
                to=user.email,
                subject=f"Оплата заявки #{app.id}",
                text=f"Для продолжения работы по заявке #{app.id} необходима оплата {amount} руб.\nСсылка для оплаты: {payment_link}"
            )
        except Exception as e:
            print(f"⚠️ Email error: {e}")


async def _send_email(to: str, subject: str, text: str) -> None:
    """Send email via Mailgun (placeholder implementation)."""
    if not EMAIL_ENABLED:
        return

    # TODO: Implement actual Mailgun API call
    print(f"📧 Email to {to}: {subject}")


async def _send_sms(phone: str, text: str) -> None:
    """Send SMS via SMS.RU (placeholder implementation)."""
    if not SMS_ENABLED:
        return

    # TODO: Implement actual SMS.RU API call
    print(f"📱 SMS to {phone}: {text}")
