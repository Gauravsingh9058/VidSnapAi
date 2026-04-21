from datetime import datetime, timezone

from app.extensions import db
from app.models import PostJob
from app.services.meta_oauth_service import (
    disconnect_social_account as delete_social_account,
    get_connected_accounts_for_user,
    refresh_social_account,
    save_connected_account,
    sync_social_account,
)


class MetaPublisher:
    def publish_post_now(self, post_job):
        account = post_job.social_account
        if not account:
            raise RuntimeError("Connected social account required before publishing.")
        if account.status != "connected":
            raise RuntimeError("The selected social account needs reconnecting before publishing.")
        if account.token_expiry and account.token_expiry <= datetime.now(timezone.utc):
            account.status = "expired"
            db.session.commit()
            raise RuntimeError("The selected social account token has expired. Refresh or reconnect it first.")

        post_job.status = "published"
        post_job.published_time = datetime.now(timezone.utc)
        post_job.error_message = None
        return post_job


publisher = MetaPublisher()


def publish_post_now(post_job: PostJob):
    post_job.status = "publishing"
    db.session.flush()
    publisher.publish_post_now(post_job)
    db.session.commit()
    return post_job


def disconnect_social_account(account):
    delete_social_account(account)


__all__ = [
    "disconnect_social_account",
    "get_connected_accounts_for_user",
    "publish_post_now",
    "refresh_social_account",
    "save_connected_account",
    "sync_social_account",
]
