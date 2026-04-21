from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import PostJob
from app.services.scheduler_service import cancel_scheduled_post, schedule_post


bp = Blueprint("scheduler", __name__, url_prefix="/app/scheduled")


@bp.route("/")
@login_required
def index():
    scheduled_jobs = (
        PostJob.query.filter_by(user_id=current_user.id)
        .filter(PostJob.status.in_(["pending", "publishing", "published", "failed", "cancelled"]))
        .order_by(PostJob.created_at.desc())
        .all()
    )
    return render_template(
        "scheduler/index.html",
        title="Scheduled posts",
        dashboard_shell=True,
        active_page="scheduled",
        jobs=scheduled_jobs,
        now=datetime.now(timezone.utc),
    )


@bp.post("/<job_id>/reschedule")
@login_required
def reschedule(job_id):
    job = PostJob.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    new_time = request.form.get("scheduled_time")
    if not new_time:
        flash("Choose a new schedule time.", "error")
        return redirect(url_for("scheduler.index"))

    try:
        scheduled_at = datetime.fromisoformat(new_time)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        schedule_post(job, scheduled_at)
        flash("Scheduled time updated.", "success")
    except ValueError:
        flash("Invalid date format supplied.", "error")
    return redirect(url_for("scheduler.index"))


@bp.post("/<job_id>/cancel")
@login_required
def cancel(job_id):
    job = PostJob.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    cancel_scheduled_post(job)
    flash("Scheduled job cancelled.", "success")
    return redirect(url_for("scheduler.index"))
