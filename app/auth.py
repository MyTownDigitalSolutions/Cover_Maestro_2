from __future__ import annotations

from typing import Any
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.config import settings


class AuthError(Exception):
    pass


def _issuer() -> str:
    if settings.SUPABASE_JWT_ISSUER:
        return settings.SUPABASE_JWT_ISSUER.rstrip("/")
    return f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"


def _jwks_url() -> str:
    return f"{_issuer()}/.well-known/jwks.json"


_jwk_client = PyJWKClient(_jwks_url())


def _verify_via_supabase_user(token: str) -> dict[str, Any]:
    """
    Fallback verifier for projects that are not using asymmetric JWT keys.
    Validates token by calling Supabase Auth /user endpoint.
    """
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    req = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": settings.SUPABASE_KEY,
        },
    )

    try:
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise AuthError("Invalid or expired token") from exc
        raise AuthError(f"Token verification failed via Supabase: HTTP {exc.code}") from exc
    except URLError as exc:
        raise AuthError(f"Token verification failed via Supabase: {exc.reason}") from exc
    except Exception as exc:
        raise AuthError(f"Token verification failed via Supabase: {exc}") from exc

    if not isinstance(payload, dict) or not payload.get("id"):
        raise AuthError("Token verification failed via Supabase: invalid user payload")

    return payload


def verify_bearer_token(authorization_header: str | None) -> dict[str, Any]:
    if not authorization_header:
        raise AuthError("Missing Authorization header")

    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Invalid Authorization header format")

    claims: dict[str, Any]
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=_issuer(),
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except InvalidTokenError:
        claims = _verify_via_supabase_user(token)
    except Exception:
        claims = _verify_via_supabase_user(token)

    if settings.SUPABASE_OWNER_EMAIL:
        user_email = (claims.get("email") or "").lower()
        if user_email != settings.SUPABASE_OWNER_EMAIL.lower():
            raise AuthError("Forbidden for this account")

    return claims
