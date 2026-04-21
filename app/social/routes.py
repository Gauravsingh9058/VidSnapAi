from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import SocialAccount
from app.services.meta_oauth_service import (
    AssetSelectionError,
    NoEligibleAccountsError,
    SocialConnectionError,
    StateValidationError,
    build_meta_auth_url,
    create_pending_selection,
    exchange_code_for_token,
    fetch_facebook_pages,
    fetch_instagram_accounts,
    get_connected_accounts_for_user,
    get_pending_selection_for_user,
    meta_is_configured,
    refresh_social_account,
    resolve_pending_selection,
    save_connected_account,
    validate_oauth_state,
)
from app.services.social_service import disconnect_social_account
from app.social.forms import SelectSocialAccountForm


bp = Blueprint("social", __name__, url_prefix="/app/social-accounts")


@bp.route("/", methods=["GET"])
@login_required
def index():
    accounts = get_connected_accounts_for_user(current_user.id)
    instagram_accounts = [account for account in accounts if account.platform == "instagram"]
    facebook_accounts = [account for account in accounts if account.platform == "facebook"]

    return render_template(
        "social/accounts.html",
        title="Social accounts",
        dashboard_shell=True,
        active_page="accounts",
        accounts=accounts,
        instagram_accounts=instagram_accounts,
        facebook_accounts=facebook_accounts,
        meta_configured=meta_is_configured(),
        social_account_limit=current_user.account_limit(current_app.config),
    )


@bp.get("/connect/<platform>")
@login_required
def connect(platform):
    if platform not in {"instagram", "facebook"}:
        flash("Unsupported social platform.", "error")
        return redirect(url_for("social.index"))

    accounts = get_connected_accounts_for_user(current_user.id)
    if len(accounts) >= current_user.account_limit(current_app.config):
        flash("You have reached the connected account limit for your lifetime plan.", "error")
        return redirect(url_for("social.index"))

    try:
        auth_url = build_meta_auth_url(platform=platform, user_id=current_user.id)
        return redirect(auth_url)
    except SocialConnectionError as exc:
        flash(exc.message, "error")
        return redirect(url_for("social.index"))


@bp.get("/callback/meta")
@login_required
def meta_callback():
    if request.args.get("error"):
        error_description = request.args.get("error_description") or "Meta access was denied or cancelled before account access was granted."
        flash(error_description, "error")
        return redirect(url_for("social.index"))

    state = request.args.get("state")
    code = request.args.get("code")
    if not state or not code:
        flash("Meta callback did not include the required authorization data.", "error")
        return redirect(url_for("social.index"))

    try:
        oauth_state = validate_oauth_state(state=state, user_id=current_user.id)
        token_bundle = exchange_code_for_token(code)
        assets = (
            fetch_instagram_accounts(token_bundle["user_access_token"])
            if oauth_state.platform == "instagram"
            else fetch_facebook_pages(token_bundle["user_access_token"])
        )

        if len(assets) == 1:
            account = save_connected_account(
                user_id=current_user.id,
                platform=oauth_state.platform,
                asset=assets[0],
                token_bundle=token_bundle,
                reconnect_social_account_id=oauth_state.social_account_id,
            )
            flash(f"{account.platform.title()} account connected successfully.", "success")
            return redirect(url_for("social.index"))

        selection = create_pending_selection(
            user_id=current_user.id,
            platform=oauth_state.platform,
            assets=assets,
            token_bundle=token_bundle,
            reconnect_social_account_id=oauth_state.social_account_id,
        )
        flash("Choose which Meta asset you want to connect.", "info")
        return redirect(url_for("social.choose_account", selection_id=selection.id))
    except (StateValidationError, NoEligibleAccountsError, SocialConnectionError) as exc:
        flash(exc.message, "error")
    return redirect(url_for("social.index"))


@bp.route("/select/<selection_id>", methods=["GET"])
@login_required
def choose_account(selection_id):
    try:
        selection = get_pending_selection_for_user(selection_id, current_user.id)
    except AssetSelectionError as exc:
        flash(exc.message, "error")
        return redirect(url_for("social.index"))

    form = SelectSocialAccountForm()
    form.apply_assets(selection)

    return render_template(
        "social/select_account.html",
        title="Choose account",
        dashboard_shell=True,
        active_page="accounts",
        selection=selection,
        form=form,
    )


@bp.post("/select-account")
@login_required
def select_account():
    form = SelectSocialAccountForm()
    try:
        selection = get_pending_selection_for_user(request.form.get("selection_id", ""), current_user.id)
    except AssetSelectionError as exc:
        flash(exc.message, "error")
        return redirect(url_for("social.index"))
    form.apply_assets(selection)

    if not form.validate_on_submit():
        flash("Choose a Meta asset before saving the connection.", "error")
        return render_template(
            "social/select_account.html",
            title="Choose account",
            dashboard_shell=True,
            active_page="accounts",
            selection=selection,
            form=form,
        )

    try:
        account = resolve_pending_selection(
            selection_id=form.selection_id.data,
            user_id=current_user.id,
            asset_key=form.asset_key.data,
        )
        flash(f"{account.platform.title()} account connected successfully.", "success")
        return redirect(url_for("social.index"))
    except (AssetSelectionError, SocialConnectionError) as exc:
        flash(exc.message, "error")
        return redirect(url_for("social.index"))


@bp.post("/<account_id>/disconnect")
@login_required
def disconnect(account_id):
    account = SocialAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    disconnect_social_account(account)
    flash("Social account disconnected and removed from your workspace.", "success")
    return redirect(url_for("social.index"))


@bp.post("/<account_id>/refresh")
@login_required
def refresh(account_id):
    account = SocialAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    try:
        refresh_social_account(account)
        flash("Meta account refreshed successfully.", "success")
    except SocialConnectionError as exc:
        flash(exc.message, "error")
    return redirect(url_for("social.index"))


@bp.post("/<account_id>/reconnect")
@login_required
def reconnect(account_id):
    account = SocialAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    try:
        auth_url = build_meta_auth_url(platform=account.platform, user_id=current_user.id, social_account_id=account.id)
        return redirect(auth_url)
    except SocialConnectionError as exc:
        flash(exc.message, "error")
        return redirect(url_for("social.index"))
