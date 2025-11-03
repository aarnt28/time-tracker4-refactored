from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from .config import settings

ALGORITHM = "HS256"
AUDIENCE = "time-tracker-clients"
ISSUER = "time-tracker"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    iat: datetime
    typ: str
    aud: str
    iss: str
    scope: str | None = None

    @property
    def scopes(self) -> list[str]:
        if not self.scope:
            return []
        return [segment.strip() for segment in self.scope.split() if segment.strip()]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _encode_token(subject: str, expires_delta: timedelta, token_type: str, scope: str | None = None) -> str:
    now = _now()
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "typ": token_type,
        "aud": AUDIENCE,
        "iss": ISSUER,
    }
    if scope:
        payload["scope"] = scope
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def issue_token_pair(subject: str, scope: str | None = None) -> TokenPair:
    access_delta = timedelta(minutes=settings.JWT_ACCESS_TTL_MIN)
    refresh_delta = timedelta(days=settings.JWT_REFRESH_TTL_DAYS)
    access_token = _encode_token(subject, access_delta, token_type="access", scope=scope)
    refresh_token = _encode_token(subject, refresh_delta, token_type="refresh", scope=scope)
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_delta.total_seconds()),
    )


def decode_token(token: str, *, verify_type: str | None = None) -> TokenPayload:
    try:
        decoded = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    try:
        payload = TokenPayload.model_validate(decoded)
    except ValidationError as exc:
        raise ValueError("Invalid token payload") from exc
    if verify_type and payload.typ != verify_type:
        raise ValueError("Invalid token type")
    return payload


def refresh_access_token(refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token, verify_type="refresh")
    return issue_token_pair(payload.sub, scope=payload.scope)
