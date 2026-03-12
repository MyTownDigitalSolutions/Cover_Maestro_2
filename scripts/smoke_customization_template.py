#!/usr/bin/env python3
"""
Smoke Test: Customization Template Fidelity + Preview Bounds

Purpose:
  End-to-end verification for customization template:
    - upload
    - preview (<=50x50)
    - download
    - SHA-256 byte-identical match

Dependencies:
  - Python 3.9+
  - requests (pip install requests)

Date:
  2025-12-26
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, Optional

import requests


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def die(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}")
    sys.exit(code)


def ok(msg: str) -> None:
    print(f"PASS: {msg}")


def info(msg: str) -> None:
    print(f"INFO: {msg}")


def http_ok(resp: requests.Response, context: str) -> None:
    if not (200 <= resp.status_code < 300):
        die(f"{context} returned HTTP {resp.status_code}. Body: {resp.text[:2000]}")


def load_env(name: str, default: Optional[str] = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v.strip() == "":
        die(f"Missing required environment variable: {name}")
    return v


def upload_customization_template(base_url: str, xlsx_path: str, timeout_s: int = 120) -> Dict[str, Any]:
    """
    Calls existing customization upload endpoint:

      POST {BASE_URL}/settings/amazon-customization-templates/upload

    multipart:
      - file: xlsx

    If your backend expects a different field name, change ONLY files={...}.
    """
    url = f"{base_url}/settings/amazon-customization-templates/upload"
    with open(xlsx_path, "rb") as f:
        files = {
            "file": (
                os.path.basename(xlsx_path),
                f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        resp = requests.post(url, files=files, timeout=timeout_s)
    http_ok(resp, f"Upload customization template to {url}")
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}


def preview_customization_template(base_url: str, template_id: int, timeout_s: int = 120) -> Dict[str, Any]:
    url = f"{base_url}/settings/amazon-customization-templates/{template_id}/preview"
    resp = requests.get(url, timeout=timeout_s)
    http_ok(resp, f"Preview customization template from {url}")
    return resp.json()


def download_customization_template(base_url: str, template_id: int, timeout_s: int = 120) -> bytes:
    url = f"{base_url}/settings/amazon-customization-templates/{template_id}/download"
    resp = requests.get(url, timeout=timeout_s)
    http_ok(resp, f"Download customization template from {url}")
    return resp.content


def extract_template_id(upload_resp: Dict[str, Any]) -> int:
    """
    Try common shapes:
      - { id: 123 }
      - { template_id: 123 }
      - { data: { id: 123 } }

    Adjust ONLY if your payload differs.
    """
    for k in ("id", "template_id"):
        if k in upload_resp and isinstance(upload_resp[k], int):
            return int(upload_resp[k])
    data = upload_resp.get("data")
    if isinstance(data, dict):
        for k in ("id", "template_id"):
            if k in data and isinstance(data[k], int):
                return int(data[k])
    die(f"Could not find template id in upload response: {json.dumps(upload_resp)[:2000]}")
    return -1


def main() -> None:
    """
    Required env vars:
      BASE_URL                 e.g. http://localhost:8000
      TEMPLATE_XLSX_PATH       path to a real Amazon customization template XLSX

    Optional:
      TIMEOUT_S                default 120
    """
    base_url = load_env("BASE_URL", "http://localhost:8000").rstrip("/")
    xlsx_path = load_env("TEMPLATE_XLSX_PATH")
    timeout_s = int(os.environ.get("TIMEOUT_S", "120"))

    if not os.path.exists(xlsx_path):
        die(f"TEMPLATE_XLSX_PATH does not exist: {xlsx_path}")

    info(f"BASE_URL={base_url}")
    info(f"TEMPLATE_XLSX_PATH={xlsx_path}")

    original_bytes = open(xlsx_path, "rb").read()
    original_sha = sha256_bytes(original_bytes)
    info(f"Original SHA-256: {original_sha}")

    info("Uploading customization template...")
    upload_resp = upload_customization_template(base_url, xlsx_path, timeout_s=timeout_s)
    info(f"Upload response: {json.dumps(upload_resp)[:2000]}")

    template_id = extract_template_id(upload_resp)
    ok(f"Upload returned template_id={template_id}")

    info("Fetching preview...")
    preview = preview_customization_template(base_url, template_id, timeout_s=timeout_s)

    pr = int(preview.get("preview_row_count", 0) or 0)
    pc = int(preview.get("preview_column_count", 0) or 0)
    if pr > 50 or pc > 50:
        die(f"Preview bounds exceeded: preview_row_count={pr}, preview_column_count={pc}")
    ok(f"Preview bounds OK ({pr}x{pc})")

    grid = preview.get("grid", [])
    if not isinstance(grid, list) or (grid and not isinstance(grid[0], list)):
        die("Preview grid not a 2D list")
    if len(grid) != pr:
        die(f"Preview grid row count mismatch: len(grid)={len(grid)} vs preview_row_count={pr}")
    ok("Preview grid shape matches reported bounds")

    info("Downloading stored customization template...")
    downloaded_bytes = download_customization_template(base_url, template_id, timeout_s=timeout_s)
    downloaded_sha = sha256_bytes(downloaded_bytes)
    info(f"Downloaded SHA-256: {downloaded_sha}")

    if downloaded_sha != original_sha:
        die("SHA-256 mismatch: stored download is NOT byte-identical to uploaded file")
    ok("SHA-256 match: stored download is byte-identical to uploaded file")

    ok("All customization smoke checks passed.")


if __name__ == "__main__":
    main()
