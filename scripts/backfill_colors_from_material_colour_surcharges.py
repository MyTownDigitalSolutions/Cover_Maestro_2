#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.core import Color, MaterialColor, MaterialColourSurcharge  # noqa: E402


REPORT_PATH = PROJECT_ROOT / "storage" / "color_backfill_report.json"


def _collapse_spaces(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_name(value: Optional[str]) -> str:
    return _collapse_spaces(value).casefold()


def _norm_sku(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).lower()


def _to_serializable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass
class LegacyRow:
    legacy_id: int
    material_id: int
    colour: Optional[str]
    color_friendly_name: Optional[str]
    sku_abbreviation: Optional[str]
    surcharge: Optional[float]
    ebay_variation_enabled: bool
    internal_name: str
    friendly_name: str
    sku_abbrev: str
    norm_internal_name: str
    norm_friendly_name: str
    norm_sku_abbrev: str

    @property
    def identity_key(self) -> Tuple[str, str, str]:
        return (self.norm_internal_name, self.norm_friendly_name, self.norm_sku_abbrev)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "legacy_id": self.legacy_id,
            "material_id": self.material_id,
            "colour": self.colour,
            "color_friendly_name": self.color_friendly_name,
            "sku_abbreviation": self.sku_abbreviation,
            "surcharge": self.surcharge,
            "ebay_variation_enabled": self.ebay_variation_enabled,
            "internal_name": self.internal_name,
            "friendly_name": self.friendly_name,
            "sku_abbrev": self.sku_abbrev,
            "normalized_identity_key": {
                "internal_name": self.norm_internal_name,
                "friendly_name": self.norm_friendly_name,
                "sku_abbrev": self.norm_sku_abbrev,
            },
        }


def _build_legacy_rows(db: Session) -> List[LegacyRow]:
    rows = (
        db.query(MaterialColourSurcharge)
        .order_by(MaterialColourSurcharge.id.asc())
        .all()
    )
    out: List[LegacyRow] = []
    for row in rows:
        colour = _collapse_spaces(row.colour)
        friendly = _collapse_spaces(row.color_friendly_name)
        sku = _collapse_spaces(row.sku_abbreviation)

        internal_name = colour or friendly
        friendly_name = friendly or colour
        sku_abbrev = sku

        out.append(
            LegacyRow(
                legacy_id=int(row.id),
                material_id=int(row.material_id),
                colour=row.colour,
                color_friendly_name=row.color_friendly_name,
                sku_abbreviation=row.sku_abbreviation,
                surcharge=float(row.surcharge or 0.0),
                ebay_variation_enabled=bool(row.ebay_variation_enabled),
                internal_name=internal_name,
                friendly_name=friendly_name,
                sku_abbrev=sku_abbrev,
                norm_internal_name=_norm_name(internal_name),
                norm_friendly_name=_norm_name(friendly_name),
                norm_sku_abbrev=_norm_sku(sku_abbrev),
            )
        )
    return out


def _detect_conflicts(
    legacy_rows: List[LegacyRow],
    existing_colors: List[Color],
) -> Tuple[Set[int], List[Dict[str, Any]], Dict[int, List[str]]]:
    entries: List[Dict[str, Any]] = []
    for row in legacy_rows:
        entries.append(
            {
                "source": "legacy",
                "legacy_id": row.legacy_id,
                "internal": row.norm_internal_name,
                "friendly": row.norm_friendly_name,
                "sku": row.norm_sku_abbrev,
                "signature_internal": (row.norm_friendly_name, row.norm_sku_abbrev),
                "signature_friendly": (row.norm_internal_name, row.norm_sku_abbrev),
                "signature_sku": (row.norm_internal_name, row.norm_friendly_name),
            }
        )
    for color in existing_colors:
        internal = _norm_name(color.internal_name)
        friendly = _norm_name(color.friendly_name)
        sku = _norm_sku(color.sku_abbrev)
        entries.append(
            {
                "source": "existing",
                "color_id": int(color.id),
                "internal": internal,
                "friendly": friendly,
                "sku": sku,
                "signature_internal": (friendly, sku),
                "signature_friendly": (internal, sku),
                "signature_sku": (internal, friendly),
            }
        )

    conflicts: List[Dict[str, Any]] = []
    row_reasons: Dict[int, List[str]] = defaultdict(list)

    def add_conflict(
        *,
        rule: str,
        key_field: str,
        key_value: str,
        signatures: Set[Tuple[str, str]],
        grouped_entries: List[Dict[str, Any]],
    ) -> None:
        if not key_value:
            return
        if len(signatures) <= 1:
            return
        legacy_ids = sorted(
            int(e["legacy_id"])
            for e in grouped_entries
            if e.get("source") == "legacy" and e.get("legacy_id") is not None
        )
        if not legacy_ids:
            return
        reason = f"{rule} ({key_field}={key_value})"
        for lid in legacy_ids:
            row_reasons[lid].append(reason)
        conflicts.append(
            {
                "rule": rule,
                "key_field": key_field,
                "key_value": key_value,
                "signatures": sorted([list(sig) for sig in signatures]),
                "legacy_row_ids": legacy_ids,
                "sources_present": sorted(set(str(e.get("source")) for e in grouped_entries)),
            }
        )

    by_internal: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_friendly: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_sku: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        if e["internal"]:
            by_internal[e["internal"]].append(e)
        if e["friendly"]:
            by_friendly[e["friendly"]].append(e)
        # Blank SKU is ignored for conflict rule #3 to avoid false global collisions.
        if e["sku"]:
            by_sku[e["sku"]].append(e)

    for key, grouped in by_internal.items():
        add_conflict(
            rule="same_normalized_internal_name_different_friendly_or_sku",
            key_field="internal_name",
            key_value=key,
            signatures=set(e["signature_internal"] for e in grouped),
            grouped_entries=grouped,
        )
    for key, grouped in by_friendly.items():
        add_conflict(
            rule="same_normalized_friendly_name_different_internal_or_sku",
            key_field="friendly_name",
            key_value=key,
            signatures=set(e["signature_friendly"] for e in grouped),
            grouped_entries=grouped,
        )
    for key, grouped in by_sku.items():
        add_conflict(
            rule="same_normalized_sku_abbrev_different_internal_or_friendly",
            key_field="sku_abbrev",
            key_value=key,
            signatures=set(e["signature_sku"] for e in grouped),
            grouped_entries=grouped,
        )

    conflicted_ids = set(row_reasons.keys())
    return conflicted_ids, conflicts, row_reasons


def _run_backfill(db: Session, *, apply: bool) -> Dict[str, Any]:
    now = datetime.utcnow()

    legacy_rows = _build_legacy_rows(db)
    existing_colors: List[Color] = db.query(Color).order_by(Color.id.asc()).all()
    existing_links: Set[Tuple[int, int]] = {
        (int(link.material_id), int(link.color_id))
        for link in db.query(MaterialColor).all()
    }

    conflicted_ids, conflicts, row_reasons = _detect_conflicts(legacy_rows, existing_colors)

    skipped_conflict_rows: List[Dict[str, Any]] = []
    candidate_rows: List[LegacyRow] = []
    for row in legacy_rows:
        if row.legacy_id in conflicted_ids:
            entry = row.as_dict()
            entry["conflict_reasons"] = sorted(set(row_reasons.get(row.legacy_id, [])))
            skipped_conflict_rows.append(entry)
        else:
            candidate_rows.append(row)

    # Reuse existing canonical colors by normalized identity.
    color_by_identity: Dict[Tuple[str, str, str], Color] = {}
    for color in existing_colors:
        key = (_norm_name(color.internal_name), _norm_name(color.friendly_name), _norm_sku(color.sku_abbrev))
        color_by_identity[key] = color

    created_colors: List[Dict[str, Any]] = []
    linked_material_colors: List[Dict[str, Any]] = []
    skipped_existing_links: List[Dict[str, Any]] = []

    planned_new_color_keys: Set[Tuple[str, str, str]] = set()
    planned_link_keys_for_new_colors: Set[Tuple[int, Tuple[str, str, str]]] = set()
    planned_link_keys_existing_colors: Set[Tuple[int, int]] = set()

    for row in candidate_rows:
        identity_key = row.identity_key
        color_obj = color_by_identity.get(identity_key)
        color_id_for_report: Optional[int] = None

        if color_obj is None:
            if apply:
                color_obj = Color(
                    internal_name=row.internal_name,
                    friendly_name=row.friendly_name,
                    sku_abbrev=(row.sku_abbrev or None),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(color_obj)
                db.flush()
                color_by_identity[identity_key] = color_obj
                color_id_for_report = int(color_obj.id)
            else:
                planned_new_color_keys.add(identity_key)
                color_id_for_report = None

            created_colors.append(
                {
                    "legacy_row_id": row.legacy_id,
                    "normalized_identity_key": {
                        "internal_name": identity_key[0],
                        "friendly_name": identity_key[1],
                        "sku_abbrev": identity_key[2],
                    },
                    "color": {
                        "id": color_id_for_report,
                        "internal_name": row.internal_name,
                        "friendly_name": row.friendly_name,
                        "sku_abbrev": row.sku_abbrev,
                        "is_active": True,
                    },
                    "mode": "applied" if apply else "dry_run_planned",
                }
            )
        else:
            color_id_for_report = int(color_obj.id)

        if apply:
            assert color_obj is not None
            material_color_pair = (row.material_id, int(color_obj.id))
            if material_color_pair in existing_links or material_color_pair in planned_link_keys_existing_colors:
                skipped_existing_links.append(
                    {
                        "legacy_row_id": row.legacy_id,
                        "material_id": row.material_id,
                        "color_id": int(color_obj.id),
                        "reason": "material_color_link_already_exists",
                    }
                )
                continue

            link = MaterialColor(
                material_id=row.material_id,
                color_id=int(color_obj.id),
                surcharge=float(row.surcharge or 0.0),
                ebay_variation_enabled=bool(row.ebay_variation_enabled),
                sort_order=None,
                created_at=now,
                updated_at=now,
            )
            db.add(link)
            planned_link_keys_existing_colors.add(material_color_pair)
            linked_material_colors.append(
                {
                    "legacy_row_id": row.legacy_id,
                    "material_id": row.material_id,
                    "color_id": int(color_obj.id),
                    "surcharge": float(row.surcharge or 0.0),
                    "ebay_variation_enabled": bool(row.ebay_variation_enabled),
                    "sort_order": None,
                    "mode": "applied",
                }
            )
        else:
            if color_obj is not None:
                material_color_pair_existing = (row.material_id, int(color_obj.id))
                if (
                    material_color_pair_existing in existing_links
                    or material_color_pair_existing in planned_link_keys_existing_colors
                ):
                    skipped_existing_links.append(
                        {
                            "legacy_row_id": row.legacy_id,
                            "material_id": row.material_id,
                            "color_id": int(color_obj.id),
                            "reason": "material_color_link_already_exists",
                        }
                    )
                    continue
                planned_link_keys_existing_colors.add(material_color_pair_existing)
                linked_material_colors.append(
                    {
                        "legacy_row_id": row.legacy_id,
                        "material_id": row.material_id,
                        "color_id": int(color_obj.id),
                        "surcharge": float(row.surcharge or 0.0),
                        "ebay_variation_enabled": bool(row.ebay_variation_enabled),
                        "sort_order": None,
                        "mode": "dry_run_planned",
                    }
                )
                continue

            material_color_pair_new = (row.material_id, identity_key)
            if material_color_pair_new in planned_link_keys_for_new_colors:
                skipped_existing_links.append(
                    {
                        "legacy_row_id": row.legacy_id,
                        "material_id": row.material_id,
                        "color_id": None,
                        "normalized_identity_key": {
                            "internal_name": identity_key[0],
                            "friendly_name": identity_key[1],
                            "sku_abbrev": identity_key[2],
                        },
                        "reason": "material_color_link_already_planned_for_new_color",
                    }
                )
                continue
            planned_link_keys_for_new_colors.add(material_color_pair_new)
            linked_material_colors.append(
                {
                    "legacy_row_id": row.legacy_id,
                    "material_id": row.material_id,
                    "color_id": None,
                    "normalized_identity_key": {
                        "internal_name": identity_key[0],
                        "friendly_name": identity_key[1],
                        "sku_abbrev": identity_key[2],
                    },
                    "surcharge": float(row.surcharge or 0.0),
                    "ebay_variation_enabled": bool(row.ebay_variation_enabled),
                    "sort_order": None,
                    "mode": "dry_run_planned",
                }
            )

    report: Dict[str, Any] = {
        "summary": {
            "dry_run": not apply,
            "legacy_rows_scanned": len(legacy_rows),
            "candidate_rows_after_conflict_filter": len(candidate_rows),
            "created_colors_count": len(created_colors),
            "linked_material_colors_count": len(linked_material_colors),
            "skipped_conflict_rows_count": len(skipped_conflict_rows),
            "skipped_existing_links_count": len(skipped_existing_links),
            "conflicts_count": len(conflicts),
            "generated_at_utc": now.isoformat(),
        },
        "created_colors": created_colors,
        "linked_material_colors": linked_material_colors,
        "skipped_conflict_rows": sorted(skipped_conflict_rows, key=lambda r: int(r["legacy_id"])),
        "skipped_existing_links": skipped_existing_links,
        "conflicts": conflicts,
    }
    return report


def _write_report(report: Dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_to_serializable)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill canonical colors/material_colors from legacy material_colour_surcharges. "
            "Defaults to dry-run."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply inserts into colors and material_colors. Default mode is dry-run (no writes).",
    )
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        report = _run_backfill(db, apply=args.apply)
        if args.apply:
            db.commit()
        else:
            db.rollback()
        _write_report(report)
        print(
            f"{'APPLY' if args.apply else 'DRY RUN'} complete. "
            f"Report written to: {REPORT_PATH}"
        )
        print(json.dumps(report["summary"], indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
