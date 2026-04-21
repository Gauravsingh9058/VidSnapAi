import uuid

from app.extensions import db
from app.models.mixins import TimestampMixin


class GeneratedVideo(TimestampMixin, db.Model):
    __tablename__ = "generated_videos"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    script = db.Column(db.Text)
    style = db.Column(db.String(50), nullable=False)
    language = db.Column(db.String(30), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    aspect_ratio = db.Column(db.String(20), nullable=False)
    template = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255))
    thumbnail_path = db.Column(db.String(255))
    file_url = db.Column(db.String(500))
    thumbnail_url = db.Column(db.String(500))
    storage_provider = db.Column(db.String(30), default="local", nullable=False)
    status = db.Column(db.String(30), default="queued", nullable=False)
    source_asset_count = db.Column(db.Integer, default=0, nullable=False)
    processing_started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    error_message = db.Column(db.Text)

    user = db.relationship("User", back_populates="generated_videos")
    assets = db.relationship("MediaAsset", back_populates="video", cascade="all, delete-orphan")
    caption_set = db.relationship("CaptionSet", back_populates="video", uselist=False, cascade="all, delete-orphan")
    post_jobs = db.relationship("PostJob", back_populates="video", cascade="all, delete-orphan")

    @property
    def is_ready(self):
        return self.status == "ready"

    @property
    def is_processing(self):
        return self.status in {"queued", "processing", "uploading"}
