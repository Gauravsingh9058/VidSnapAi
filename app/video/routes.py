from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import GeneratedVideo, PostJob, SocialAccount
from app.services.background_jobs import queue_video_generation, register_uploaded_assets
from app.services.scheduler_service import schedule_post
from app.services.upload_service import (
    absolute_upload_path,
    is_allowed_file,
    remove_user_workspace,
    save_file,
    user_workspace,
)
from app.utils.rate_limit import rate_limit
from app.video.forms import GenerateVideoForm, PostPreviewForm


bp = Blueprint("video", __name__, url_prefix="/app")


@bp.route("/generate", methods=["GET", "POST"])
@login_required
@rate_limit("generate-video", limit=10, window_seconds=300)
def generate():
    form = GenerateVideoForm()

    if form.validate_on_submit():
        raw_images = [file for file in form.images.data if file and file.filename]
        raw_video = form.video_file.data if form.video_file.data and form.video_file.data.filename else None
        raw_audio = form.audio_file.data if form.audio_file.data and form.audio_file.data.filename else None

        if not raw_images and not raw_video:
            flash("Upload at least one image or one video file.", "error")
            return render_template(
                "video/generate.html",
                title="Generate video",
                dashboard_shell=True,
                active_page="generate",
                form=form,
            )

        if len(raw_images) > current_app.config["MAX_IMAGES_PER_VIDEO"]:
            flash(f"You can upload up to {current_app.config['MAX_IMAGES_PER_VIDEO']} images per reel.", "error")
            return render_template(
                "video/generate.html",
                title="Generate video",
                dashboard_shell=True,
                active_page="generate",
                form=form,
            )

        for image in raw_images:
            if not is_allowed_file(image.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]):
                flash(f"Unsupported image type: {image.filename}", "error")
                return render_template("video/generate.html", title="Generate video", dashboard_shell=True, active_page="generate", form=form)

        if raw_video and not is_allowed_file(raw_video.filename, current_app.config["ALLOWED_VIDEO_EXTENSIONS"]):
            flash("Unsupported video type uploaded.", "error")
            return render_template("video/generate.html", title="Generate video", dashboard_shell=True, active_page="generate", form=form)

        if raw_audio and not is_allowed_file(raw_audio.filename, current_app.config["ALLOWED_AUDIO_EXTENSIONS"]):
            flash("Unsupported audio type uploaded.", "error")
            return render_template("video/generate.html", title="Generate video", dashboard_shell=True, active_page="generate", form=form)

        video = GeneratedVideo(
            user_id=current_user.id,
            title=form.title.data.strip(),
            topic=form.topic.data.strip(),
            script=(form.script.data or "").strip(),
            style=form.style.data,
            language=form.language.data,
            duration=form.duration.data,
            aspect_ratio=form.aspect_ratio.data,
            template=form.template.data,
            status="queued",
            storage_provider="local",
            source_asset_count=len(raw_images) + (1 if raw_video else 0),
        )
        db.session.add(video)
        db.session.commit()

        workspace = user_workspace(current_user.id, video.id)
        image_paths = [save_file(image, workspace / "images") for image in raw_images]
        video_path = save_file(raw_video, workspace / "video") if raw_video else None
        audio_path = save_file(raw_audio, workspace / "audio") if raw_audio else None

        register_uploaded_assets(video, image_paths=image_paths, video_path=video_path, audio_path=audio_path)
        queue_video_generation(
            video_id=video.id,
            user_id=current_user.id,
            workspace=workspace,
            image_paths=image_paths,
            video_path=video_path,
            audio_path=audio_path,
            tone=form.tone.data,
            caption_length=form.caption_length.data,
            emoji_enabled=form.emoji_enabled.data,
            cta_strength=form.cta_strength.data,
        )
        flash("Your project has been queued. We'll keep updating its status in the preview page.", "success")
        return redirect(url_for("video.preview", video_id=video.id))

    return render_template(
        "video/generate.html",
        title="Generate video",
        dashboard_shell=True,
        active_page="generate",
        form=form,
    )


@bp.route("/videos/<video_id>/preview", methods=["GET", "POST"])
@login_required
def preview(video_id):
    video = GeneratedVideo.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    caption_set = video.caption_set
    form = PostPreviewForm()

    accounts = SocialAccount.query.filter_by(user_id=current_user.id).order_by(SocialAccount.platform.asc()).all()
    form.social_account_id.choices = [("", "Select a connected account")] + [
        (account.id, f"{account.platform.title()} - {account.account_name}") for account in accounts
    ]

    if request.method == "GET" and caption_set:
        form.caption_text.data = caption_set.main_caption
        form.hashtags_text.data = caption_set.hashtags

    if request.method == "POST" and not video.is_ready:
        flash("This reel is still being generated. Wait until the status changes to ready before publishing.", "error")
        return redirect(url_for("video.preview", video_id=video.id))

    if form.validate_on_submit():
        action = request.form.get("action", "draft")
        social_account = None
        platform = None

        if action == "publish" and not current_user.can_publish_directly:
            flash("Direct publishing is a premium feature. Upgrade to lifetime access to unlock it.", "error")
            return redirect(url_for("billing.index"))
        if action == "schedule" and not current_user.can_schedule:
            flash("Scheduling is available on premium lifetime access. Upgrade to unlock it.", "error")
            return redirect(url_for("billing.index"))

        if form.social_account_id.data:
            social_account = SocialAccount.query.filter_by(
                id=form.social_account_id.data,
                user_id=current_user.id,
            ).first()
            if not social_account:
                flash("Selected social account was not found.", "error")
                return redirect(url_for("video.preview", video_id=video.id))
            platform = social_account.platform

        job = PostJob(
            user_id=current_user.id,
            video_id=video.id,
            social_account_id=social_account.id if social_account else None,
            caption_text=form.caption_text.data.strip(),
            hashtags_text=(form.hashtags_text.data or "").strip(),
            platform=platform,
            status="draft",
        )
        db.session.add(job)
        db.session.commit()

        if action == "publish":
            if not social_account:
                flash("Select a connected account before publishing.", "error")
                return redirect(url_for("video.preview", video_id=video.id))
            from app.services.social_service import publish_post_now

            try:
                publish_post_now(job)
                flash("Your content has been published.", "success")
                return redirect(url_for("history.index"))
            except Exception as exc:  # noqa: BLE001
                job.status = "failed"
                job.error_message = str(exc)
                db.session.commit()
                flash(f"Publishing failed: {exc}", "error")

        if action == "schedule":
            if not social_account:
                flash("Select a connected account before scheduling.", "error")
                return redirect(url_for("video.preview", video_id=video.id))
            if not form.scheduled_time.data:
                flash("Pick a date and time before scheduling.", "error")
                return redirect(url_for("video.preview", video_id=video.id))

            scheduled_at = form.scheduled_time.data
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            schedule_post(job, scheduled_at)
            flash("Your post has been scheduled.", "success")
            return redirect(url_for("scheduler.index"))

        flash("Draft saved to your post history.", "success")
        return redirect(url_for("history.index"))

    return render_template(
        "video/preview.html",
        title=f"Preview {video.title}",
        dashboard_shell=True,
        active_page="generate",
        video=video,
        caption_set=caption_set,
        connected_accounts=accounts,
        form=form,
    )


@bp.get("/videos/<video_id>/stream")
@login_required
def stream_video(video_id):
    video = GeneratedVideo.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    if not video.file_path:
        if video.file_url:
            return redirect(video.file_url)
        abort(404)
    absolute_path = absolute_upload_path(video.file_path)
    if not absolute_path.exists():
        if video.file_url:
            return redirect(video.file_url)
        abort(404)
    return send_file(absolute_path, mimetype="video/mp4", as_attachment=False, download_name=f"{video.title}.mp4")


@bp.get("/videos/<video_id>/thumbnail")
@login_required
def stream_thumbnail(video_id):
    video = GeneratedVideo.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    if not video.thumbnail_path:
        if video.thumbnail_url:
            return redirect(video.thumbnail_url)
        abort(404)
    absolute_path = absolute_upload_path(video.thumbnail_path)
    if not absolute_path.exists():
        if video.thumbnail_url:
            return redirect(video.thumbnail_url)
        abort(404)
    return send_file(absolute_path, mimetype="image/jpeg")


@bp.get("/videos/<video_id>/download")
@login_required
def download_video(video_id):
    video = GeneratedVideo.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    if not video.file_path:
        if video.file_url:
            return redirect(video.file_url)
        abort(404)
    absolute_path = absolute_upload_path(video.file_path)
    if not absolute_path.exists():
        if video.file_url:
            return redirect(video.file_url)
        abort(404)
    return send_file(absolute_path, mimetype="video/mp4", as_attachment=True, download_name=f"{video.title}.mp4")


@bp.get("/videos/<video_id>/status")
@login_required
def video_status(video_id):
    video = GeneratedVideo.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    return {
        "video_id": video.id,
        "status": video.status,
        "is_ready": video.is_ready,
        "error_message": video.error_message,
        "preview_url": url_for("video.preview", video_id=video.id),
        "download_url": url_for("video.download_video", video_id=video.id) if video.is_ready else None,
    }


@bp.post("/videos/<video_id>/delete")
@login_required
def delete_video(video_id):
    video = GeneratedVideo.query.filter_by(id=video_id, user_id=current_user.id).first_or_404()
    title = video.title
    db.session.delete(video)
    db.session.commit()
    remove_user_workspace(current_user.id, video_id)
    flash(f"Deleted project '{title}'.", "success")

    next_url = request.form.get("next") or url_for("history.index")
    return redirect(next_url)
