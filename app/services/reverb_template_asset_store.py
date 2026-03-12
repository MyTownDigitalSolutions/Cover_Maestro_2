from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from app.models.templates import ReverbTemplate
from app.services.storage_policy import get_reverb_template_paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ReverbTemplateAssetMissingError(FileNotFoundError):
    pass


def get_reverb_template_storage_key(template_id: int, original_filename: Optional[str] = None) -> str:
    source_name = str(original_filename or "").strip().lower()
    extension = os.path.splitext(source_name)[1] or ".csv"
    canonical_path, _ = get_reverb_template_paths(template_id, extension=extension)
    return canonical_path.replace("\\", "/")


def get_reverb_template_media_type(template: ReverbTemplate) -> str:
    ext = os.path.splitext((template.original_filename or template.file_path or "").lower())[1]
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext == ".xlsx" else "text/csv"


def get_reverb_template_asset_error_message(template: ReverbTemplate) -> str:
    storage_ref = str(template.file_path or "").strip() or get_reverb_template_storage_key(
        int(template.id),
        template.original_filename,
    )
    return (
        f"Reverb template asset unavailable for template_id={template.id} "
        f"storage_ref={storage_ref}. Re-upload or replace the template file."
    )


def _legacy_disk_candidates(template: ReverbTemplate) -> list[str]:
    candidates: list[str] = []
    stored_path = str(template.file_path or "").strip()
    if not stored_path:
        return candidates
    candidates.append(stored_path)
    if not os.path.isabs(stored_path):
        candidates.append(str((PROJECT_ROOT / stored_path).resolve()))
    return candidates


def load_reverb_template_asset_bytes(
    template: ReverbTemplate,
    *,
    db: Optional[Session] = None,
    persist_backfill: bool = True,
) -> bytes:
    if template.asset_blob:
        return bytes(template.asset_blob)

    for candidate in _legacy_disk_candidates(template):
        if not candidate or not os.path.exists(candidate):
            continue
        with open(candidate, "rb") as f:
            payload = f.read()
        if not payload:
            continue

        if persist_backfill and db is not None:
            template.asset_blob = payload
            template.file_path = get_reverb_template_storage_key(int(template.id), template.original_filename)
            template.file_size = len(payload)
            template.sha256 = hashlib.sha256(payload).hexdigest()
            db.commit()
            db.refresh(template)
        return payload

    raise ReverbTemplateAssetMissingError(get_reverb_template_asset_error_message(template))


@contextmanager
def materialize_reverb_template_asset(
    template: ReverbTemplate,
    *,
    db: Optional[Session] = None,
    persist_backfill: bool = True,
) -> Iterator[str]:
    payload = load_reverb_template_asset_bytes(template, db=db, persist_backfill=persist_backfill)
    suffix = os.path.splitext((template.original_filename or "").strip())[1] or ".csv"
    temp_path = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(payload)
        temp_path = temp_file.name

    try:
        yield temp_path
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
