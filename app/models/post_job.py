import uuid
from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin


class PostJob(TimestampMixin, db.Model):
    __tablename__ = "post_jobs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    video_id = db.Column(db.String(36), db.ForeignKey("generated_videos.id"), nullable=False, index=True)
    social_account_id = db.Column(db.String(36), db.ForeignKey("social_accounts.id"), nullable=True, index=True)
    caption_text = db.Column(db.Text)
    hashtags_text = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime(timezone=True))
    published_time = db.Column(db.DateTime(timezone=True))
    platform = db.Column(db.String(50))
    status = db.Column(db.String(30), default="draft", nullable=False)
    error_message = db.Column(db.Text)

    user = db.relationship("User", back_populates="post_jobs")
    video = db.relationship("GeneratedVideo", back_populates="post_jobs")
    social_account = db.relationship("SocialAccount", back_populates="post_jobs")

    @property
    def is_pending(self):
        return self.status == "pending"

    @property
    def is_scheduled(self):
        return self.status == "pending" and self.scheduled_time is not None

    @property
    def is_published(self):
        return self.status == "published"
