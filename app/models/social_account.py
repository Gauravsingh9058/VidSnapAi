import uuid
import json
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin


class SocialAccount(TimestampMixin, db.Model):
    __tablename__ = "social_accounts"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(120), nullable=False)
    account_id = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(120))
    page_id = db.Column(db.String(120))
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    token_expiry = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(30), default="connected", nullable=False)
    meta_scopes = db.Column(db.Text)
    raw_metadata_json = db.Column(db.Text)
    last_error = db.Column(db.Text)

    user = db.relationship("User", back_populates="social_accounts")
    post_jobs = db.relationship("PostJob", back_populates="social_account")

    __table_args__ = (
        db.UniqueConstraint("user_id", "platform", "account_id", name="uq_social_accounts_user_platform_account"),
    )

    @property
    def is_active(self):
        return self.status == "connected"

    @property
    def is_expired(self):
        return bool(self.token_expiry and self.token_expiry <= datetime.now(timezone.utc))

    @property
    def scope_list(self):
        try:
            return json.loads(self.meta_scopes) if self.meta_scopes else []
        except json.JSONDecodeError:
            return []

    @property
    def metadata_payload(self):
        try:
            return json.loads(self.raw_metadata_json) if self.raw_metadata_json else {}
        except json.JSONDecodeError:
            return {}
