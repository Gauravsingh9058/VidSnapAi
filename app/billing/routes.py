from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import csrf
from app.models import PaymentTransaction
from app.services.payment_service import (
    PaymentError,
    complete_checkout,
    create_checkout_order,
    process_webhook,
    razorpay_is_configured,
)


bp = Blueprint("billing", __name__, url_prefix="/app/billing")


@bp.get("/")
@login_required
def index():
    latest_payment = (
        PaymentTransaction.query.filter_by(user_id=current_user.id)
        .order_by(PaymentTransaction.created_at.desc())
        .first()
    )
    return render_template(
        "billing/index.html",
        title="Billing",
        dashboard_shell=True,
        active_page="billing",
        latest_payment=latest_payment,
        razorpay_ready=razorpay_is_configured(),
    )


@bp.post("/checkout")
@login_required
def checkout():
    if current_user.is_premium:
        flash("Your workspace already has premium lifetime access.", "success")
        return redirect(url_for("billing.index"))

    try:
        order = create_checkout_order(current_user)
    except PaymentError as exc:
        flash(exc.message, "error")
        return redirect(url_for("billing.index"))

    return render_template(
        "billing/checkout.html",
        title="Complete checkout",
        dashboard_shell=True,
        active_page="billing",
        order=order,
        razorpay_key_id=current_app.config["RAZORPAY_KEY_ID"],
        billing_name=current_user.name,
        billing_email=current_user.email,
    )


@bp.post("/verify")
@login_required
def verify():
    order_id = request.form.get("razorpay_order_id", "").strip()
    payment_id = request.form.get("razorpay_payment_id", "").strip()
    signature = request.form.get("razorpay_signature", "").strip()

    if not order_id or not payment_id or not signature:
        flash("Razorpay did not return the full payment confirmation payload.", "error")
        return redirect(url_for("billing.index"))

    transaction = PaymentTransaction.query.filter_by(order_id=order_id, user_id=current_user.id).first()
    if transaction is None:
        flash("That payment order does not belong to the signed-in account.", "error")
        return redirect(url_for("billing.index"))

    try:
        complete_checkout(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
            payload={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
            },
        )
        flash("Payment verified. Lifetime premium access is now active on your workspace.", "success")
    except PaymentError as exc:
        flash(exc.message, "error")
    return redirect(url_for("dashboard.index"))


@bp.post("/razorpay/webhook")
@csrf.exempt
def webhook():
    signature = request.headers.get("X-Razorpay-Signature", "")
    payload = request.get_data()
    if not signature:
        abort(400)

    try:
        process_webhook(payload, signature)
    except PaymentError:
        abort(400)
    return {"status": "ok"}
