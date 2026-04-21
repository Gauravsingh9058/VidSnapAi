import uuid

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.mixins import TimestampMixin


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(30), default="free", nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    premium_activated_at = db.Column(db.DateTime(timezone=True))
    premium_source = db.Column(db.String(50))
    notify_product_updates = db.Column(db.Boolean, default=True, nullable=False)
    notify_scheduled_posts = db.Column(db.Boolean, default=True, nullable=False)
    notify_failures = db.Column(db.Boolean, default=True, nullable=False)

    social_accounts = db.relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    generated_videos = db.relationship("GeneratedVideo", back_populates="user", cascade="all, delete-orphan")
    payment_transactions = db.relationship("PaymentTransaction", back_populates="user", cascade="all, delete-orphan")
    post_jobs = db.relationship("PostJob", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def account_limit(self, app_config):
        if self.is_premium:
            return app_config["MAX_SOCIAL_ACCOUNTS_PER_USER"]
        return 1

    @property
    def plan_label(self):
        return "lifetime" if self.is_premium else "free"

    @property
    def can_schedule(self):
        return self.is_premium

    @property
    def can_publish_directly(self):
        return self.is_premium

    @property
    def has_priority_processing(self):
        return self.is_premium

    @property
    def should_watermark_exports(self):
        return not self.is_premium
