import hashlib
import hmac
import time
from pathlib import Path

import requests
from flask import current_app


class StorageError(RuntimeError):
    pass


def storage_is_configured():
    return all(
        [
            current_app.config["CLOUDINARY_CLOUD_NAME"],
            current_app.config["CLOUDINARY_API_KEY"],
            current_app.config["CLOUDINARY_API_SECRET"],
        ]
    )


def active_storage_provider():
    return "cloudinary" if storage_is_configured() else "local"


def upload_to_storage(file_path, folder, public_id=None, resource_type="auto"):
    if not storage_is_configured():
        return {
            "provider": "local",
            "public_url": None,
        }

    timestamp = int(time.time())
    cloud_name = current_app.config["CLOUDINARY_CLOUD_NAME"]
    api_key = current_app.config["CLOUDINARY_API_KEY"]
    api_secret = current_app.config["CLOUDINARY_API_SECRET"]
    cloudinary_folder = current_app.config["CLOUDINARY_FOLDER"].strip("/")
    effective_folder = "/".join([segment for segment in [cloudinary_folder, folder.strip("/")] if segment])

    params = {
        "folder": effective_folder,
        "timestamp": timestamp,
    }
    if public_id:
        params["public_id"] = public_id

    params["signature"] = _cloudinary_signature(params, api_secret)
    upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"
    with Path(file_path).open("rb") as media_file:
        response = requests.post(
            upload_url,
            data={**params, "api_key": api_key},
            files={"file": media_file},
            timeout=60,
        )

    if response.status_code >= 400:
        raise StorageError("Cloudinary upload failed while storing project media.")

    payload = response.json()
    return {
        "provider": "cloudinary",
        "public_url": payload.get("secure_url") or payload.get("url"),
    }


def _cloudinary_signature(params, api_secret):
    serialized = "&".join(f"{key}={value}" for key, value in sorted(params.items()) if value not in {None, ""})
    digest = hmac.new(api_secret.encode("utf-8"), serialized.encode("utf-8"), hashlib.sha1)
    return digest.hexdigest()
