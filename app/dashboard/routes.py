from datetime import datetime, timezone

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import GeneratedVideo, PostJob, SocialAccount


bp = Blueprint("dashboard", __name__, url_prefix="/app")


@bp.route("/")
@login_required
def root():
    return redirect(url_for("dashboard.index"))


@bp.route("/dashboard")
@login_required
def index():
    videos = (
        GeneratedVideo.query.filter_by(user_id=current_user.id)
        .order_by(GeneratedVideo.created_at.desc())
        .limit(4)
        .all()
    )
    accounts = (
        SocialAccount.query.filter_by(user_id=current_user.id)
        .order_by(SocialAccount.created_at.desc())
        .limit(4)
        .all()
    )
    jobs = (
        PostJob.query.filter_by(user_id=current_user.id)
        .order_by(PostJob.created_at.desc())
        .limit(6)
        .all()
    )

    scheduled_count = PostJob.query.filter_by(user_id=current_user.id, status="pending").count()
    published_count = PostJob.query.filter_by(user_id=current_user.id, status="published").count()
    video_count = GeneratedVideo.query.filter_by(user_id=current_user.id).count()
    connected_count = SocialAccount.query.filter_by(user_id=current_user.id, status="connected").count()

    upcoming_job = (
        PostJob.query.filter(
            PostJob.user_id == current_user.id,
            PostJob.status == "pending",
            PostJob.scheduled_time.isnot(None),
            PostJob.scheduled_time >= datetime.now(timezone.utc),
        )
        .order_by(PostJob.scheduled_time.asc())
        .first()
    )

    return render_template(
        "dashboard/index.html",
        title="Dashboard",
        dashboard_shell=True,
        active_page="dashboard",
        stats={
            "videos": video_count,
            "accounts": connected_count,
            "published": published_count,
            "scheduled": scheduled_count,
        },
        recent_videos=videos,
        social_accounts=accounts,
        recent_jobs=jobs,
        upcoming_job=upcoming_job,
    )
