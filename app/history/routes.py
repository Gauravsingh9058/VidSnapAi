from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models import GeneratedVideo, PostJob


bp = Blueprint("history", __name__, url_prefix="/app/history")


@bp.route("/")
@login_required
def index():
    videos = (
        GeneratedVideo.query.filter_by(user_id=current_user.id)
        .order_by(GeneratedVideo.created_at.desc())
        .all()
    )
    jobs = (
        PostJob.query.filter_by(user_id=current_user.id)
        .order_by(PostJob.created_at.desc())
        .all()
    )

    return render_template(
        "history/index.html",
        title="History",
        dashboard_shell=True,
        active_page="history",
        videos=videos,
        jobs=jobs,
    )
