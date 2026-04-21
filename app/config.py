import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


def _get_env_string(name, default=""):
    return os.getenv(name, default).strip()


def _get_env_bool(name, default=False):
    value = _get_env_string(name, "")
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _default_app_base_url():
    configured = _get_env_string("APP_BASE_URL", "")
    if configured:
        return configured.rstrip("/")

    render_url = _get_env_string("RENDER_EXTERNAL_URL", "")
    if render_url:
        return render_url.rstrip("/")

    return "http://127.0.0.1:5000"


def _default_upload_root():
    configured = _get_env_string("UPLOAD_ROOT", "")
    if configured:
        return Path(configured).expanduser()
    return BASE_DIR / "app" / "uploads"


class Config:
    APP_BASE_URL = _default_app_base_url()
    _HTTPS_ENABLED = APP_BASE_URL.startswith("https://") or _get_env_bool("RENDER", False)
    SECRET_KEY = _get_env_string("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(INSTANCE_DIR / 'vidsnapai.db').as_posix()}",
    ).strip()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PREFERRED_URL_SCHEME = "https" if _HTTPS_ENABLED else "http"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _HTTPS_ENABLED
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _HTTPS_ENABLED
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 1024 * 1024 * 200))
    UPLOAD_ROOT = _default_upload_root()
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "m4v"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a"}
    SCHEDULER_POLL_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_POLL_INTERVAL_SECONDS", "30"))
    MAX_IMAGES_PER_VIDEO = int(os.getenv("MAX_IMAGES_PER_VIDEO", "12"))
    MAX_SOCIAL_ACCOUNTS_PER_USER = int(os.getenv("MAX_SOCIAL_ACCOUNTS_PER_USER", "10"))
    LIFETIME_PLAN_PRICE_INR = int(os.getenv("LIFETIME_PLAN_PRICE_INR", "399"))
    LIFETIME_PLAN_CURRENCY = _get_env_string("LIFETIME_PLAN_CURRENCY", "INR").upper()
    RAZORPAY_KEY_ID = _get_env_string("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = _get_env_string("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = _get_env_string("RAZORPAY_WEBHOOK_SECRET", "")
    RAZORPAY_API_BASE_URL = _get_env_string("RAZORPAY_API_BASE_URL", "https://api.razorpay.com")
    CLOUDINARY_CLOUD_NAME = _get_env_string("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = _get_env_string("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = _get_env_string("CLOUDINARY_API_SECRET", "")
    CLOUDINARY_FOLDER = _get_env_string("CLOUDINARY_FOLDER", "vidsnapai")
    META_APP_ID = _get_env_string("META_APP_ID", "")
    META_APP_SECRET = _get_env_string("META_APP_SECRET", "")
    META_REDIRECT_URI = _get_env_string("META_REDIRECT_URI", "")
    META_API_VERSION = _get_env_string("META_API_VERSION", "v23.0")
    META_AUTH_BASE_URL = _get_env_string("META_AUTH_BASE_URL", "https://www.facebook.com")
    META_GRAPH_BASE_URL = _get_env_string("META_GRAPH_BASE_URL", "https://graph.facebook.com")
    META_OAUTH_STATE_TTL_SECONDS = int(os.getenv("META_OAUTH_STATE_TTL_SECONDS", "900"))
    META_SELECTION_TTL_SECONDS = int(os.getenv("META_SELECTION_TTL_SECONDS", "900"))
    META_REQUEST_TIMEOUT_SECONDS = int(os.getenv("META_REQUEST_TIMEOUT_SECONDS", "20"))
    SOCIAL_TOKEN_ENCRYPTION_SECRET = _get_env_string("SOCIAL_TOKEN_ENCRYPTION_SECRET", SECRET_KEY)
    FREE_EXPORT_WATERMARK_TEXT = _get_env_string("FREE_EXPORT_WATERMARK_TEXT", "VidSnapAI Free")
    FFMPEG_FONT_PATH = _get_env_string("FFMPEG_FONT_PATH", "")
    META_SCOPES_INSTAGRAM = [
        "pages_show_list",
        "pages_read_engagement",
        "instagram_basic",
        "instagram_content_publish",
        "business_management",
    ]
    META_SCOPES_FACEBOOK = [
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "pages_manage_metadata",
        "business_management",
    ]
