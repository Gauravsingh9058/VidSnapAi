import uuid

from app.extensions import db
from app.models.mixins import TimestampMixin


class PaymentTransaction(TimestampMixin, db.Model):
    __tablename__ = "payment_transactions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    provider = db.Column(db.String(30), default="razorpay", nullable=False)
    order_id = db.Column(db.String(120), unique=True, nullable=False, index=True)
    payment_id = db.Column(db.String(120), unique=True)
    plan = db.Column(db.String(30), default="lifetime", nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="INR")
    status = db.Column(db.String(30), default="created", nullable=False)
    signature = db.Column(db.String(255))
    raw_payload_json = db.Column(db.Text)

    user = db.relationship("User", back_populates="payment_transactions")
