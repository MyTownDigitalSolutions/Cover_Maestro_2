"""
Marketplace Credentials API - Secure storage and management of API credentials.

Provides endpoints for:
- GET/PUT Reverb credentials (with admin key protection)
- Testing credentials against live API

Security:
- All endpoints require X-Admin-Key header matching ADMIN_KEY env var
- Tokens are masked by default unless ENABLE_CREDENTIALS_REVEAL=true
- Credentials stored encrypted if CREDENTIALS_MASTER_KEY is set
"""
import os
import json
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import MarketplaceCredential
from app.schemas.core import (
    ReverbCredentialsUpsertRequest,
    ReverbCredentialsResponse,
    CredentialsTestResponse,
)


router = APIRouter(prefix="/marketplace-credentials", tags=["marketplace-credentials"])


# ============================================================
# Configuration from environment
# ============================================================

ADMIN_KEY = os.getenv("ADMIN_KEY", "")
ENABLE_CREDENTIALS_REVEAL = os.getenv("ENABLE_CREDENTIALS_REVEAL", "false").lower() == "true"
CREDENTIALS_MASTER_KEY = os.getenv("CREDENTIALS_MASTER_KEY", "")
ALLOW_PLAINTEXT_CREDENTIALS = os.getenv("ALLOW_PLAINTEXT_CREDENTIALS", "false").lower() == "true"

# Masked token placeholder
MASKED_TOKEN = "********"


# ============================================================
# Admin Authentication Guard
# ============================================================

def verify_admin_key(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    """
    Dependency that verifies the X-Admin-Key header.
    Returns 401 if ADMIN_KEY is not configured or header doesn't match.
    """
    if not ADMIN_KEY:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_KEY environment variable not configured"
        )
    
    if not x_admin_key:
        raise HTTPException(
            status_code=401,
            detail="X-Admin-Key header required"
        )
    
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin key"
        )
    
    return True


# ============================================================
# Encryption/Decryption Helpers
# ============================================================

def _encrypt_secrets(data: dict) -> str:
    """Encrypt secrets dict to blob string."""
    json_str = json.dumps(data)
    
    if CREDENTIALS_MASTER_KEY:
        try:
            from cryptography.fernet import Fernet
            # Derive a Fernet key from the master key (must be 32 url-safe base64-encoded bytes)
            # For simplicity, we'll use the key directly if it's valid, or hash it
            import base64
            import hashlib
            
            # Hash the master key to get a consistent 32-byte key
            key_bytes = hashlib.sha256(CREDENTIALS_MASTER_KEY.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            
            f = Fernet(fernet_key)
            encrypted = f.encrypt(json_str.encode())
            return "encrypted:" + encrypted.decode()
        except ImportError:
            if not ALLOW_PLAINTEXT_CREDENTIALS:
                raise HTTPException(
                    status_code=500,
                    detail="Encryption required but cryptography library not installed. Set ALLOW_PLAINTEXT_CREDENTIALS=true to use plaintext."
                )
    
    if not ALLOW_PLAINTEXT_CREDENTIALS and not CREDENTIALS_MASTER_KEY:
        raise HTTPException(
            status_code=500,
            detail="Encryption required but CREDENTIALS_MASTER_KEY not configured. Set ALLOW_PLAINTEXT_CREDENTIALS=true to use plaintext."
        )
    
    # Return plaintext JSON
    return json_str


def _decrypt_secrets(blob: str) -> dict:
    """Decrypt blob string to secrets dict."""
    if blob.startswith("encrypted:"):
        if not CREDENTIALS_MASTER_KEY:
            raise HTTPException(
                status_code=500,
                detail="Cannot decrypt: CREDENTIALS_MASTER_KEY not configured"
            )
        try:
            from cryptography.fernet import Fernet
            import base64
            import hashlib
            
            key_bytes = hashlib.sha256(CREDENTIALS_MASTER_KEY.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            
            f = Fernet(fernet_key)
            encrypted_data = blob[len("encrypted:"):]
            decrypted = f.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Cannot decrypt: cryptography library not installed"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Decryption failed: {str(e)}"
            )
    
    # Plaintext JSON
    try:
        return json.loads(blob)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid credentials format: {str(e)}"
        )


def _mask_token(token: str) -> str:
    """Return masked token unless reveal is enabled."""
    if ENABLE_CREDENTIALS_REVEAL:
        return token
    return MASKED_TOKEN


# ============================================================
# Reverb Credentials Endpoints
# ============================================================

@router.get("/reverb", response_model=ReverbCredentialsResponse)
def get_reverb_credentials(
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """
    Get Reverb API credentials.
    
    Token is masked unless ENABLE_CREDENTIALS_REVEAL=true.
    Returns 404 if credentials not configured.
    """
    try:
        cred = db.query(MarketplaceCredential).filter(
            MarketplaceCredential.marketplace == "reverb"
        ).first()
        
        if not cred:
            raise HTTPException(
                status_code=404,
                detail="Reverb credentials not configured"
            )
        
        secrets = _decrypt_secrets(cred.secrets_blob)
        
        return ReverbCredentialsResponse(
            marketplace="reverb",
            is_enabled=cred.is_enabled,
            api_token=_mask_token(secrets.get("api_token", "")),
            base_url=secrets.get("base_url", "https://api.reverb.com"),
            updated_at=cred.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MARKETPLACE_CREDENTIALS] Error getting Reverb credentials: {repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/reverb", response_model=ReverbCredentialsResponse)
def upsert_reverb_credentials(
    data: ReverbCredentialsUpsertRequest,
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """
    Create or update Reverb API credentials.
    
    Credentials are encrypted if CREDENTIALS_MASTER_KEY is set.
    Token is masked in response unless ENABLE_CREDENTIALS_REVEAL=true.
    """
    try:
        # Build secrets JSON
        secrets = {
            "api_token": data.api_token,
            "base_url": data.base_url or "https://api.reverb.com"
        }
        
        # Encrypt the secrets
        secrets_blob = _encrypt_secrets(secrets)
        
        # Check for existing credential
        cred = db.query(MarketplaceCredential).filter(
            MarketplaceCredential.marketplace == "reverb"
        ).first()
        
        now = datetime.utcnow()
        
        if cred:
            # Update existing
            cred.is_enabled = data.is_enabled
            cred.secrets_blob = secrets_blob
            cred.updated_at = now
            print(f"[MARKETPLACE_CREDENTIALS] Updated Reverb credentials (id={cred.id})")
        else:
            # Create new
            cred = MarketplaceCredential(
                marketplace="reverb",
                is_enabled=data.is_enabled,
                label="Reverb API",
                secrets_blob=secrets_blob,
                created_at=now,
                updated_at=now
            )
            db.add(cred)
            print("[MARKETPLACE_CREDENTIALS] Created new Reverb credentials")
        
        db.commit()
        db.refresh(cred)
        
        # Return response (with masked or revealed token)
        return ReverbCredentialsResponse(
            marketplace="reverb",
            is_enabled=cred.is_enabled,
            api_token=_mask_token(data.api_token),
            base_url=secrets["base_url"],
            updated_at=cred.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MARKETPLACE_CREDENTIALS] Error upserting Reverb credentials: {repr(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reverb/test", response_model=CredentialsTestResponse)
def test_reverb_credentials(
    db: Session = Depends(get_db),
    _admin: bool = Depends(verify_admin_key)
):
    """
    Test stored Reverb credentials against live API.
    
    Makes a lightweight authenticated request to verify the token works.
    Returns account info on success, error message on failure.
    """
    try:
        # Load credentials from DB
        cred = db.query(MarketplaceCredential).filter(
            MarketplaceCredential.marketplace == "reverb"
        ).first()
        
        if not cred:
            return CredentialsTestResponse(
                ok=False,
                marketplace="reverb",
                status_code=404,
                error="Reverb credentials not configured"
            )
        
        secrets = _decrypt_secrets(cred.secrets_blob)
        api_token = secrets.get("api_token", "")
        base_url = secrets.get("base_url", "https://api.reverb.com")
        
        if not api_token:
            return CredentialsTestResponse(
                ok=False,
                marketplace="reverb",
                status_code=400,
                error="API token is empty"
            )
        
        # Make a test request to Reverb API
        import requests
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/hal+json",
            "Accept": "application/hal+json",
            "Accept-Version": "3.0"
        }
        
        # Use /my/account endpoint as a lightweight check
        test_url = f"{base_url.rstrip('/')}/api/my/account"
        
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            status_code = response.status_code
            
            if response.ok:
                account_data = response.json()
                # Extract safe account info (no sensitive data)
                safe_account = {
                    "shop_name": account_data.get("shop_name"),
                    "username": account_data.get("username"),
                    "email": account_data.get("email"),
                    "locale": account_data.get("locale"),
                }
                print(f"[MARKETPLACE_CREDENTIALS] Reverb test successful for shop: {safe_account.get('shop_name')}")
                return CredentialsTestResponse(
                    ok=True,
                    marketplace="reverb",
                    status_code=status_code,
                    account=safe_account
                )
            else:
                error_msg = response.text[:200] if response.text else f"HTTP {status_code}"
                print(f"[MARKETPLACE_CREDENTIALS] Reverb test failed: {status_code}")
                return CredentialsTestResponse(
                    ok=False,
                    marketplace="reverb",
                    status_code=status_code,
                    error=error_msg
                )
        except requests.exceptions.Timeout:
            return CredentialsTestResponse(
                ok=False,
                marketplace="reverb",
                status_code=408,
                error="Request timeout"
            )
        except requests.exceptions.RequestException as e:
            return CredentialsTestResponse(
                ok=False,
                marketplace="reverb",
                status_code=0,
                error=f"Connection error: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MARKETPLACE_CREDENTIALS] Error testing Reverb credentials: {repr(e)}")
        print(traceback.format_exc())
        return CredentialsTestResponse(
            ok=False,
            marketplace="reverb",
            status_code=500,
            error="Internal server error"
        )
