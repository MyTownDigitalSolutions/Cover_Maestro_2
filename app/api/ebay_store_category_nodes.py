from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.core import (
    EbayStoreCategoryNode,
    EbayStoreCategoryNodeBinding,
    EquipmentType,
    Manufacturer,
    Series,
    Model,
)
from app.schemas.core import (
    EbayStoreCategoryNodeCreate,
    EbayStoreCategoryNodeUpdate,
    EbayStoreCategoryNodeResponse,
    EbayStoreCategoryNodeBindingCreate,
)


router = APIRouter(prefix="/ebay-store-category-nodes", tags=["eBay Store Category Nodes"])

VALID_LEVELS = {"top", "second", "third"}
VALID_BINDING_TYPES = {"none", "equipment_type", "manufacturer", "series", "model", "custom"}
ENTITY_BINDING_TYPES = {"equipment_type", "manufacturer", "series", "model"}


def _normalize_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _validate_binding_exists(db: Session, binding_type: str, binding_id: int) -> None:
    model_map = {
        "equipment_type": EquipmentType,
        "manufacturer": Manufacturer,
        "series": Series,
        "model": Model,
    }
    model_cls = model_map.get(binding_type)
    if model_cls is None:
        return
    exists = db.query(model_cls).filter(model_cls.id == binding_id).first()
    if not exists:
        raise HTTPException(status_code=400, detail=f"Invalid binding_id for binding_type '{binding_type}'")


def _normalize_bindings_input(bindings: Optional[List[EbayStoreCategoryNodeBindingCreate]]) -> Optional[List[Dict[str, Any]]]:
    if bindings is None:
        return None
    out: List[Dict[str, Any]] = []
    for b in bindings:
        b_type = (b.binding_type or "").strip()
        out.append({"binding_type": b_type, "binding_id": b.binding_id})
    return out


def _validate_bindings_for_node(
    db: Session,
    node_binding_type: str,
    bindings: List[Dict[str, Any]],
) -> None:
    if node_binding_type in {"none", "custom"}:
        if bindings:
            raise HTTPException(status_code=400, detail=f"binding_type '{node_binding_type}' requires bindings to be empty")
        return

    if node_binding_type not in ENTITY_BINDING_TYPES:
        raise HTTPException(status_code=400, detail="Invalid binding_type")

    if not bindings:
        raise HTTPException(status_code=400, detail=f"binding_type '{node_binding_type}' requires at least one binding")

    seen = set()
    for b in bindings:
        b_type = (b.get("binding_type") or "").strip()
        b_id = b.get("binding_id")
        if b_type not in ENTITY_BINDING_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid binding_type '{b_type}' in bindings")
        if b_type != node_binding_type:
            raise HTTPException(status_code=400, detail="All bindings must match node binding_type")
        if b_id is None:
            raise HTTPException(status_code=400, detail="binding_id is required in bindings")
        key = (b_type, b_id)
        if key in seen:
            raise HTTPException(status_code=400, detail="Duplicate bindings are not allowed")
        seen.add(key)
        _validate_binding_exists(db, b_type, b_id)


def _validate_node_payload(
    db: Session,
    payload: Dict[str, Any],
    existing_id: Optional[int] = None,
) -> Dict[str, Any]:
    state = dict(payload)
    state.pop("bindings", None)
    state["system"] = (state.get("system") or "").strip() or "ebay"
    state["level"] = (state.get("level") or "").strip()
    state["name"] = (state.get("name") or "").strip()
    state["binding_type"] = (state.get("binding_type") or "none").strip()
    state["binding_label"] = _normalize_optional_string(state.get("binding_label"))

    if state["level"] not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid level")
    if not state["name"]:
        raise HTTPException(status_code=400, detail="name is required")

    parent_id = state.get("parent_id")
    if state["level"] == "top":
        if parent_id is not None:
            raise HTTPException(status_code=400, detail="top level requires parent_id to be null")
    else:
        if parent_id is None:
            raise HTTPException(status_code=400, detail=f"{state['level']} level requires parent_id")
        if existing_id is not None and parent_id == existing_id:
            raise HTTPException(status_code=400, detail="parent_id cannot equal id")
        parent = db.query(EbayStoreCategoryNode).filter(EbayStoreCategoryNode.id == parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Invalid parent_id")
        if state["level"] == "second" and parent.level != "top":
            raise HTTPException(status_code=400, detail="second level parent must be top level")
        if state["level"] == "third" and parent.level != "second":
            raise HTTPException(status_code=400, detail="third level parent must be second level")

    binding_type = state["binding_type"]
    binding_id = state.get("binding_id")
    binding_label = state.get("binding_label")

    if binding_type not in VALID_BINDING_TYPES:
        raise HTTPException(status_code=400, detail="Invalid binding_type")

    if binding_type == "none":
        if binding_id is not None or binding_label is not None:
            raise HTTPException(status_code=400, detail="binding_type 'none' requires binding_id and binding_label to be null")
    elif binding_type == "custom":
        if binding_id is not None:
            raise HTTPException(status_code=400, detail="binding_type 'custom' requires binding_id to be null")
        if binding_label is None:
            raise HTTPException(status_code=400, detail="binding_type 'custom' requires non-empty binding_label")
    else:
        if binding_type not in ENTITY_BINDING_TYPES:
            raise HTTPException(status_code=400, detail="Invalid binding_type")
        if binding_label is not None:
            raise HTTPException(status_code=400, detail=f"binding_type '{binding_type}' requires binding_label to be null")
        if binding_id is not None:
            _validate_binding_exists(db, binding_type, binding_id)

    return state


@router.get("", response_model=List[EbayStoreCategoryNodeResponse])
@router.get("/", response_model=List[EbayStoreCategoryNodeResponse])
def list_ebay_store_category_nodes(
    system: Optional[str] = None,
    level: Optional[str] = None,
    parent_id: Optional[int] = None,
    binding_type: Optional[str] = None,
    binding_id: Optional[int] = None,
    include_disabled: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(EbayStoreCategoryNode).options(selectinload(EbayStoreCategoryNode.bindings))

    if system is not None:
        query = query.filter(EbayStoreCategoryNode.system == system)
    if level is not None:
        query = query.filter(EbayStoreCategoryNode.level == level)
    if parent_id is not None:
        query = query.filter(EbayStoreCategoryNode.parent_id == parent_id)
    if binding_type is not None or binding_id is not None:
        query = query.join(EbayStoreCategoryNodeBinding)
        if binding_type is not None:
            query = query.filter(EbayStoreCategoryNodeBinding.binding_type == binding_type)
        if binding_id is not None:
            query = query.filter(EbayStoreCategoryNodeBinding.binding_id == binding_id)
    if not include_disabled:
        query = query.filter(EbayStoreCategoryNode.is_enabled == True)  # noqa: E712

    return query.distinct().order_by(
        EbayStoreCategoryNode.system.asc(),
        EbayStoreCategoryNode.level.asc(),
        EbayStoreCategoryNode.parent_id.asc(),
        EbayStoreCategoryNode.name.asc(),
        EbayStoreCategoryNode.id.asc(),
    ).all()


@router.post("", response_model=EbayStoreCategoryNodeResponse)
@router.post("/", response_model=EbayStoreCategoryNodeResponse)
def create_ebay_store_category_node(data: EbayStoreCategoryNodeCreate, db: Session = Depends(get_db)):
    payload = _validate_node_payload(db, data.dict())
    normalized_bindings = _normalize_bindings_input(data.bindings)
    if normalized_bindings is None:
        if payload["binding_type"] in ENTITY_BINDING_TYPES and payload.get("binding_id") is not None:
            normalized_bindings = [{"binding_type": payload["binding_type"], "binding_id": payload["binding_id"]}]
        else:
            normalized_bindings = []
    _validate_bindings_for_node(db, payload["binding_type"], normalized_bindings)

    node = EbayStoreCategoryNode(**payload)
    db.add(node)
    db.flush()

    for binding in normalized_bindings:
        db.add(
            EbayStoreCategoryNodeBinding(
                node_id=node.id,
                binding_type=binding["binding_type"],
                binding_id=binding["binding_id"],
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate bindings are not allowed")

    node_with_bindings = (
        db.query(EbayStoreCategoryNode)
        .options(selectinload(EbayStoreCategoryNode.bindings))
        .filter(EbayStoreCategoryNode.id == node.id)
        .first()
    )
    return node_with_bindings


@router.put("/{node_id}", response_model=EbayStoreCategoryNodeResponse)
def update_ebay_store_category_node(
    node_id: int,
    data: EbayStoreCategoryNodeUpdate,
    db: Session = Depends(get_db),
):
    node = db.query(EbayStoreCategoryNode).filter(EbayStoreCategoryNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="eBay store category node not found")

    current_state = {
        "system": node.system,
        "level": node.level,
        "name": node.name,
        "store_category_number": node.store_category_number,
        "parent_id": node.parent_id,
        "is_enabled": node.is_enabled,
        "binding_type": node.binding_type,
        "binding_id": node.binding_id,
        "binding_label": node.binding_label,
    }
    incoming = data.dict(exclude_unset=True)
    bindings_provided = "bindings" in incoming
    normalized_bindings = _normalize_bindings_input(incoming.get("bindings")) if bindings_provided else None
    if "bindings" in incoming:
        incoming.pop("bindings")
    merged = {**current_state, **incoming}
    payload = _validate_node_payload(db, merged, existing_id=node.id)

    if bindings_provided:
        _validate_bindings_for_node(db, payload["binding_type"], normalized_bindings or [])

    for key, value in payload.items():
        setattr(node, key, value)
    node.updated_at = datetime.utcnow()

    binding_type_changed_to_non_entity = (
        "binding_type" in incoming and payload["binding_type"] in {"none", "custom"}
    )

    if bindings_provided or binding_type_changed_to_non_entity:
        node.bindings.clear()
        if bindings_provided:
            for binding in normalized_bindings or []:
                node.bindings.append(
                    EbayStoreCategoryNodeBinding(
                        binding_type=binding["binding_type"],
                        binding_id=binding["binding_id"],
                    )
                )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate bindings are not allowed")

    node_with_bindings = (
        db.query(EbayStoreCategoryNode)
        .options(selectinload(EbayStoreCategoryNode.bindings))
        .filter(EbayStoreCategoryNode.id == node.id)
        .first()
    )
    return node_with_bindings


@router.delete("/{node_id}")
def delete_ebay_store_category_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(EbayStoreCategoryNode).filter(EbayStoreCategoryNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="eBay store category node not found")
    db.delete(node)
    db.commit()
    return {"message": "Deleted", "id": node_id}
