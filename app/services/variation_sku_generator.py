"""
eBay Variation SKU Generator Service

Deterministic generation and persistence of child variation SKUs for models.

DEPRECATED / legacy service:
Persisted child variation SKUs are not authoritative for eBay export.
eBay child SKUs are computed at export time; parent SKU is the only persistent SKU.
"""

from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
import json
import re

from app.models.core import (
    Model, Material, MaterialColourSurcharge, DesignOption,
    EquipmentTypeDesignOption, ModelVariationSKU,
    MaterialRoleAssignment, MaterialRoleConfig
)


def parse_sku_slot_region(base_sku: str) -> Tuple[str, str, str]:
    """
    Parse SKU to extract prefix, version marker, and tail region.
    
    Args:
        base_sku: The canonical SKU (e.g., "CASIOXXX-CASIOTON-CTS1XXXXXXXXXV10000000")
    
    Returns:
        Tuple of (prefix_before_v, version_marker, tail_region)
        Example: ("CASIOXXX-CASIOTON-CTS1XXXXXXXXXV", "1", "0000000")
    
    Raises:
        ValueError: If V{digit} pattern not found or tail is too short
    """
    # Find first occurrence of V followed by digit(s)
    match = re.search(r'V(\d+)', base_sku)
    
    if not match:
        raise ValueError(
            f"SKU '{base_sku}' does not contain V{{digit}} pattern. "
            "Expected format like 'PREFIX-V1-TAIL' or 'PREFIXV10000000'."
        )
    
    v_pos = match.start()
    version_digits = match.group(1)
    tail_start = match.end()
    
    prefix = base_sku[:v_pos + 1]  # Include the 'V'
    tail = base_sku[tail_start:]
    
    if len(tail) < 7:
        raise ValueError(
            f"SKU tail region after V{version_digits} is only {len(tail)} characters. "
            f"Expected at least 7 characters for variation encoding. SKU: '{base_sku}'"
        )
    
    return prefix, version_digits, tail


def get_enabled_material_role_configs(db: Session) -> List[MaterialRoleConfig]:
    """
    Get material role configs enabled for eBay variations with abbreviations.
    
    Returns:
        List of MaterialRoleConfig objects, ordered by sort_order ASC, then role ASC
    """
    return db.query(MaterialRoleConfig).filter(
        MaterialRoleConfig.ebay_variation_enabled == True,
        (
            (MaterialRoleConfig.sku_abbrev_no_padding.isnot(None) & (MaterialRoleConfig.sku_abbrev_no_padding != "")) |
            (MaterialRoleConfig.sku_abbrev_with_padding.isnot(None) & (MaterialRoleConfig.sku_abbrev_with_padding != ""))
        )
    ).order_by(
        MaterialRoleConfig.sort_order.asc(),
        MaterialRoleConfig.role.asc()
    ).all()


def get_assigned_material_for_role(db: Session, role: str) -> Optional[Material]:
    """
    Get the active assigned material for a given role.
    
    Args:
        role: The role string (e.g., "CHOICE_WATERPROOF_FABRIC")
    
    Returns:
        Material object if an active assignment exists, None otherwise
    """
    # Find the most recent active assignment for this role
    # Filter by end_date IS NULL to get active assignments
    assignment = db.query(MaterialRoleAssignment).filter(
        MaterialRoleAssignment.role == role,
        MaterialRoleAssignment.end_date.is_(None)
    ).order_by(
        MaterialRoleAssignment.effective_date.desc(),
        MaterialRoleAssignment.created_at.desc()
    ).first()
    
    if not assignment:
        return None
    
    # Get the material
    material = db.query(Material).filter(
        Material.id == assignment.material_id
    ).first()
    
    return material


def get_enabled_colors_for_material(db: Session, material_id: int) -> List[MaterialColourSurcharge]:
    """Get enabled colors for a specific material."""
    return db.query(MaterialColourSurcharge).filter(
        MaterialColourSurcharge.material_id == material_id,
        MaterialColourSurcharge.ebay_variation_enabled == True,
        MaterialColourSurcharge.sku_abbreviation.isnot(None),
        MaterialColourSurcharge.sku_abbreviation != ''
    ).all()


def get_enabled_design_options_for_equipment(db: Session, equipment_type_id: int) -> List[DesignOption]:
    """Get pricing-relevant design options enabled for eBay variations, filtered by equipment type."""
    return db.query(DesignOption).join(
        EquipmentTypeDesignOption,
        DesignOption.id == EquipmentTypeDesignOption.design_option_id
    ).filter(
        EquipmentTypeDesignOption.equipment_type_id == equipment_type_id,
        DesignOption.is_pricing_relevant == True,
        DesignOption.ebay_variation_enabled == True,
        DesignOption.sku_abbreviation.isnot(None),
        DesignOption.sku_abbreviation != ''
    ).order_by(DesignOption.id).all()  # Deterministic ordering


def generate_option_combinations(options: List[DesignOption]) -> List[List[DesignOption]]:
    """
    Generate combinations: empty, singles, and pairs.
    
    Args:
        options: List of design options sorted by ID
    
    Returns:
        List of combinations, each combination is a list of DesignOptions
    """
    combinations = []
    
    # Base (no options)
    combinations.append([])
    
    # Singles
    for opt in options:
        combinations.append([opt])
    
    # Pairs
    for i in range(len(options)):
        for j in range(i + 1, len(options)):
            combinations.append([options[i], options[j]])
    
    return combinations


def build_variation_code(
    material_abbrev: str,
    color_abbrev: str,
    option_abbrevs: List[str],
    tail_length: int
) -> str:
    """
    Build variation code by concatenating abbreviations.
    
    Args:
        material_abbrev: Material abbreviation (e.g., "C")
        color_abbrev: Color abbreviation (e.g., "PBK")
        option_abbrevs: List of design option abbreviations
        tail_length: Available tail length (e.g., 7)
    
    Returns:
        Variation code padded/truncated to tail_length, or empty string if too long
    """
    code = material_abbrev + color_abbrev + ''.join(option_abbrevs)
    
    if len(code) > tail_length:
        return ''  # Signal to skip this combination
    
    # Pad with zeros to fill tail length
    return code.ljust(tail_length, '0')


def generate_and_persist_model_variation_skus(db: Session, model_id: int) -> int:
    """
    Generate and persist all variation SKUs for a model.
    
    This function:
    1. Loads the model and gets its canonical SKU
    2. Parses the SKU to find the variation slot region
    3. Queries enabled material role configs
    4. For each role, resolves the assigned material and its colors
    5. Generates all valid combinations (base + singles + pairs)
    6. Deletes existing variations for the model
    7. Inserts new variation records
    
    Args:
        db: Database session
        model_id: ID of the model to generate variations for
    
    Returns:
        Number of variation SKUs created
    
    Raises:
        ValueError: If model not found, canonical_sku missing, or SKU format invalid
        RuntimeError: If variation limit exceeded
    """
    MAX_VARIATIONS = 200
    
    # 1. Load model and validate canonical SKU
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise ValueError(f"Model with ID {model_id} not found")
    
    base_sku = model.canonical_sku
    if not base_sku:
        raise ValueError(
            f"Model '{model.name}' (ID {model_id}) does not have a canonical SKU. "
            "Set either parent_sku or sku_override before generating variations."
        )
    
    # 2. Parse SKU slot region
    try:
        prefix, version, tail = parse_sku_slot_region(base_sku)
        tail_length = len(tail)
    except ValueError as e:
        raise ValueError(f"Cannot parse SKU for model '{model.name}': {e}")
    
    # 3. Query enabled material role configs
    role_configs = get_enabled_material_role_configs(db)
    if not role_configs:
        raise ValueError(
            f"No material role configs are enabled for eBay variations. "
            "Set ebay_variation_enabled=true and sku_abbrev on at least one material_role_config."
        )
    
    design_options = get_enabled_design_options_for_equipment(db, model.equipment_type_id)
    
    # 4. Generate all combinations
    variations: List[Dict[str, Any]] = []
    
    for role_config in role_configs:
        # Resolve assigned material for this role
        material = get_assigned_material_for_role(db, role_config.role)
        
        if not material:
            print(
                f"Warning: Material role '{role_config.role}' has no active assignment, skipping"
            )
            continue
        
        colors = get_enabled_colors_for_material(db, material.id)
        
        if not colors:
            print(f"Warning: Material '{material.name}' (role: {role_config.role}) has no enabled colors, skipping")
            continue
        
        # Choose material abbreviation (for now, always use no_padding if available)
        material_abbrev = role_config.sku_abbrev_no_padding or role_config.sku_abbrev_with_padding
        
        if not material_abbrev:
            print(f"Warning: Material role '{role_config.role}' has no abbreviations, skipping")
            continue
        
        for color in colors:
            # Generate option combinations (empty, singles, pairs)
            option_combos = generate_option_combinations(design_options)
            
            for option_combo in option_combos:
                # Check limit
                if len(variations) >= MAX_VARIATIONS:
                    raise RuntimeError(
                        f"Variation limit of {MAX_VARIATIONS} exceeded for model '{model.name}'. "
                        f"Attempted: {len(variations) + 1}. Reduce enabled roles/colors/options."
                    )
                
                # Build variation code
                option_abbrevs = [opt.sku_abbreviation for opt in option_combo]
                variation_code = build_variation_code(
                    material_abbrev,
                    color.sku_abbreviation,
                    option_abbrevs,
                    tail_length
                )
                
                if not variation_code:  # Too long, skip
                    print(
                        f"Warning: Skipping combination - code too long: "
                        f"{material_abbrev}{color.sku_abbreviation}{''.join(option_abbrevs)} "
                        f"(max {tail_length} chars)"
                    )
                    continue
                
                # Build full variation SKU
                variation_sku = prefix + version + variation_code
                
                # Build payload
                payload = {
                    'base_sku': base_sku,
                    'material_role': role_config.role,
                    'material_role_abbreviation': material_abbrev,
                    'material_id': material.id,
                    'color_id': color.id,
                    'color_abbreviation': color.sku_abbreviation,
                    'design_option_ids': [opt.id for opt in option_combo],
                    'design_option_abbreviations': option_abbrevs
                }
                
                variations.append({
                    'variation_sku': variation_sku,
                    'payload': payload
                })
    
    if not variations:
        raise ValueError(
            f"No valid variations generated for model '{model.name}'. "
            "Check that material roles have active assignments with enabled colors."
        )
    
    # 5. Delete existing variations for this model
    db.query(ModelVariationSKU).filter(
        ModelVariationSKU.model_id == model_id
    ).delete()
    
    # 6. Insert new variations
    for var in variations:
        variation_record = ModelVariationSKU(
            model_id=model_id,
            variation_sku=var['variation_sku'],
            variation_payload=json.dumps(var['payload'])
        )
        db.add(variation_record)
    
    db.flush()  # Don't commit - let caller decide when to commit
    
    return len(variations)
