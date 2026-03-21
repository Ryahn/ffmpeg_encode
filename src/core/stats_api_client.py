"""Upload lifetime encoding totals to the ffmpeg-encode.com stats API."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Optional

from storage import get_lifetime_totals
from utils.config import config
from utils.logger import logger

_JWT_LOCK = threading.Lock()
_jwt_token: Optional[str] = None
_jwt_fetched_at: float = 0.0

JWT_MAX_AGE_SEC = 23 * 3600
REQUEST_TIMEOUT_SEC = 10


def _normalize_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if u.endswith("/api"):
        u = u[:-4].rstrip("/")
    return u


def effective_app_key() -> str:
    env = os.environ.get("FFMPEG_ENCODE_APP_KEY", "").strip()
    if env:
        return env
    return (config.get_stats_api_app_key() or "").strip()


def _post_json(url: str, payload: dict, headers: Optional[dict] = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp else b""
        return e.code, body
    except urllib.error.URLError as e:
        raise RuntimeError(str(e.reason)) from e


def _fetch_token(base: str, app_key: str) -> str:
    url = f"{base}/api/auth/token"
    status, body = _post_json(url, {"app_key": app_key})
    if status != 200:
        raise RuntimeError(f"auth HTTP {status}")
    obj = json.loads(body.decode("utf-8"))
    token = obj.get("access_token")
    if not token:
        raise RuntimeError("auth response missing access_token")
    return str(token)


def _get_bearer_token(base: str, app_key: str) -> str:
    global _jwt_token, _jwt_fetched_at
    now = time.time()
    with _JWT_LOCK:
        if _jwt_token and (now - _jwt_fetched_at) < JWT_MAX_AGE_SEC:
            return _jwt_token
    token = _fetch_token(base, app_key)
    with _JWT_LOCK:
        _jwt_token = token
        _jwt_fetched_at = time.time()
    return token


def _clear_token() -> None:
    global _jwt_token, _jwt_fetched_at
    with _JWT_LOCK:
        _jwt_token = None
        _jwt_fetched_at = 0.0


def _post_stats(base: str, token: str) -> int:
    totals = get_lifetime_totals()
    url = f"{base}/api/stats"
    payload = {
        "files_encoded": totals.files_encoded_success,
        "total_output_size_bytes": totals.total_output_bytes,
        "total_encoding_time_seconds": totals.total_encode_seconds,
    }
    status, _body = _post_json(
        url,
        payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return status


def sync_lifetime_stats_to_api() -> None:
    if not config.get_stats_api_enabled():
        return
    app_key = effective_app_key()
    if not app_key:
        return
    base = _normalize_base_url(config.get_stats_api_base_url())
    if not base:
        logger.warning("Stats API: empty base URL, skipping sync")
        return
    try:
        token = _get_bearer_token(base, app_key)
        status = _post_stats(base, token)
        if status == 401:
            _clear_token()
            token = _get_bearer_token(base, app_key)
            status = _post_stats(base, token)
        if status != 200:
            logger.warning(f"Stats API: POST /api/stats returned HTTP {status}")
    except Exception as e:
        logger.debug(f"Stats API sync failed: {e}")


def schedule_sync_lifetime_stats_if_enabled() -> None:
    if not config.get_stats_api_enabled():
        return
    if not effective_app_key():
        return

    def run() -> None:
        try:
            sync_lifetime_stats_to_api()
        except Exception as e:
            logger.debug(f"Stats API sync thread error: {e}")

    threading.Thread(target=run, daemon=True).start()
