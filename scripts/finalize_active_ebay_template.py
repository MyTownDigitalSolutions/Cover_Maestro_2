#!/usr/bin/env python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

# Allow running as `python scripts/finalize_active_ebay_template.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models.templates import (
    EbayField,
    EbayFieldEquipmentTypeContent,
    EbayFieldEquipmentTypeImagePattern,
    EbayTemplate,
    TemplateField,
    TemplateFieldAsset,
)


DESCRIPTION_NORM_KEY = "description"
IMAGE_NORM_KEYS = {
    "itemphotourl",
    "itemphotourls",
    "pictureurl",
    "pictureurls",
    "photourl",
    "photourls",
    "imageurl",
    "imageurls",
}
SUPPORTED_KEYS = {DESCRIPTION_NORM_KEY, *IMAGE_NORM_KEYS}


@dataclass
class Report:
    fields_found: int = 0
    fields_updated: int = 0
    assets_inserted: int = 0
    assets_inserted_by_type: Dict[str, int] = None

    def __post_init__(self) -> None:
        if self.assets_inserted_by_type is None:
            self.assets_inserted_by_type = {
                "description_html": 0,
                "image_parent_pattern": 0,
                "image_variation_pattern": 0,
            }


def normalize_key(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def clean_text(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    return text if text else None


def get_or_create_template_field(
    db: Session,
    *,
    key: str,
    field_name: str,
    order_index: Optional[int],
) -> TemplateField:
    row = (
        db.query(TemplateField)
        .filter(
            TemplateField.marketplace == "ebay",
            TemplateField.field_key_norm == key,
        )
        .first()
    )
    if row is None:
        row = TemplateField(
            marketplace="ebay",
            field_name=field_name,
            field_key_norm=key,
            order_index=order_index,
        )
        db.add(row)
        db.flush()
    return row


def has_canonical_fallback(db: Session, template_field_id: int, asset_type: str) -> bool:
    return (
        db.query(TemplateFieldAsset.id)
        .filter(
            TemplateFieldAsset.template_field_id == template_field_id,
            TemplateFieldAsset.asset_type == asset_type,
            TemplateFieldAsset.is_default_fallback.is_(True),
        )
        .first()
        is not None
    )


def insert_canonical_fallback(
    db: Session,
    *,
    template_field_id: int,
    asset_type: str,
    value: str,
    report: Report,
) -> None:
    db.add(
        TemplateFieldAsset(
            template_field_id=template_field_id,
            asset_type=asset_type,
            value=value,
            is_default_fallback=True,
        )
    )
    report.assets_inserted += 1
    report.assets_inserted_by_type[asset_type] += 1


def finalize_active_template(db: Session) -> Report:
    template = (
        db.query(EbayTemplate)
        .order_by(EbayTemplate.uploaded_at.desc(), EbayTemplate.id.desc())
        .first()
    )
    if template is None:
        raise RuntimeError("No eBay template found. Upload and parse a template first.")

    fields = (
        db.query(EbayField)
        .filter(EbayField.ebay_template_id == template.id)
        .order_by(EbayField.order_index.asc(), EbayField.id.asc())
        .all()
    )

    report = Report()
    supported_fields: List[EbayField] = []
    for field in fields:
        key = normalize_key(field.field_name)
        if key in SUPPORTED_KEYS:
            supported_fields.append(field)

    report.fields_found = len(supported_fields)
    if report.fields_found == 0:
        raise RuntimeError(
            f"Active template id={template.id} has no supported fields "
            f"({DESCRIPTION_NORM_KEY} + image-url keys)."
        )

    for field in supported_fields:
        key = normalize_key(field.field_name)
        canonical_field = get_or_create_template_field(
            db,
            key=key,
            field_name=field.field_name,
            order_index=field.order_index,
        )
        if field.template_field_id != canonical_field.id:
            field.template_field_id = canonical_field.id
            report.fields_updated += 1

    db.flush()

    missing_legacy: List[str] = []
    description_fields = [f for f in supported_fields if normalize_key(f.field_name) == DESCRIPTION_NORM_KEY]
    image_fields = [f for f in supported_fields if normalize_key(f.field_name) in IMAGE_NORM_KEYS]

    seeded_description_template_fields: Set[int] = set()
    for field in description_fields:
        if field.template_field_id is None:
            missing_legacy.append(
                f"EbayField id={field.id} ({field.field_name}) has NULL template_field_id after backfill."
            )
            continue
        template_field_id = int(field.template_field_id)
        if template_field_id in seeded_description_template_fields:
            continue
        seeded_description_template_fields.add(template_field_id)

        if has_canonical_fallback(db, template_field_id, "description_html"):
            continue

        legacy_row = (
            db.query(EbayFieldEquipmentTypeContent)
            .filter(
                EbayFieldEquipmentTypeContent.ebay_field_id == field.id,
                EbayFieldEquipmentTypeContent.equipment_type_id.is_(None),
            )
            .order_by(
                EbayFieldEquipmentTypeContent.is_default_fallback.desc(),
                EbayFieldEquipmentTypeContent.id.asc(),
            )
            .first()
        )
        legacy_html = clean_text(legacy_row.html_value if legacy_row else None)
        if legacy_html is None:
            missing_legacy.append(
                "Missing legacy description fallback row for "
                f"EbayField id={field.id} ({field.field_name}). "
                "Add a NULL equipment_type_id row in ebay_field_equipment_type_contents."
            )
            continue

        insert_canonical_fallback(
            db,
            template_field_id=template_field_id,
            asset_type="description_html",
            value=legacy_html,
            report=report,
        )

    seeded_image_template_fields: Set[int] = set()
    for field in image_fields:
        if field.template_field_id is None:
            missing_legacy.append(
                f"EbayField id={field.id} ({field.field_name}) has NULL template_field_id after backfill."
            )
            continue
        template_field_id = int(field.template_field_id)
        if template_field_id in seeded_image_template_fields:
            continue
        seeded_image_template_fields.add(template_field_id)

        need_parent = not has_canonical_fallback(db, template_field_id, "image_parent_pattern")
        need_variation = not has_canonical_fallback(db, template_field_id, "image_variation_pattern")
        if not need_parent and not need_variation:
            continue

        legacy_row = (
            db.query(EbayFieldEquipmentTypeImagePattern)
            .filter(
                EbayFieldEquipmentTypeImagePattern.ebay_field_id == field.id,
                EbayFieldEquipmentTypeImagePattern.equipment_type_id.is_(None),
            )
            .order_by(EbayFieldEquipmentTypeImagePattern.id.asc())
            .first()
        )

        legacy_parent = clean_text(legacy_row.parent_pattern if legacy_row else None)
        legacy_variation = clean_text(legacy_row.variation_pattern if legacy_row else None)

        if need_parent and legacy_parent is None:
            missing_legacy.append(
                "Missing legacy image parent fallback row for "
                f"EbayField id={field.id} ({field.field_name}). "
                "Add a NULL equipment_type_id row in ebay_field_equipment_type_image_patterns."
            )
        if need_variation and legacy_variation is None:
            missing_legacy.append(
                "Missing legacy image variation fallback row for "
                f"EbayField id={field.id} ({field.field_name}). "
                "Add a NULL equipment_type_id row in ebay_field_equipment_type_image_patterns."
            )
        if (need_parent and legacy_parent is None) or (need_variation and legacy_variation is None):
            continue

        if need_parent:
            insert_canonical_fallback(
                db,
                template_field_id=template_field_id,
                asset_type="image_parent_pattern",
                value=str(legacy_parent),
                report=report,
            )
        if need_variation:
            insert_canonical_fallback(
                db,
                template_field_id=template_field_id,
                asset_type="image_variation_pattern",
                value=str(legacy_variation),
                report=report,
            )

    if missing_legacy:
        raise RuntimeError(
            "Cannot finalize active eBay template due to missing legacy fallback rows:\n- "
            + "\n- ".join(missing_legacy)
        )

    db.commit()

    print(f"Active template: id={template.id} uploaded_at={template.uploaded_at}")
    print(f"Fields found (supported keys): {report.fields_found}")
    print(f"Fields updated (template_field_id backfilled): {report.fields_updated}")
    print(
        "Assets inserted: "
        f"{report.assets_inserted} "
        f"(description_html={report.assets_inserted_by_type['description_html']}, "
        f"image_parent_pattern={report.assets_inserted_by_type['image_parent_pattern']}, "
        f"image_variation_pattern={report.assets_inserted_by_type['image_variation_pattern']})"
    )
    return report


def main() -> None:
    db = SessionLocal()
    try:
        finalize_active_template(db)
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
