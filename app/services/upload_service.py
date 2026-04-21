import shutil
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


def ensure_upload_root():
    upload_root = Path(current_app.config["UPLOAD_ROOT"])
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root


def is_allowed_file(filename, allowed_extensions):
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in allowed_extensions


def user_workspace(user_id, video_id):
    root = ensure_upload_root()
    workspace = root / "users" / user_id / video_id
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def save_file(file_storage, destination_dir):
    Path(destination_dir).mkdir(parents=True, exist_ok=True)
    extension = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid4().hex}.{extension}"
    safe_name = secure_filename(filename)
    destination = Path(destination_dir) / safe_name
    file_storage.save(destination)
    return destination


def relative_upload_path(path):
    root = ensure_upload_root()
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def absolute_upload_path(relative_path):
    root = ensure_upload_root()
    return root / relative_path


def remove_user_workspace(user_id, video_id):
    workspace = ensure_upload_root() / "users" / str(user_id) / str(video_id)
    if workspace.exists() and workspace.is_dir():
        shutil.rmtree(workspace)
