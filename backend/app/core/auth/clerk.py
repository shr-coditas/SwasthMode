from functools import lru_cache
from time import time

import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer = HTTPBearer(auto_error=False)


@lru_cache
def clerk_client() -> Clerk:
    return Clerk(bearer_auth=settings().clerk_secret_key.get_secret_value(),
                 client=httpx.Client(timeout=10))


def identity(request: Request, token: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    cfg = settings()
    if not token or token.scheme.lower() != "bearer":
        raise HTTPException(401, "Sign in to continue", headers={"WWW-Authenticate": "Bearer"})
    if not cfg.clerk_secret_key.get_secret_value() or not cfg.clerk_issuer:
        raise HTTPException(503, "Clerk backend configuration is required")
    try:
        verified = clerk_client().authenticate_request(
            httpx.Request("GET", str(request.url), headers={"Authorization": f"Bearer {token.credentials}"}),
            AuthenticateRequestOptions(
                authorized_parties=[cfg.frontend_origin], accepts_token=["session_token"],
                jwt_key=cfg.clerk_jwt_key.get_secret_value().replace("\\n", "\n") or None,
            ),
        )
    except Exception:
        raise HTTPException(401, "Session verification failed. Please sign in again") from None
    claims = verified.payload or {}
    # These checks are on SDK-verified claims, never an unverified JWT decode.
    if (not verified.is_signed_in or claims.get("iss") != cfg.clerk_issuer
            or claims.get("azp") != cfg.frontend_origin
            or not isinstance(claims.get("exp"), (int, float))
            or claims["exp"] <= time() or not claims.get("sid")
            or not isinstance(claims.get("sub"), str)):
        raise HTTPException(401, "Session expired or invalid. Please sign in again",
                            headers={"WWW-Authenticate": "Bearer"})
    return claims["sub"]
