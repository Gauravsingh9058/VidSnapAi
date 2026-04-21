from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from app.extensions import db
from app.models import SocialAccount, User
from app.settings.forms import DeleteAccountForm, NotificationForm, PasswordUpdateForm, ProfileForm


bp = Blueprint("settings", __name__, url_prefix="/app/settings")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    profile_form = ProfileForm(prefix="profile")
    password_form = PasswordUpdateForm(prefix="password")
    notification_form = NotificationForm(prefix="notifications")
    delete_form = DeleteAccountForm(prefix="delete")

    if request.method == "GET":
        profile_form.name.data = current_user.name
        profile_form.email.data = current_user.email
        notification_form.notify_product_updates.data = current_user.notify_product_updates
        notification_form.notify_scheduled_posts.data = current_user.notify_scheduled_posts
        notification_form.notify_failures.data = current_user.notify_failures

    form_name = request.form.get("form_name")

    if form_name == "profile" and profile_form.validate_on_submit():
        existing_email_owner = User.query.filter(
            User.email == profile_form.email.data.lower().strip(),
            User.id != current_user.id,
        ).first()
        if existing_email_owner:
            flash("That email is already used by another account.", "error")
            return redirect(url_for("settings.index"))
        current_user.name = profile_form.name.data.strip()
        current_user.email = profile_form.email.data.lower().strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("settings.index"))

    if form_name == "password" and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Your current password is incorrect.", "error")
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for("settings.index"))

    if form_name == "notifications" and notification_form.validate_on_submit():
        current_user.notify_product_updates = notification_form.notify_product_updates.data
        current_user.notify_scheduled_posts = notification_form.notify_scheduled_posts.data
        current_user.notify_failures = notification_form.notify_failures.data
        db.session.commit()
        flash("Notification preferences saved.", "success")
        return redirect(url_for("settings.index"))

    if form_name == "delete" and delete_form.validate_on_submit():
        if delete_form.confirm_text.data != "DELETE":
            flash("Type DELETE exactly to remove the account.", "error")
        else:
            logout_user()
            db.session.delete(current_user)
            db.session.commit()
            flash("Your account has been deleted.", "success")
            return redirect(url_for("marketing.landing"))

    reconnect_accounts = SocialAccount.query.filter_by(user_id=current_user.id).order_by(SocialAccount.created_at.desc()).all()
    return render_template(
        "settings/index.html",
        title="Settings",
        dashboard_shell=True,
        active_page="settings",
        profile_form=profile_form,
        password_form=password_form,
        notification_form=notification_form,
        delete_form=delete_form,
        reconnect_accounts=reconnect_accounts,
    )
