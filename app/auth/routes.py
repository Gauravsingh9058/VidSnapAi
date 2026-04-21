from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.forms import ForgotPasswordForm, LoginForm, SignupForm
from app.extensions import db
from app.models import User
from app.utils.rate_limit import rate_limit


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/signup", methods=["GET", "POST"])
@rate_limit("signup", limit=12, window_seconds=300)
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing_user:
            flash("An account with that email already exists.", "error")
        else:
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.lower().strip(),
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Your VidSnapAI workspace is ready.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template(
        "auth/signup.html",
        title="Create your account",
        form=form,
        auth_mode="signup",
    )


@bp.route("/login", methods=["GET", "POST"])
@rate_limit("login", limit=20, window_seconds=300)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if not user or not user.check_password(form.password.data):
            flash("Invalid email or password.", "error")
        else:
            login_user(user, remember=True)
            flash("Welcome back to your dashboard.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template(
        "auth/login.html",
        title="Welcome back",
        form=form,
        auth_mode="login",
    )


@bp.route("/forgot-password", methods=["GET", "POST"])
@rate_limit("forgot-password", limit=8, window_seconds=600)
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        flash("If that email exists, a reset link would be sent in the real production flow.", "success")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/forgot_password.html",
        title="Reset password",
        form=form,
        auth_mode="forgot-password",
    )


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("marketing.landing"))
