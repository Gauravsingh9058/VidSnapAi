import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


class TokenStoreError(RuntimeError):
    pass


def encrypt_token(raw_value):
    if raw_value is None:
        return None
    return _fernet().encrypt(raw_value.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_value):
    if encrypted_value is None:
        return None
    try:
        return _fernet().decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenStoreError("Unable to decrypt stored token.") from exc


def _fernet():
    seed = current_app.config["SOCIAL_TOKEN_ENCRYPTION_SECRET"].encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)
