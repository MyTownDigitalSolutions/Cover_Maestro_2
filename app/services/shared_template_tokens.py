import re
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.core import ModelPricingSnapshot


PRICE_PLACEHOLDER_PATTERN = re.compile(r"\[PRICE:([^\]]+)\]", flags=re.IGNORECASE)
PRICE_PLACEHOLDER_SPEC_PATTERN = re.compile(
    r"^\s*marketplace\s*=\s*([a-zA-Z0-9_-]+)\s*:\s*variant\s*=\s*([a-zA-Z0-9_\-\s]+?)(?:\s*([+-])\s*([0-9]+(?:\.[0-9]+)?))?\s*$",
    flags=re.IGNORECASE,
)

REVERB_LEGACY_PRICE_VARIANT_MAP = {
    "[REVERB_PRICE]": "choice_no_padding",
    "[Reverb_Price]": "choice_no_padding",
    "[REVERB_PRICE_CHOICE_NP]": "choice_no_padding",
    "[REVERB_PRICE_CHOICE_P]": "choice_padded",
    "[REVERB_PRICE_PREMIUM_NP]": "premium_no_padding",
    "[REVERB_PRICE_PREMIUM_P]": "premium_padded",
}

BASE_SKU_TOKENS = ("[BASE_SKU]", "[Base_Sku]", "[base_sku]")
STRUCTURED_TOKEN_PATTERN = re.compile(r"\[(t_[a-z0-9_]+)\]")
STRUCTURED_MODEL_BASE_TOKEN = "t_model"
STRUCTURED_MODEL_ATTRIBUTE_PREFIX = "t_model_c_"
STRUCTURED_EQUIPMENT_TYPE_BASE_TOKEN = "t_equipment_type"
STRUCTURED_DESIGN_OPTION_PREFIX = "t_design_option_"
STRUCTURED_ATTRIBUTE_SEPARATOR = "_c_"


def normalize_variant_key_for_price_token(raw_value: str) -> str:
    return re.sub(r"\s+", "_", str(raw_value or "").strip().lower())


def is_price_placeholder_token(token: str) -> bool:
    text = str(token or "")
    return bool(text) and bool(PRICE_PLACEHOLDER_PATTERN.fullmatch(text))


def resolve_single_price_placeholder(
    *,
    spec_text: str,
    db: Session,
    model_id: int,
    field_name: str,
    numeric_zero_default: bool = False,
) -> str:
    if db is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Database session missing while resolving PRICE placeholder "
                f"in field '{field_name}'."
            ),
        )

    match = PRICE_PLACEHOLDER_SPEC_PATTERN.match(str(spec_text or ""))
    if not match:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid PRICE placeholder syntax in field "
                f"'{field_name}'. Expected format: "
                "[PRICE:marketplace=<name>:variant=<variant_key> +/- <dollars>]"
            ),
        )

    marketplace = str(match.group(1) or "").strip().lower()
    variant_key = normalize_variant_key_for_price_token(match.group(2) or "")
    operator = str(match.group(3) or "").strip()
    delta_amount_text = str(match.group(4) or "").strip()

    delta_cents = 0
    if operator and delta_amount_text:
        try:
            delta_cents = int(round(float(delta_amount_text) * 100))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid PRICE placeholder adjustment in field "
                    f"'{field_name}'. Adjustment must be numeric."
                ),
            )
        if operator == "-":
            delta_cents = -delta_cents

    snapshot = (
        db.query(ModelPricingSnapshot)
        .filter(
            ModelPricingSnapshot.model_id == model_id,
            ModelPricingSnapshot.marketplace.ilike(marketplace),
            ModelPricingSnapshot.variant_key.ilike(variant_key),
        )
        .order_by(ModelPricingSnapshot.id.desc())
        .first()
    )
    if not snapshot:
        if numeric_zero_default:
            return "0"
        raise HTTPException(
            status_code=400,
            detail=(
                "Missing pricing snapshot for PRICE placeholder in field "
                f"'{field_name}': marketplace='{marketplace}', variant='{variant_key}', model_id={model_id}."
            ),
        )

    base_cents = int(snapshot.retail_price_cents or 0)
    resolved_cents = base_cents + delta_cents
    return f"{resolved_cents / 100:.2f}"


def resolve_price_placeholders_in_value(
    *,
    value: str,
    db: Session,
    model_id: int,
    field_name: str,
    numeric_zero_default: bool = False,
) -> str:
    text = str(value or "")
    if "[PRICE:" not in text.upper():
        return text
    return PRICE_PLACEHOLDER_PATTERN.sub(
        lambda m: resolve_single_price_placeholder(
            spec_text=str(m.group(1) or ""),
            db=db,
            model_id=model_id,
            field_name=field_name,
            numeric_zero_default=numeric_zero_default,
        ),
        text,
    )


def get_model_base_sku(model: Any) -> str:
    return str(getattr(model, "parent_sku", "") or "")


def get_model_base_sku_token_value(model: Any, *, numeric_zero_default: bool = False) -> str:
    base_sku = get_model_base_sku(model).strip()
    if base_sku:
        return base_sku
    return "0" if numeric_zero_default else ""


def apply_base_sku_tokens(value: str, model: Any, *, numeric_zero_default: bool = False) -> str:
    text = str(value or "")
    if "[BASE_SKU" not in text.upper():
        return text
    base_sku_value = get_model_base_sku_token_value(model, numeric_zero_default=numeric_zero_default)
    out = text
    for token in BASE_SKU_TOKENS:
        out = out.replace(token, base_sku_value)
    return out


def normalize_design_option_structured_key(raw_identity: Any) -> str:
    text = str(raw_identity or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    if text.lower().startswith(STRUCTURED_DESIGN_OPTION_PREFIX):
        text = text[len(STRUCTURED_DESIGN_OPTION_PREFIX):]
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return text


def normalize_structured_equipment_type_token_value(value: Any) -> str:
    return str(value or "").lower().replace(" ", "_")


def parse_structured_token(token_text: str) -> Optional[Dict[str, Optional[str]]]:
    token = str(token_text or "").strip()
    if not token.startswith("t_"):
        return None

    if token == STRUCTURED_MODEL_BASE_TOKEN:
        return {"entity": "model", "key": None, "attribute": None}

    if token.startswith(STRUCTURED_MODEL_ATTRIBUTE_PREFIX):
        attribute = token[len(STRUCTURED_MODEL_ATTRIBUTE_PREFIX):]
        if not attribute:
            return None
        return {"entity": "model", "key": None, "attribute": attribute}

    if token == STRUCTURED_EQUIPMENT_TYPE_BASE_TOKEN:
        return {"entity": "equipment_type", "key": None, "attribute": None}

    if token.startswith(STRUCTURED_DESIGN_OPTION_PREFIX):
        tail = token[len(STRUCTURED_DESIGN_OPTION_PREFIX):]
        if not tail:
            return None
        if STRUCTURED_ATTRIBUTE_SEPARATOR in tail:
            key, attribute = tail.rsplit(STRUCTURED_ATTRIBUTE_SEPARATOR, 1)
            if not key or not attribute:
                return None
            return {"entity": "design_option", "key": key, "attribute": attribute}
        return {"entity": "design_option", "key": tail, "attribute": None}

    return None


def _resolve_model_structured_token(
    *,
    attribute: Optional[str],
    model: Any,
    manufacturer: Any = None,
    series: Any = None,
    numeric_zero_default: bool = False,
) -> Optional[str]:
    if model is None:
        return None

    if attribute is None:
        return str(getattr(model, "name", "") or "")
    if attribute == "name":
        return str(getattr(model, "name", "") or "")
    if attribute == "base_sku":
        return get_model_base_sku_token_value(model, numeric_zero_default=numeric_zero_default)
    if attribute == "manufacturer_name":
        return str(getattr(manufacturer, "name", "") or "")
    if attribute == "series_name":
        return str(getattr(series, "name", "") or "")
    return None


def _build_design_option_structured_key_map(design_option_map: Optional[Dict[Any, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for raw_identity, option in (design_option_map or {}).items():
        key = normalize_design_option_structured_key(getattr(option, "placeholder_token", None) or raw_identity)
        if key and key not in out:
            out[key] = option
    return out


def _resolve_equipment_type_structured_token(
    *,
    attribute: Optional[str],
    equipment_type: Any = None,
) -> Optional[str]:
    if equipment_type is None or attribute is not None:
        return None
    return normalize_structured_equipment_type_token_value(getattr(equipment_type, "name", "") or "")


def _resolve_design_option_structured_token(
    *,
    key: Optional[str],
    attribute: Optional[str],
    design_option_map: Optional[Dict[Any, Any]],
    numeric_zero_default: bool = False,
) -> Optional[str]:
    if not key:
        return None

    option = _build_design_option_structured_key_map(design_option_map).get(str(key or "").strip().lower())
    if option is None:
        return None

    if attribute is None or attribute == "name":
        return str(getattr(option, "name", "") or "")
    if attribute == "value":
        cents = int(getattr(option, "price_cents", 0) or 0)
        return f"{cents / 100:.2f}"
    if attribute == "sku":
        return str(getattr(option, "sku_abbreviation", "") or "")
    if attribute == "description":
        return str(getattr(option, "description", "") or "")
    return None


def resolve_structured_token(
    token_text: str,
    *,
    model: Any = None,
    manufacturer: Any = None,
    series: Any = None,
    equipment_type: Any = None,
    design_option_map: Optional[Dict[Any, Any]] = None,
    numeric_zero_default: bool = False,
) -> Optional[str]:
    parsed = parse_structured_token(token_text)
    if not parsed:
        return None

    entity = parsed.get("entity")
    if entity == "model":
        return _resolve_model_structured_token(
            attribute=parsed.get("attribute"),
            model=model,
            manufacturer=manufacturer,
            series=series,
            numeric_zero_default=numeric_zero_default,
        )
    if entity == "equipment_type":
        return _resolve_equipment_type_structured_token(
            attribute=parsed.get("attribute"),
            equipment_type=equipment_type,
        )
    if entity == "design_option":
        return _resolve_design_option_structured_token(
            key=parsed.get("key"),
            attribute=parsed.get("attribute"),
            design_option_map=design_option_map,
            numeric_zero_default=numeric_zero_default,
        )
    return None


def resolve_structured_tokens_in_value(
    value: str,
    *,
    model: Any = None,
    manufacturer: Any = None,
    series: Any = None,
    equipment_type: Any = None,
    design_option_map: Optional[Dict[Any, Any]] = None,
    numeric_zero_default: bool = False,
) -> str:
    text = str(value or "")
    if "[t_" not in text:
        return text

    def _replace(match: re.Match[str]) -> str:
        token_text = str(match.group(1) or "")
        resolved = resolve_structured_token(
            token_text,
            model=model,
            manufacturer=manufacturer,
            series=series,
            equipment_type=equipment_type,
            design_option_map=design_option_map,
            numeric_zero_default=numeric_zero_default,
        )
        if resolved is None:
            return match.group(0)
        return resolved

    return STRUCTURED_TOKEN_PATTERN.sub(_replace, text)
