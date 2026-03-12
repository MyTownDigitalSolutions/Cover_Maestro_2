from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.templates import (
    EbayField,
    EbayFieldEquipmentTypeContent,
    EbayFieldEquipmentTypeImagePattern,
    TemplateFieldAsset,
    TemplateFieldAssetEquipmentType,
)


def _clean_value(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    return text if text else None


def _resolve_canonical_asset_value(
    db: Session,
    template_field_id: int,
    asset_type: str,
    equipment_type_id: Optional[int],
) -> Optional[str]:
    # Deterministic fallback-first semantics for eBay template assets:
    # when a fallback exists for this field/type, it applies to all equipment types.
    fallback_row = (
        db.query(TemplateFieldAsset)
        .filter(
            TemplateFieldAsset.template_field_id == template_field_id,
            TemplateFieldAsset.asset_type == asset_type,
            TemplateFieldAsset.is_default_fallback.is_(True),
        )
        .order_by(TemplateFieldAsset.id.desc())
        .first()
    )
    fallback_value = _clean_value(fallback_row.value if fallback_row else None)
    if fallback_value is not None:
        return fallback_value

    if equipment_type_id is not None:
        exact_row = (
            db.query(TemplateFieldAsset)
            .join(
                TemplateFieldAssetEquipmentType,
                TemplateFieldAssetEquipmentType.asset_id == TemplateFieldAsset.id,
            )
            .filter(
                TemplateFieldAsset.template_field_id == template_field_id,
                TemplateFieldAsset.asset_type == asset_type,
                TemplateFieldAssetEquipmentType.equipment_type_id == equipment_type_id,
            )
            .order_by(TemplateFieldAsset.id.desc())
            .first()
        )
        exact_value = _clean_value(exact_row.value if exact_row else None)
        if exact_value is not None:
            return exact_value

    return None


def _resolve_legacy_image_row(
    db: Session,
    template_field_id: int,
    equipment_type_id: Optional[int],
) -> Optional[EbayFieldEquipmentTypeImagePattern]:
    field_ids_subq = select(EbayField.id).where(EbayField.template_field_id == template_field_id)

    if equipment_type_id is not None:
        exact_row = (
            db.query(EbayFieldEquipmentTypeImagePattern)
            .filter(
                EbayFieldEquipmentTypeImagePattern.ebay_field_id.in_(field_ids_subq),
                EbayFieldEquipmentTypeImagePattern.equipment_type_id == equipment_type_id,
            )
            .order_by(
                EbayFieldEquipmentTypeImagePattern.ebay_field_id.desc(),
                EbayFieldEquipmentTypeImagePattern.id.asc(),
            )
            .first()
        )
        if exact_row is not None:
            return exact_row

    return (
        db.query(EbayFieldEquipmentTypeImagePattern)
        .filter(
            EbayFieldEquipmentTypeImagePattern.ebay_field_id.in_(field_ids_subq),
            EbayFieldEquipmentTypeImagePattern.equipment_type_id.is_(None),
        )
        .order_by(
            EbayFieldEquipmentTypeImagePattern.ebay_field_id.desc(),
            EbayFieldEquipmentTypeImagePattern.id.asc(),
        )
        .first()
    )


def _resolve_legacy_description_value(
    db: Session,
    template_field_id: int,
    equipment_type_id: Optional[int],
) -> Optional[str]:
    field_ids_subq = select(EbayField.id).where(EbayField.template_field_id == template_field_id)

    if equipment_type_id is not None:
        exact_row = (
            db.query(EbayFieldEquipmentTypeContent)
            .filter(
                EbayFieldEquipmentTypeContent.ebay_field_id.in_(field_ids_subq),
                EbayFieldEquipmentTypeContent.equipment_type_id == equipment_type_id,
            )
            .order_by(
                EbayFieldEquipmentTypeContent.ebay_field_id.desc(),
                EbayFieldEquipmentTypeContent.id.asc(),
            )
            .first()
        )
        exact_value = _clean_value(exact_row.html_value if exact_row else None)
        if exact_value is not None:
            return exact_value

    fallback_row = (
        db.query(EbayFieldEquipmentTypeContent)
        .filter(
            EbayFieldEquipmentTypeContent.ebay_field_id.in_(field_ids_subq),
            EbayFieldEquipmentTypeContent.equipment_type_id.is_(None),
        )
        .order_by(
            EbayFieldEquipmentTypeContent.is_default_fallback.desc(),
            EbayFieldEquipmentTypeContent.ebay_field_id.desc(),
            EbayFieldEquipmentTypeContent.id.asc(),
        )
        .first()
    )
    return _clean_value(fallback_row.html_value if fallback_row else None)


def resolve_ebay_field_assets(
    db: Session,
    template_field_id: int,
    equipment_type_id: int | None,
) -> dict:
    """
    Canonical-first resolver for eBay field assets.

    Resolution order per value:
    1) TemplateFieldAsset fallback (is_default_fallback=True)
    2) TemplateFieldAsset exact equipment_type match (only if no fallback exists)
    3) Legacy eBay field tables (image patterns + description content)

    Returns normalized output:
    {
        "parent_pattern": str | None,
        "variation_pattern": str | None,
        "description_html": str | None,
    }
    """
    parent_pattern = _resolve_canonical_asset_value(
        db=db,
        template_field_id=template_field_id,
        asset_type="image_parent_pattern",
        equipment_type_id=equipment_type_id,
    )
    variation_pattern = _resolve_canonical_asset_value(
        db=db,
        template_field_id=template_field_id,
        asset_type="image_variation_pattern",
        equipment_type_id=equipment_type_id,
    )
    description_html = _resolve_canonical_asset_value(
        db=db,
        template_field_id=template_field_id,
        asset_type="description_html",
        equipment_type_id=equipment_type_id,
    )

    if parent_pattern is None or variation_pattern is None:
        legacy_image_row = _resolve_legacy_image_row(
            db=db,
            template_field_id=template_field_id,
            equipment_type_id=equipment_type_id,
        )
        if legacy_image_row is not None:
            if parent_pattern is None:
                parent_pattern = _clean_value(legacy_image_row.parent_pattern)
            if variation_pattern is None:
                variation_pattern = _clean_value(legacy_image_row.variation_pattern)

    if description_html is None:
        description_html = _resolve_legacy_description_value(
            db=db,
            template_field_id=template_field_id,
            equipment_type_id=equipment_type_id,
        )

    return {
        "parent_pattern": parent_pattern,
        "variation_pattern": variation_pattern,
        "description_html": description_html,
    }
