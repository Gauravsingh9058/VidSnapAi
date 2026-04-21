from datetime import datetime, timezone
from threading import Thread

from flask import current_app

from app.extensions import db
from app.models import CaptionSet, GeneratedVideo, MediaAsset, User
from app.services.caption_service import generate_caption_bundle
from app.services.storage_service import StorageError, active_storage_provider, upload_to_storage
from app.services.video_service import generate_video


def queue_video_generation(
    *,
    video_id,
    user_id,
    workspace,
    image_paths,
    video_path,
    audio_path,
    tone,
    caption_length,
    emoji_enabled,
    cta_strength,
):
    app = current_app._get_current_object()
    worker = Thread(
        target=_generate_video_in_background,
        kwargs={
            "app": app,
            "video_id": video_id,
            "user_id": user_id,
            "workspace": str(workspace),
            "image_paths": [str(path) for path in image_paths],
            "video_path": str(video_path) if video_path else None,
            "audio_path": str(audio_path) if audio_path else None,
            "tone": tone,
            "caption_length": caption_length,
            "emoji_enabled": emoji_enabled,
            "cta_strength": cta_strength,
        },
        daemon=True,
    )
    worker.start()
    return worker


def register_uploaded_assets(video, image_paths, video_path=None, audio_path=None):
    for image_path in image_paths:
        _register_asset(video, "image", image_path)
    if video_path:
        _register_asset(video, "video", video_path)
    if audio_path:
        _register_asset(video, "audio", audio_path)
    db.session.commit()


def _generate_video_in_background(
    *,
    app,
    video_id,
    user_id,
    workspace,
    image_paths,
    video_path,
    audio_path,
    tone,
    caption_length,
    emoji_enabled,
    cta_strength,
):
    with app.app_context():
        video = GeneratedVideo.query.filter_by(id=video_id, user_id=user_id).first()
        user = db.session.get(User, user_id)
        if video is None or user is None:
            return

        try:
            video.status = "processing"
            video.processing_started_at = datetime.now(timezone.utc)
            video.error_message = None
            db.session.commit()

            result = generate_video(
                workspace=workspace,
                image_paths=image_paths,
                video_path=video_path,
                audio_path=audio_path,
                title=video.title,
                topic=video.topic,
                duration_seconds=video.duration,
                aspect_ratio=video.aspect_ratio,
                template=video.template,
                add_watermark=user.should_watermark_exports,
                watermark_text=current_app.config["FREE_EXPORT_WATERMARK_TEXT"],
            )
            video.status = "uploading"
            video.file_path = result["file_path"]
            video.thumbnail_path = result["thumbnail_path"]
            video.duration = result["duration"]
            video.storage_provider = active_storage_provider()
            db.session.commit()

            _upload_media_assets(video)
            caption_data = generate_caption_bundle(
                topic=video.topic,
                script=video.script,
                style=video.style,
                language=video.language,
                tone=tone,
                length=caption_length,
                emoji_enabled=emoji_enabled,
                cta_strength=cta_strength,
            )
            caption_set = video.caption_set or CaptionSet(video_id=video.id, tone=tone, emoji_enabled=emoji_enabled)
            caption_set.tone = tone
            caption_set.emoji_enabled = emoji_enabled
            for key, value in caption_data.items():
                setattr(caption_set, key, value)
            db.session.add(caption_set)

            video.status = "ready"
            video.completed_at = datetime.now(timezone.utc)
            video.error_message = None
            db.session.commit()
        except Exception as exc:  # noqa: BLE001
            video.status = "failed"
            video.error_message = str(exc)
            db.session.commit()
        finally:
            db.session.remove()


def _register_asset(video, asset_type, file_path):
    asset = MediaAsset(
        video_id=video.id,
        asset_type=asset_type,
        original_filename=file_path.name,
        file_path=file_path.as_posix(),
        storage_provider="local",
    )
    db.session.add(asset)


def _upload_media_assets(video):
    for asset in video.assets:
        if asset.public_url:
            continue
        try:
            response = upload_to_storage(
                file_path=asset.file_path,
                folder=f"users/{video.user_id}/{video.id}/inputs",
                public_id=f"{asset.asset_type}-{asset.id}",
            )
            asset.storage_provider = response["provider"]
            asset.public_url = response["public_url"]
        except StorageError:
            asset.storage_provider = "local"

    if video.file_path:
        try:
            video_upload = upload_to_storage(
                file_path=current_app.config["UPLOAD_ROOT"] / video.file_path,
                folder=f"users/{video.user_id}/{video.id}/outputs",
                public_id=f"{video.id}-video",
                resource_type="video",
            )
            video.storage_provider = video_upload["provider"]
            video.file_url = video_upload["public_url"]
        except StorageError:
            video.storage_provider = "local"

    if video.thumbnail_path:
        try:
            thumb_upload = upload_to_storage(
                file_path=current_app.config["UPLOAD_ROOT"] / video.thumbnail_path,
                folder=f"users/{video.user_id}/{video.id}/outputs",
                public_id=f"{video.id}-thumbnail",
                resource_type="image",
            )
            video.thumbnail_url = thumb_upload["public_url"]
            if thumb_upload["provider"] != "local":
                video.storage_provider = thumb_upload["provider"]
        except StorageError:
            pass

    db.session.commit()
