"""
Normalization utilities for marketplace and identifier matching.

Provides centralized, deterministic normalization for:
- Marketplace names (case-insensitive, whitespace-safe)
- Identifiers (type-safe, whitespace-safe)

Used by:
- GET /api/models/marketplace-lookup
- Order line → model auto-resolution
- Future invoice / packing slip logic
"""
from typing import Optional, Union


def normalize_marketplace(value: Optional[str]) -> Optional[str]:
    """
    Normalize marketplace name for case-insensitive, whitespace-safe matching.
    
    Examples:
        "Reverb" -> "reverb"
        " REVERB " -> "reverb"
        "eBay" -> "ebay"
        None -> None
        "" -> None
    """
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized if normalized else None


def normalize_identifier(value: Optional[Union[str, int]]) -> Optional[str]:
    """
    Normalize identifier for type-safe, whitespace-safe matching.
    Casts everything to string and strips whitespace.
    
    Examples:
        "77054514" -> "77054514"
        77054514 -> "77054514"
        " 77054514 " -> "77054514"
        None -> None
        "" -> None
    """
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized else None
