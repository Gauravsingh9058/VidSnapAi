import uuid
from datetime import datetime, timezone

from app.extensions import db


class CaptionSet(db.Model):
    __tablename__ = "caption_sets"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = db.Column(db.String(36), db.ForeignKey("generated_videos.id"), nullable=False, unique=True, index=True)
    main_caption = db.Column(db.Text, nullable=False)
    short_caption = db.Column(db.Text)
    cta = db.Column(db.Text)
    hashtags = db.Column(db.Text)
    first_comment = db.Column(db.Text)
    tone = db.Column(db.String(30), nullable=False)
    emoji_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    video = db.relationship("GeneratedVideo", back_populates="caption_set")
