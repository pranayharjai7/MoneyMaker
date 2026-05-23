from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import Settings, get_settings


security = HTTPBearer(auto_error=True)
security_optional = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None
    role: str | None
    claims: dict[str, Any]


class SupabaseJWTVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._jwks_client: jwt.PyJWKClient | None = None

    def _decode_with_secret(self, token: str) -> dict[str, Any]:
        options = {"verify_aud": bool(self.settings.jwt_audience)}
        return jwt.decode(
            token,
            self.settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=self.settings.jwt_audience,
            options=options,
        )

    def _decode_with_jwks(self, token: str) -> dict[str, Any]:
        jwks_url = self.settings.effective_jwks_url
        if not jwks_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase JWT verification is not configured.",
            )
        if self._jwks_client is None:
            self._jwks_client = jwt.PyJWKClient(jwks_url)
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        options = {"verify_aud": bool(self.settings.jwt_audience)}
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            audience=self.settings.jwt_audience,
            options=options,
        )

    def verify(self, token: str) -> AuthUser:
        try:
            if self.settings.supabase_jwt_secret:
                claims = self._decode_with_secret(token)
            else:
                claims = self._decode_with_jwks(token)
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Supabase access token.",
            ) from exc

        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase access token is missing a subject.",
            )
        return AuthUser(
            id=str(user_id),
            email=claims.get("email"),
            role=claims.get("role"),
            claims=claims,
        )


@lru_cache
def get_jwt_verifier() -> SupabaseJWTVerifier:
    return SupabaseJWTVerifier(get_settings())


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    verifier: SupabaseJWTVerifier = Depends(get_jwt_verifier),
) -> AuthUser:
    return verifier.verify(credentials.credentials)


def get_dashboard_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    dashboard_key: str | None = Header(default=None, alias="X-Dashboard-Key"),
    verifier: SupabaseJWTVerifier = Depends(get_jwt_verifier),
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    """Authenticate internal quant dashboard via Supabase JWT or shared API key."""

    configured_key = (settings.dashboard_api_key or "").strip()
    if configured_key and dashboard_key and dashboard_key.strip() == configured_key:
        return AuthUser(
            id="dashboard-ops",
            email="ops@internal.local",
            role="dashboard",
            claims={"dashboard_auth": "api_key"},
        )

    if credentials and credentials.credentials:
        return verifier.verify(credentials.credentials)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Dashboard authentication required. Sign in with Supabase or send "
            "Authorization: Bearer <access_token> or X-Dashboard-Key."
        ),
    )
