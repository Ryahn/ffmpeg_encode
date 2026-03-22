"""Upload lifetime encoding totals to the ffmpeg-encode.com stats API."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Optional

from storage import get_lifetime_totals
from utils.config import config
from utils.logger import logger

REQUEST_TIMEOUT_SEC = 10


def _normalize_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if u.endswith("/api"):
        u = u[:-4].rstrip("/")
    return u


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


def _post_stats(base: str) -> int:
    totals = get_lifetime_totals()
    url = f"{base}/api/stats"
    payload = {
        "files_encoded": totals.files_encoded_success,
        "total_output_size_bytes": totals.total_output_bytes,
        "total_encoding_time_seconds": totals.total_encode_seconds,
    }
    status, _body = _post_json(url, payload)
    return status


def sync_lifetime_stats_to_api() -> None:
    if not config.get_stats_api_enabled():
        return
    base = _normalize_base_url(config.get_stats_api_base_url())
    if not base:
        logger.warning("Stats API: empty base URL, skipping sync")
        return
    try:
        status = _post_stats(base)
        if status != 200:
            logger.warning(f"Stats API: POST /api/stats returned HTTP {status}")
    except Exception as e:
        logger.debug(f"Stats API sync failed: {e}")


def schedule_sync_lifetime_stats_if_enabled() -> None:
    if not config.get_stats_api_enabled():
        return

    def run() -> None:
        try:
            sync_lifetime_stats_to_api()
        except Exception as e:
            logger.debug(f"Stats API sync thread error: {e}")

    threading.Thread(target=run, daemon=True).start()
