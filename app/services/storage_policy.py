"""
Storage Policy - Enforces file write rules to prevent repository bloat.

This module defines allowed storage directories and provides guardrails
to ensure runtime files are written only to gitignored subdirectories,
never to the attached_assets root.
"""

import os
from datetime import datetime, timedelta


# ============================================================================
# DIRECTORY CONSTANTS
# ============================================================================
ATTACHED_ASSETS_ROOT = "attached_assets"
TEMPLATE_DIR = "attached_assets/product_type_templates"
CUSTOMIZATION_DIR = "attached_assets/customization_templates"
EBAY_TEMPLATE_DIR = "attached_assets/ebay_templates"
REVERB_TEMPLATE_DIR = "attached_assets/reverb_templates"
EXPORT_DIR = "attached_assets/exports"
DEV_DIR = "attached_assets/dev_artifacts"
TMP_DIR = "attached_assets/tmp"


# ============================================================================
# STORAGE DIRECTORY MANAGEMENT
# ============================================================================
def ensure_storage_dirs_exist() -> None:
    """
    Create storage directories if they don't exist.
    Deterministic, no side effects beyond directory creation.
    """
    directories = [
        TEMPLATE_DIR,
        CUSTOMIZATION_DIR,
        EBAY_TEMPLATE_DIR,
        REVERB_TEMPLATE_DIR,
        EXPORT_DIR,
        DEV_DIR,
        TMP_DIR,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# ============================================================================
# WRITE PATH VALIDATION
# ============================================================================
def assert_allowed_write_path(path: str) -> None:
    """
    Assert that a file path is allowed for writing.
    
    Prevents writes to attached_assets root to avoid repository bloat.
    Only allows writes to designated subdirectories that are gitignored.
    
    Args:
        path: File path to validate
        
    Raises:
        ValueError: If path is not in an allowed directory
    """
    # Normalize path separators to forward slashes for consistent comparison
    normalized_path = path.replace("\\", "/")
    
    # Define allowed path prefixes
    allowed_prefixes = [
        TEMPLATE_DIR + "/",
        CUSTOMIZATION_DIR + "/",
        EBAY_TEMPLATE_DIR + "/",
        REVERB_TEMPLATE_DIR + "/",
        EXPORT_DIR + "/",
        DEV_DIR + "/",
        TMP_DIR + "/",
    ]
    
    # Check if path starts with any allowed prefix
    is_allowed = any(normalized_path.startswith(prefix) for prefix in allowed_prefixes)
    
    if not is_allowed:
        raise ValueError(
            f"Storage Policy Violation: Cannot write to '{path}'. "
            f"Files must be written to one of the following directories: "
            f"{TEMPLATE_DIR}/, {CUSTOMIZATION_DIR}/, {EBAY_TEMPLATE_DIR}/, {REVERB_TEMPLATE_DIR}/, {EXPORT_DIR}/, {DEV_DIR}/, {TMP_DIR}/"
        )


# ============================================================================
# CUSTOMIZATION TEMPLATE PATH HELPERS
# ============================================================================
def get_customization_template_paths(template_id: int) -> tuple[str, str]:
    """
    Return canonical and backup paths for an Amazon Customization Template.

    Canonical format mirrors product type templates (deterministic, collision-safe):
      Customization_<template_id>(Template).xlsx

    Args:
        template_id: AmazonCustomizationTemplate.id

    Returns:
        (canonical_path, backup_path)
    """
    canonical_filename = f"Customization_{template_id}(Template).xlsx"
    backup_filename = f"Customization_{template_id}(Template)_BACKUP.xlsx"
    canonical_path = os.path.join(CUSTOMIZATION_DIR, canonical_filename)
    backup_path = os.path.join(CUSTOMIZATION_DIR, backup_filename)
    return canonical_path, backup_path


def rotate_customization_template_backup(canonical_path: str, backup_path: str) -> None:
    """
    Rotate an existing canonical customization template into a single backup copy.

    Behavior:
    - If canonical exists, move it to backup (overwriting any existing backup).
    - If canonical does not exist, do nothing.
    """
    try:
        if os.path.exists(canonical_path):
            # Remove old backup first so os.replace is deterministic across platforms
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.replace(canonical_path, backup_path)
            print(f"[CUSTOMIZATION_ROTATION] Moved {canonical_path} -> {backup_path}")
    except Exception as e:
        # Do not crash API calls; log and continue (mirrors existing cleanup approach)
        print(f"[CUSTOMIZATION_ROTATION] Error rotating backup: {e}")


# ============================================================================
# TEMPORARY FILE CLEANUP
# ============================================================================
def cleanup_tmp_dir(max_age_days: int = 7) -> int:
    """
    Delete files in TMP_DIR older than max_age_days.
    
    Args:
        max_age_days: Maximum age in days for files to keep
        
    Returns:
        Number of files deleted
    """
    if not os.path.exists(TMP_DIR):
        return 0
    
    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    
    try:
        for filename in os.listdir(TMP_DIR):
            file_path = os.path.join(TMP_DIR, filename)
            
            # Only delete files, not directories
            if not os.path.isfile(file_path):
                continue
            
            # Check file age
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < cutoff_time:
                os.remove(file_path)
                deleted_count += 1
    except Exception as e:
        # Log error but don't crash
        print(f"[STORAGE_POLICY] Error during tmp cleanup: {e}")
    
    return deleted_count


# ============================================================================
# EBAY TEMPLATE PATH HELPERS
# ============================================================================
def get_ebay_template_paths() -> tuple[str, str]:
    """
    Return canonical and backup paths for the single eBay template.
    
    Returns:
        (canonical_path, backup_path)
    """
    canonical_filename = "ebay_template.xlsx"
    backup_filename = "ebay_template_BACKUP.xlsx"
    canonical_path = os.path.join(EBAY_TEMPLATE_DIR, canonical_filename)
    backup_path = os.path.join(EBAY_TEMPLATE_DIR, backup_filename)
    return canonical_path, backup_path


def rotate_ebay_template_backup(canonical_path: str, backup_path: str) -> None:
    """
    Rotate existing canonical eBay template into a single backup copy.
    """
    try:
        if os.path.exists(canonical_path):
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.replace(canonical_path, backup_path)
            print(f"[EBAY_ROTATION] Moved {canonical_path} -> {backup_path}")
    except Exception as e:
        print(f"[EBAY_ROTATION] Error rotating backup: {e}")


def get_reverb_template_paths(template_id: int, extension: str = ".csv") -> tuple[str, str]:
    """
    Return canonical and backup paths for a Reverb template row.

    Args:
        template_id: ReverbTemplate.id
        extension: File extension including dot (e.g. ".csv", ".xlsx")

    Returns:
        (canonical_path, backup_path)
    """
    ext = str(extension or ".csv").strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    canonical_filename = f"Reverb_{int(template_id)}(Template){ext}"
    backup_filename = f"Reverb_{int(template_id)}(Template)_BACKUP{ext}"
    canonical_path = os.path.join(REVERB_TEMPLATE_DIR, canonical_filename)
    backup_path = os.path.join(REVERB_TEMPLATE_DIR, backup_filename)
    return canonical_path, backup_path


def rotate_reverb_template_backup(canonical_path: str, backup_path: str) -> None:
    """
    Rotate existing canonical Reverb template into a single backup copy.
    """
    try:
        if os.path.exists(canonical_path):
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.replace(canonical_path, backup_path)
            print(f"[REVERB_ROTATION] Moved {canonical_path} -> {backup_path}")
    except Exception as e:
        print(f"[REVERB_ROTATION] Error rotating backup: {e}")
