from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from decimal import Decimal
import base64
import os
import json

"""Payment integration (CloudPayments/YooKassa).
Generate payment links and verify callbacks.
"""

# TODO: implement payment link generation

"""Payment integration – CloudPayments.

Env vars:
    CP_PUBLIC_ID – CloudPayments public key
    CP_SECRET    – secret (for signature, not stored in repo)
    PAY_BASE_URL – e.g. https://pay.cloudpayments.ru/payments/form

Function create_payment(app: Application, amount: Decimal) -> str
returns redirect URL with encoded params (json, base64) ready to open in browser.
"""


if TYPE_CHECKING:
    from bot.services.db import Application, User


CP_PUBLIC_ID = os.getenv("CP_PUBLIC_ID")
PAY_BASE_URL = os.getenv(
    "PAY_BASE_URL", "https://pay.cloudpayments.ru/payments/form")

# Make payment optional - bot can work without it
PAYMENTS_ENABLED = bool(CP_PUBLIC_ID)

if not PAYMENTS_ENABLED:
    print("⚠️ Payment system disabled: CP_PUBLIC_ID not set")


def _encode(data: dict) -> str:
    """CloudPayments expects params encoded as base64(json)."""
    raw = json.dumps(data, ensure_ascii=False).encode()
    return base64.b64encode(raw).decode()


def create_payment(app: "Application", user: "User", amount: Decimal) -> str:
    """Return redirect link to CloudPayments payment form."""
    if not PAYMENTS_ENABLED:
        return "# Платежная система не настроена"

    data = {
        "publicId": CP_PUBLIC_ID,
        "description": f"Оплата заявки #{app.id}",
        "amount": float(amount),
        "currency": "RUB",
        "invoiceId": str(app.id),
        "accountId": str(user.tg_id),
        "email": user.email or "noemail@bot.local",
        "skin": "classic",
    }
    params = urlencode({"data": _encode(data)})
    return f"{PAY_BASE_URL}?{params}"
