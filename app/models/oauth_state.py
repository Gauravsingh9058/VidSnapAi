import uuid
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin


class OAuthState(TimestampMixin, db.Model):
    __tablename__ = "oauth_states"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    provider = db.Column(db.String(50), default="meta", nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    state_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    redirect_uri = db.Column(db.String(255), nullable=False)
    social_account_id = db.Column(db.String(36), db.ForeignKey("social_accounts.id"))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User")
    social_account = db.relationship("SocialAccount")

    @property
    def is_expired(self):
        return self.expires_at <= datetime.now(timezone.utc)

    @property
    def is_used(self):
        return self.used_at is not None
