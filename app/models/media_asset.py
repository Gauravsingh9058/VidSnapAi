import uuid

from app.extensions import db
from app.models.mixins import TimestampMixin


class MediaAsset(TimestampMixin, db.Model):
    __tablename__ = "media_assets"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = db.Column(db.String(36), db.ForeignKey("generated_videos.id"), nullable=False, index=True)
    asset_type = db.Column(db.String(30), nullable=False)
    original_filename = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    public_url = db.Column(db.String(500))
    storage_provider = db.Column(db.String(30), default="local", nullable=False)

    video = db.relationship("GeneratedVideo", back_populates="assets")
