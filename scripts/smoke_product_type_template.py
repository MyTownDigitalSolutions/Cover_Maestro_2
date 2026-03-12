#!/usr/bin/env python3
"""
Smoke Test: ProductType Template Fidelity + Preview + Sparse Fields + Reimport Dedupe
Purpose:
  End-to-end verification for ProductType template preservation and indexing behavior.

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
from typing import Any, Dict, List, Optional, Tuple

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
        body = resp.text
        die(f"{context} returned HTTP {resp.status_code}. Body: {body[:2000]}")


def load_env(name: str, default: Optional[str] = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v.strip() == "":
        die(f"Missing required environment variable: {name}")
    return v


def upload_product_type_template(
    base_url: str,
    product_code: str,
    xlsx_path: str,
    timeout_s: int = 120,
) -> Dict[str, Any]:
    """
    Calls the existing ProductType import endpoint.

    NOTE: This assumes your API route is:
      POST {BASE_URL}/templates/import
    with multipart form fields:
      - product_code (text)
      - file (xlsx)

    If your backend uses different parameter names, adjust ONLY the 'data' keys and file field name.
    """
    url = f"{base_url}/templates/import"
    with open(xlsx_path, "rb") as f:
        files = {"file": (os.path.basename(xlsx_path), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"product_code": product_code}
        resp = requests.post(url, data=data, files=files, timeout=timeout_s)
    http_ok(resp, f"Upload import to {url}")
    try:
        return resp.json()
    except Exception:
        # Some implementations return plain text; allow that.
        return {"raw": resp.text}


def download_original_template_bytes(base_url: str, product_code: str, timeout_s: int = 120) -> bytes:
    """
    Calls:
      GET {BASE_URL}/templates/product-types/{product_code}/download
    """
    url = f"{base_url}/templates/product-types/{product_code}/download"
    resp = requests.get(url, timeout=timeout_s)
    http_ok(resp, f"Download original template from {url}")
    return resp.content


def preview_template(base_url: str, product_code: str, timeout_s: int = 120) -> Dict[str, Any]:
    """
    Calls:
      GET {BASE_URL}/templates/product-types/{product_code}/preview
    """
    url = f"{base_url}/templates/product-types/{product_code}/preview"
    resp = requests.get(url, timeout=timeout_s)
    http_ok(resp, f"Preview template from {url}")
    return resp.json()


def get_product_type_detail(base_url: str, product_code: str, timeout_s: int = 120) -> Dict[str, Any]:
    """
    Fetch product type detail. Most implementations provide something like:
      GET {BASE_URL}/templates/{product_code}

    If your actual route differs, change ONLY this function.
    """
    url = f"{base_url}/templates/{product_code}"
    resp = requests.get(url, timeout=timeout_s)
    http_ok(resp, f"Get product type detail from {url}")
    return resp.json()


def extract_field_names(product_type_detail: Dict[str, Any]) -> List[str]:
    """
    Attempts common shapes:
      - { fields: [{ field_name: "..." }, ...] }
      - { product_type_fields: [{ name: "..." } ...] }
      - { fields: ["FieldA", "FieldB"] }
    Adjust ONLY if your payload differs.
    """
    candidates = [
        ("fields", "field_name"),
        ("fields", "name"),
        ("product_type_fields", "field_name"),
        ("product_type_fields", "name"),
    ]

    for list_key, name_key in candidates:
        if list_key in product_type_detail and isinstance(product_type_detail[list_key], list):
            arr = product_type_detail[list_key]
            if len(arr) == 0:
                return []
            if isinstance(arr[0], str):
                return [str(x) for x in arr]
            if isinstance(arr[0], dict) and name_key in arr[0]:
                return [str(x.get(name_key, "")).strip() for x in arr if str(x.get(name_key, "")).strip() != ""]

    # fallback: try to find first list-of-dicts with a likely name field
    for k, v in product_type_detail.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            for key in ("field_name", "name"):
                if key in v[0]:
                    return [str(x.get(key, "")).strip() for x in v if str(x.get(key, "")).strip() != ""]

    return []


def assert_no_duplicates(names: List[str]) -> None:
    cleaned = [n.strip() for n in names if n.strip() != ""]
    dupes = sorted({n for n in cleaned if cleaned.count(n) > 1})
    if dupes:
        die(f"Duplicate field names detected: {dupes[:50]}")


def main() -> None:
    """
    Required env vars:
      BASE_URL              e.g. http://localhost:8000
      PRODUCT_CODE          e.g. AMPLIFIER_COVER
      TEMPLATE_XLSX_PATH    path to a real Amazon ProductType template XLSX
      SPARSE_FIELD_NAME     a field you expect the indexer to recover (exact match)

    Optional:
      TIMEOUT_S             default 120
    """
    base_url = load_env("BASE_URL", "http://localhost:8000").rstrip("/")
    product_code = load_env("PRODUCT_CODE")
    xlsx_path = load_env("TEMPLATE_XLSX_PATH")
    sparse_field = load_env("SPARSE_FIELD_NAME")
    timeout_s = int(os.environ.get("TIMEOUT_S", "120"))

    if not os.path.exists(xlsx_path):
        die(f"TEMPLATE_XLSX_PATH does not exist: {xlsx_path}")

    info(f"BASE_URL={base_url}")
    info(f"PRODUCT_CODE={product_code}")
    info(f"TEMPLATE_XLSX_PATH={xlsx_path}")
    info(f"SPARSE_FIELD_NAME={sparse_field}")

    # Read original bytes and hash
    original_bytes = open(xlsx_path, "rb").read()
    original_sha = sha256_bytes(original_bytes)
    info(f"Original SHA-256: {original_sha}")

    # 1) Upload/import once
    info("Uploading/importing ProductType template (run 1)...")
    upload_result_1 = upload_product_type_template(base_url, product_code, xlsx_path, timeout_s=timeout_s)
    info(f"Upload result (run 1): {json.dumps(upload_result_1)[:2000]}")

    # 2) Preview check
    info("Fetching preview...")
    preview = preview_template(base_url, product_code, timeout_s=timeout_s)

    pr = int(preview.get("preview_row_count", 0) or 0)
    pc = int(preview.get("preview_column_count", 0) or 0)
    if pr > 50 or pc > 50:
        die(f"Preview bounds exceeded: preview_row_count={pr}, preview_column_count={pc}")
    ok(f"Preview bounds OK ({pr}x{pc})")

    # Assert ProductType preview is using the deterministic "Template" sheet
    sheet_name = str(preview.get("sheet_name", "") or "")
    if sheet_name != "Template":
        die(f'Expected preview sheet_name="Template" but got "{sheet_name}"')
    ok('Preview uses expected sheet_name="Template"')

    grid = preview.get("grid", [])
    if not isinstance(grid, list):
        die("Preview grid is not a list")
    if len(grid) != pr:
        die(f"Preview grid row count mismatch: len(grid)={len(grid)} preview_row_count={pr}")
    ok("Preview grid shape matches reported bounds")

    # 3) Download stored original and hash compare (byte-identical guarantee)
    info("Downloading stored original XLSX...")
    downloaded_bytes = download_original_template_bytes(base_url, product_code, timeout_s=timeout_s)
    downloaded_sha = sha256_bytes(downloaded_bytes)
    info(f"Downloaded SHA-256: {downloaded_sha}")

    if downloaded_sha != original_sha:
        die("SHA-256 mismatch: stored download is NOT byte-identical to uploaded file")
    ok("SHA-256 match: stored download is byte-identical to uploaded file")

    # 4) Verify sparse field exists and no duplicates
    info("Fetching product type detail to inspect field list...")
    detail_1 = get_product_type_detail(base_url, product_code, timeout_s=timeout_s)
    names_1 = extract_field_names(detail_1)
    if not names_1:
        die("Could not extract any field names from product type detail response (adjust extract_field_names() if needed)")
    assert_no_duplicates(names_1)
    ok(f"No duplicate field names after import (count={len(names_1)})")

    if sparse_field not in names_1:
        die(f"Expected sparse field '{sparse_field}' was not found in field list (count={len(names_1)})")
    ok(f"Sparse field present: '{sparse_field}'")

    # 5) Re-import and verify no duplicates + sparse still present
    info("Uploading/importing ProductType template (run 2 / re-import)...")
    upload_result_2 = upload_product_type_template(base_url, product_code, xlsx_path, timeout_s=timeout_s)
    info(f"Upload result (run 2): {json.dumps(upload_result_2)[:2000]}")

    detail_2 = get_product_type_detail(base_url, product_code, timeout_s=timeout_s)
    names_2 = extract_field_names(detail_2)
    assert_no_duplicates(names_2)
    ok(f"No duplicate field names after re-import (count={len(names_2)})")

    if sparse_field not in names_2:
        die(f"Sparse field '{sparse_field}' missing after re-import")
    ok(f"Sparse field still present after re-import: '{sparse_field}'")

    # Optional: ensure count didn't inflate unexpectedly (soft check)
    if len(names_2) > len(names_1) + 5:
        info(f"WARNING: field count increased noticeably after re-import ({len(names_1)} -> {len(names_2)}). Investigate if unexpected.")
    else:
        ok(f"Field count stable-ish across re-import ({len(names_1)} -> {len(names_2)})")

    ok("All smoke checks passed.")


if __name__ == "__main__":
    main()
