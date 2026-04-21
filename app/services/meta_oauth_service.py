import hashlib
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from flask import current_app, has_request_context, url_for

from app.extensions import db
from app.models import OAuthState, PendingSocialAccountSelection, SocialAccount
from app.services.token_store import decrypt_token, encrypt_token


logger = logging.getLogger(__name__)
APP_SECRET_TOKEN_PREFIXES = ("EAA", "EAA", "EAAB", "EAAC", "EAAD", "EAAG", "EAAS")


class SocialConnectionError(RuntimeError):
    def __init__(self, message, status="error"):
        super().__init__(message)
        self.message = message
        self.status = status


class MetaConfigurationError(SocialConnectionError):
    pass


class StateValidationError(SocialConnectionError):
    pass


class TokenExchangeError(SocialConnectionError):
    pass


class NoEligibleAccountsError(SocialConnectionError):
    pass


class AssetSelectionError(SocialConnectionError):
    pass


def meta_is_configured():
    return not _meta_configuration_errors()


def get_meta_redirect_uri():
    configured = current_app.config["META_REDIRECT_URI"].strip()
    if configured:
        return configured
    if has_request_context():
        return url_for("social.meta_callback", _external=True)
    base_url = current_app.config["APP_BASE_URL"].rstrip("/")
    return f"{base_url}{url_for('social.meta_callback')}"


def build_meta_auth_url(platform, user_id, social_account_id=None):
    _require_meta_configuration()

    state_token = secrets.token_urlsafe(32)
    state_hash = hashlib.sha256(state_token.encode("utf-8")).hexdigest()
    oauth_state = OAuthState(
        user_id=user_id,
        provider="meta",
        platform=platform,
        state_hash=state_hash,
        redirect_uri=get_meta_redirect_uri(),
        social_account_id=social_account_id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=current_app.config["META_OAUTH_STATE_TTL_SECONDS"]),
    )
    db.session.add(oauth_state)
    db.session.commit()

    params = {
        "client_id": current_app.config["META_APP_ID"],
        "redirect_uri": oauth_state.redirect_uri,
        "state": state_token,
        "response_type": "code",
        "scope": ",".join(_scopes_for_platform(platform)),
    }
    auth_url = f"{current_app.config['META_AUTH_BASE_URL'].rstrip('/')}/{current_app.config['META_API_VERSION']}/dialog/oauth?{urlencode(params)}"
    return auth_url


def validate_oauth_state(state, user_id):
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    oauth_state = OAuthState.query.filter_by(
        state_hash=state_hash,
        user_id=user_id,
        provider="meta",
    ).first()

    if not oauth_state or oauth_state.is_used or oauth_state.is_expired:
        raise StateValidationError("Your Meta connection session is invalid or expired. Start the connection again.", status="needs reconnect")

    oauth_state.used_at = datetime.now(timezone.utc)
    db.session.commit()
    return oauth_state


def exchange_code_for_token(code):
    _require_meta_configuration()

    redirect_uri = get_meta_redirect_uri()
    token_url = _graph_url("/oauth/access_token")

    short_response = requests.get(
        token_url,
        params={
            "client_id": current_app.config["META_APP_ID"],
            "client_secret": current_app.config["META_APP_SECRET"],
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=current_app.config["META_REQUEST_TIMEOUT_SECONDS"],
    )
    if short_response.status_code >= 400:
        logger.warning("Meta short-lived token exchange failed with status %s", short_response.status_code)
        raise TokenExchangeError("Meta token exchange failed. Double-check your app credentials, redirect URI, and permissions.")

    short_data = short_response.json()
    short_token = short_data.get("access_token")
    if not short_token:
        raise TokenExchangeError("Meta did not return an access token.")

    long_response = requests.get(
        token_url,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": current_app.config["META_APP_ID"],
            "client_secret": current_app.config["META_APP_SECRET"],
            "fb_exchange_token": short_token,
        },
        timeout=current_app.config["META_REQUEST_TIMEOUT_SECONDS"],
    )
    if long_response.status_code >= 400:
        logger.warning("Meta long-lived token exchange failed with status %s", long_response.status_code)
        raise TokenExchangeError("Meta long-lived token exchange failed. Check whether the app is configured for the requested permissions.")

    long_data = long_response.json()
    long_token = long_data.get("access_token")
    expires_in = long_data.get("expires_in")
    if not long_token:
        raise TokenExchangeError("Meta did not return a long-lived token.")

    granted_scopes = fetch_granted_scopes(long_token)
    expiry = None
    if expires_in:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    return {
        "user_access_token": long_token,
        "token_expiry": expiry,
        "granted_scopes": granted_scopes,
    }


def fetch_instagram_accounts(user_access_token):
    assets = []
    for page in _fetch_pages_with_meta_data(user_access_token):
        ig_account = page.get("instagram_business_account")
        if not ig_account:
            continue

        username = ig_account.get("username")
        account_name = ig_account.get("name") or username or page.get("name")
        assets.append(
            {
                "asset_key": f"ig::{ig_account['id']}",
                "platform": "instagram",
                "account_id": ig_account["id"],
                "account_name": account_name,
                "username": username,
                "page_id": page.get("id"),
                "page_name": page.get("name"),
                "access_token": page.get("access_token"),
                "metadata": {
                    "page_name": page.get("name"),
                    "page_tasks": page.get("tasks", []),
                    "picture": ((page.get("picture") or {}).get("data") or {}).get("url"),
                    "instagram_business_account": ig_account,
                },
            }
        )

    if not assets:
        raise NoEligibleAccountsError(
            "No eligible Instagram professional accounts were found. Make sure the Instagram professional account is linked to a Facebook Page that your Meta user can access.",
            status="needs reconnect",
        )
    return assets


def fetch_facebook_pages(user_access_token):
    assets = []
    for page in _fetch_pages_with_meta_data(user_access_token):
        assets.append(
            {
                "asset_key": f"fb::{page['id']}",
                "platform": "facebook",
                "account_id": page["id"],
                "account_name": page["name"],
                "username": None,
                "page_id": page["id"],
                "page_name": page["name"],
                "access_token": page.get("access_token"),
                "metadata": {
                    "page_tasks": page.get("tasks", []),
                    "picture": ((page.get("picture") or {}).get("data") or {}).get("url"),
                },
            }
        )

    if not assets:
        raise NoEligibleAccountsError(
            "No Facebook Pages were found for this Meta login. Make sure the user can access at least one Page and granted the required permissions.",
            status="needs reconnect",
        )
    return assets


def create_pending_selection(user_id, platform, assets, token_bundle, reconnect_social_account_id=None):
    selection = PendingSocialAccountSelection(
        user_id=user_id,
        platform=platform,
        encrypted_user_token=encrypt_token(token_bundle["user_access_token"]),
        token_expiry=token_bundle.get("token_expiry"),
        granted_scopes=json.dumps(token_bundle.get("granted_scopes", [])),
        raw_assets_json=json.dumps(_sanitize_assets_for_selection(assets)),
        reconnect_social_account_id=reconnect_social_account_id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=current_app.config["META_SELECTION_TTL_SECONDS"]),
    )
    db.session.add(selection)
    db.session.commit()
    return selection


def get_pending_selection_for_user(selection_id, user_id):
    selection = PendingSocialAccountSelection.query.filter_by(id=selection_id, user_id=user_id).first()
    if not selection or selection.is_expired:
        raise AssetSelectionError("This account selection link has expired. Start the connection again.", status="needs reconnect")
    return selection


def resolve_pending_selection(selection_id, user_id, asset_key):
    selection = get_pending_selection_for_user(selection_id, user_id)
    user_token = decrypt_token(selection.encrypted_user_token)
    token_bundle = {
        "user_access_token": user_token,
        "token_expiry": selection.token_expiry,
        "granted_scopes": json.loads(selection.granted_scopes) if selection.granted_scopes else [],
    }
    assets = _discover_assets(selection.platform, user_token)
    matched_asset = next((asset for asset in assets if asset["asset_key"] == asset_key), None)
    if not matched_asset:
        raise AssetSelectionError("The selected Meta asset is no longer available. Reconnect and try again.", status="needs reconnect")

    account = save_connected_account(
        user_id=user_id,
        platform=selection.platform,
        asset=matched_asset,
        token_bundle=token_bundle,
        reconnect_social_account_id=selection.reconnect_social_account_id,
    )
    db.session.delete(selection)
    db.session.commit()
    return account


def save_connected_account(user_id, platform, asset, token_bundle, reconnect_social_account_id=None):
    existing_account = None
    if reconnect_social_account_id:
        existing_account = SocialAccount.query.filter_by(id=reconnect_social_account_id, user_id=user_id).first()
    if not existing_account:
        existing_account = SocialAccount.query.filter_by(
            user_id=user_id,
            platform=platform,
            account_id=asset["account_id"],
        ).first()

    if existing_account is None:
        existing_account = SocialAccount(user_id=user_id, platform=platform, account_id=asset["account_id"])
        db.session.add(existing_account)

    existing_account.platform = platform
    existing_account.account_id = asset["account_id"]
    existing_account.account_name = asset["account_name"]
    existing_account.username = asset.get("username")
    existing_account.page_id = asset.get("page_id")
    existing_account.access_token = encrypt_token(asset.get("access_token") or token_bundle["user_access_token"])
    existing_account.refresh_token = encrypt_token(token_bundle["user_access_token"])
    existing_account.token_expiry = token_bundle.get("token_expiry")
    existing_account.status = "connected"
    existing_account.meta_scopes = json.dumps(token_bundle.get("granted_scopes", []))
    existing_account.raw_metadata_json = json.dumps(asset.get("metadata", {}))
    existing_account.last_error = None
    db.session.commit()
    return existing_account


def refresh_social_account(account):
    try:
        seed_token = decrypt_token(account.refresh_token or account.access_token)
    except Exception as exc:  # noqa: BLE001
        account.status = "needs reconnect"
        account.last_error = str(exc)
        db.session.commit()
        raise SocialConnectionError("The stored Meta token could not be decrypted. Reconnect the account.", status="needs reconnect") from exc

    token_bundle = exchange_existing_long_lived_token(seed_token)
    assets = _discover_assets(account.platform, token_bundle["user_access_token"])
    matched_asset = next(
        (
            asset
            for asset in assets
            if asset["account_id"] == account.account_id or (account.page_id and asset.get("page_id") == account.page_id)
        ),
        None,
    )
    if not matched_asset:
        account.status = "needs reconnect"
        account.last_error = "The previously connected Meta asset is no longer accessible."
        db.session.commit()
        raise SocialConnectionError("This Meta asset is no longer accessible. Reconnect the account.", status="needs reconnect")

    return save_connected_account(
        user_id=account.user_id,
        platform=account.platform,
        asset=matched_asset,
        token_bundle=token_bundle,
        reconnect_social_account_id=account.id,
    )


def disconnect_social_account(account):
    for post_job in account.post_jobs:
        post_job.social_account_id = None
    db.session.delete(account)
    db.session.commit()


def sync_social_account(account):
    return refresh_social_account(account)


def get_connected_accounts_for_user(user_id):
    return SocialAccount.query.filter_by(user_id=user_id).order_by(SocialAccount.updated_at.desc()).all()


def fetch_granted_scopes(user_access_token):
    try:
        response = _graph_get("/me/permissions", user_access_token, params={})
        permissions = response.get("data", [])
        return [item["permission"] for item in permissions if item.get("status") == "granted"]
    except SocialConnectionError:
        return []


def exchange_existing_long_lived_token(existing_token):
    _require_meta_configuration()
    response = requests.get(
        _graph_url("/oauth/access_token"),
        params={
            "grant_type": "fb_exchange_token",
            "client_id": current_app.config["META_APP_ID"],
            "client_secret": current_app.config["META_APP_SECRET"],
            "fb_exchange_token": existing_token,
        },
        timeout=current_app.config["META_REQUEST_TIMEOUT_SECONDS"],
    )
    if response.status_code >= 400:
        logger.warning("Meta token refresh failed with status %s", response.status_code)
        raise SocialConnectionError("Meta rejected the refresh request. Reconnect the account to continue.", status="expired")
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise SocialConnectionError("Meta did not return a refreshed token.", status="expired")
    expires_in = data.get("expires_in")
    expiry = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in)) if expires_in else None
    return {
        "user_access_token": access_token,
        "token_expiry": expiry,
        "granted_scopes": fetch_granted_scopes(access_token),
    }


def _discover_assets(platform, user_access_token):
    if platform == "instagram":
        return fetch_instagram_accounts(user_access_token)
    if platform == "facebook":
        return fetch_facebook_pages(user_access_token)
    raise SocialConnectionError(f"Unsupported platform '{platform}'.")


def _fetch_pages_with_meta_data(user_access_token):
    response = _graph_get(
        "/me/accounts",
        user_access_token,
        params={
            "fields": "id,name,access_token,tasks,picture{url},instagram_business_account{id,username,name}",
        },
    )
    return response.get("data", [])


def _sanitize_assets_for_selection(assets):
    return [
        {
            "asset_key": asset["asset_key"],
            "platform": asset["platform"],
            "account_id": asset["account_id"],
            "account_name": asset["account_name"],
            "username": asset.get("username"),
            "page_id": asset.get("page_id"),
            "page_name": asset.get("page_name"),
        }
        for asset in assets
    ]


def _graph_get(path, access_token, params):
    response = requests.get(
        _graph_url(path),
        params={"access_token": access_token, **params},
        timeout=current_app.config["META_REQUEST_TIMEOUT_SECONDS"],
    )
    if response.status_code >= 400:
        _raise_meta_error(response)
    return response.json()


def _raise_meta_error(response):
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    error = payload.get("error", {})
    message = error.get("message") or "Meta returned an error."
    code = error.get("code")
    logger.warning("Meta API error status=%s code=%s message=%s", response.status_code, code, message)
    lowered = message.lower()
    if "permission" in lowered or code == 10:
        raise SocialConnectionError("Meta did not grant all required permissions. Check your app review status and selected scopes.", status="needs reconnect")
    if "token" in lowered or code in {190, 102}:
        raise SocialConnectionError("The Meta token is invalid or expired. Reconnect the account.", status="expired")
    raise SocialConnectionError("Meta request failed while discovering accounts. Review your app configuration and permissions.", status="error")


def _graph_url(path):
    return f"{current_app.config['META_GRAPH_BASE_URL'].rstrip('/')}/{current_app.config['META_API_VERSION']}{path}"


def _scopes_for_platform(platform):
    if platform == "instagram":
        return current_app.config["META_SCOPES_INSTAGRAM"]
    if platform == "facebook":
        return current_app.config["META_SCOPES_FACEBOOK"]
    raise MetaConfigurationError(f"Unsupported platform '{platform}'.")


def _require_meta_configuration():
    errors = _meta_configuration_errors()
    if errors:
        raise MetaConfigurationError(" ".join(errors))


def _meta_configuration_errors():
    errors = []
    app_id = current_app.config["META_APP_ID"].strip()
    app_secret = current_app.config["META_APP_SECRET"].strip()

    if not app_id:
        errors.append(
            "META_APP_ID is missing. Add the numeric App ID from Meta App Dashboard > App Settings > Basic."
        )
    elif not re.fullmatch(r"\d{8,32}", app_id):
        errors.append(
            "META_APP_ID must be the numeric App ID from Meta App Dashboard > App Settings > Basic."
        )

    if not app_secret:
        errors.append(
            "META_APP_SECRET is missing. Add the App Secret from Meta App Dashboard > App Settings > Basic."
        )
    elif app_secret.startswith(APP_SECRET_TOKEN_PREFIXES):
        errors.append(
            "META_APP_SECRET looks like a Meta access token, not an App Secret. Copy the App Secret from Meta App Dashboard > App Settings > Basic."
        )

    if not get_meta_redirect_uri():
        errors.append(
            "META_REDIRECT_URI or APP_BASE_URL is required so Meta can return to your app after login."
        )

    if not current_app.config["SOCIAL_TOKEN_ENCRYPTION_SECRET"].strip():
        errors.append(
            "SOCIAL_TOKEN_ENCRYPTION_SECRET is missing. Add a long random secret before connecting accounts."
        )

    return errors
