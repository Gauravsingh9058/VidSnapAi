import hashlib
import hmac
import json
from datetime import datetime, timezone

import requests
from flask import current_app

from app.extensions import db
from app.models import PaymentTransaction, User


class PaymentError(RuntimeError):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def razorpay_is_configured():
    return all(
        [
            current_app.config["RAZORPAY_KEY_ID"],
            current_app.config["RAZORPAY_KEY_SECRET"],
        ]
    )


def create_checkout_order(user: User):
    if not razorpay_is_configured():
        raise PaymentError("Razorpay keys are missing. Add them in your environment before accepting payments.")

    amount = current_app.config["LIFETIME_PLAN_PRICE_INR"] * 100
    currency = current_app.config["LIFETIME_PLAN_CURRENCY"]
    response = requests.post(
        f"{current_app.config['RAZORPAY_API_BASE_URL'].rstrip('/')}/v1/orders",
        auth=(current_app.config["RAZORPAY_KEY_ID"], current_app.config["RAZORPAY_KEY_SECRET"]),
        json={
            "amount": amount,
            "currency": currency,
            "receipt": f"vidsnapai-{user.id[:8]}-{int(datetime.now(timezone.utc).timestamp())}",
            "notes": {
                "user_id": user.id,
                "plan": "lifetime",
                "email": user.email,
            },
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise PaymentError("Razorpay order creation failed. Check the API keys and account status.")

    payload = response.json()
    transaction = PaymentTransaction.query.filter_by(order_id=payload["id"]).first()
    if transaction is None:
        transaction = PaymentTransaction(
            user_id=user.id,
            order_id=payload["id"],
            amount=payload["amount"],
            currency=payload["currency"],
            status=payload.get("status", "created"),
            plan="lifetime",
        )
        db.session.add(transaction)
    else:
        transaction.status = payload.get("status", transaction.status)
        transaction.amount = payload["amount"]
        transaction.currency = payload["currency"]
    transaction.raw_payload_json = json.dumps(payload)
    db.session.commit()
    return payload


def verify_checkout_signature(order_id, payment_id, signature):
    secret = current_app.config["RAZORPAY_KEY_SECRET"]
    signed_payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(payload_bytes, signature):
    secret = current_app.config["RAZORPAY_WEBHOOK_SECRET"]
    if not secret:
        raise PaymentError("Razorpay webhook secret is missing.")
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def complete_checkout(order_id, payment_id, signature, payload=None):
    transaction = PaymentTransaction.query.filter_by(order_id=order_id).first()
    if transaction is None:
        raise PaymentError("Payment order not found in the database.")

    if not verify_checkout_signature(order_id, payment_id, signature):
        raise PaymentError("Razorpay signature verification failed.")

    transaction.payment_id = payment_id
    transaction.signature = signature
    transaction.status = "paid"
    if payload is not None:
        transaction.raw_payload_json = json.dumps(payload)

    user = transaction.user
    user.plan = "lifetime"
    user.is_premium = True
    user.premium_source = "razorpay"
    user.premium_activated_at = datetime.now(timezone.utc)
    db.session.commit()
    return transaction


def process_webhook(payload_bytes, signature):
    if not verify_webhook_signature(payload_bytes, signature):
        raise PaymentError("Razorpay webhook signature did not match.")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PaymentError("Razorpay webhook payload was not valid JSON.") from exc
    event = payload.get("event")
    if event not in {"payment.captured", "order.paid"}:
        return payload

    entity = ((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
    order_id = entity.get("order_id")
    payment_id = entity.get("id")
    if not order_id or not payment_id:
        return payload

    transaction = PaymentTransaction.query.filter_by(order_id=order_id).first()
    if transaction is None:
        raise PaymentError("Webhook referenced an unknown Razorpay order.")

    transaction.payment_id = payment_id
    transaction.signature = signature
    transaction.status = "paid"
    transaction.raw_payload_json = json.dumps(payload)
    transaction.user.plan = "lifetime"
    transaction.user.is_premium = True
    transaction.user.premium_source = "razorpay-webhook"
    if transaction.user.premium_activated_at is None:
        transaction.user.premium_activated_at = datetime.now(timezone.utc)
    db.session.commit()
    return payload
