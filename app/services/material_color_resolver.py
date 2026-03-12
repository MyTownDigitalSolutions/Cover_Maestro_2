from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.core import Color, MaterialColor, MaterialColourSurcharge


@dataclass(frozen=True)
class ResolvedMaterialColorContext:
    material_id: int
    color_id: Optional[int]
    internal_name: str
    friendly_name: str
    sku_abbrev: str
    surcharge: float
    ebay_variation_enabled: bool
    source: str  # "canonical" | "legacy"


def _collapse_spaces(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_name(value: Optional[str]) -> str:
    return _collapse_spaces(value).casefold()


def _norm_sku(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).lower()


def _legacy_identity_fields(row: MaterialColourSurcharge) -> tuple[str, str, str]:
    internal_name = str(row.colour or row.color_friendly_name or "")
    friendly_name = str(row.color_friendly_name or row.colour or "")
    sku_abbrev = str(row.sku_abbreviation or "")
    return internal_name, friendly_name, sku_abbrev


def _canonical_identity_fields(color: Color) -> tuple[str, str, str]:
    internal_name = str(color.internal_name or "")
    friendly_name = str(color.friendly_name or "")
    sku_abbrev = str(color.sku_abbrev or "")
    return internal_name, friendly_name, sku_abbrev


def resolve_material_color_context(
    db: Session,
    *,
    legacy_surcharge_id: int,
) -> Optional[ResolvedMaterialColorContext]:
    """
    Resolve a stable material-color context with canonical-first, legacy-fallback behavior.

    Lookup shape (Phase 3):
    - Deterministic legacy identifier: material_colour_surcharges.id

    Resolution order:
    1) Try canonical material_colors -> colors row that matches the legacy identity key
       for the same material_id.
    2) Fall back to legacy material_colour_surcharges values.
    """
    legacy_row = (
        db.query(MaterialColourSurcharge)
        .filter(MaterialColourSurcharge.id == legacy_surcharge_id)
        .first()
    )
    if legacy_row is None:
        return None

    legacy_internal, legacy_friendly, legacy_sku = _legacy_identity_fields(legacy_row)
    legacy_identity_key = (
        _norm_name(legacy_internal),
        _norm_name(legacy_friendly),
        _norm_sku(legacy_sku),
    )

    canonical_links = (
        db.query(MaterialColor)
        .options(joinedload(MaterialColor.color))
        .filter(MaterialColor.material_id == legacy_row.material_id)
        .order_by(MaterialColor.id.asc())
        .all()
    )
    for link in canonical_links:
        color = link.color
        if color is None:
            continue
        can_internal, can_friendly, can_sku = _canonical_identity_fields(color)
        canonical_identity_key = (
            _norm_name(can_internal),
            _norm_name(can_friendly),
            _norm_sku(can_sku),
        )
        if canonical_identity_key != legacy_identity_key:
            continue

        return ResolvedMaterialColorContext(
            material_id=int(link.material_id),
            color_id=int(link.color_id),
            internal_name=can_internal,
            friendly_name=can_friendly,
            sku_abbrev=can_sku,
            surcharge=float(link.surcharge or 0.0),
            ebay_variation_enabled=bool(link.ebay_variation_enabled),
            source="canonical",
        )

    return ResolvedMaterialColorContext(
        material_id=int(legacy_row.material_id),
        color_id=None,
        internal_name=legacy_internal,
        friendly_name=legacy_friendly,
        sku_abbrev=legacy_sku,
        surcharge=float(legacy_row.surcharge or 0.0),
        ebay_variation_enabled=bool(legacy_row.ebay_variation_enabled),
        source="legacy",
    )
