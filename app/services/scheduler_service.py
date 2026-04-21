from datetime import datetime, timezone

from app.extensions import db
from app.models import PostJob
from app.services.social_service import publish_post_now


def schedule_post(post_job, scheduled_time):
    post_job.scheduled_time = scheduled_time
    post_job.status = "pending"
    post_job.error_message = None
    db.session.commit()
    return post_job


def cancel_scheduled_post(post_job):
    post_job.status = "cancelled"
    post_job.error_message = None
    db.session.commit()
    return post_job


def process_due_jobs():
    now = datetime.now(timezone.utc)
    due_jobs = (
        PostJob.query.filter(
            PostJob.status == "pending",
            PostJob.scheduled_time.isnot(None),
            PostJob.scheduled_time <= now,
        )
        .order_by(PostJob.scheduled_time.asc())
        .all()
    )

    processed = 0
    for job in due_jobs:
        try:
            publish_post_now(job)
            processed += 1
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_message = str(exc)
            db.session.commit()
    return processed
