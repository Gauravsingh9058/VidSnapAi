import uuid
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin


class PendingSocialAccountSelection(TimestampMixin, db.Model):
    __tablename__ = "pending_social_account_selections"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False)
    encrypted_user_token = db.Column(db.Text, nullable=False)
    token_expiry = db.Column(db.DateTime(timezone=True))
    granted_scopes = db.Column(db.Text)
    raw_assets_json = db.Column(db.Text, nullable=False)
    reconnect_social_account_id = db.Column(db.String(36), db.ForeignKey("social_accounts.id"))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    user = db.relationship("User")
    reconnect_social_account = db.relationship("SocialAccount")

    @property
    def is_expired(self):
        return self.expires_at <= datetime.now(timezone.utc)
