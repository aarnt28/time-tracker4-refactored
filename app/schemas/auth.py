from __future__ import annotations

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    api_key: str = Field(..., alias="apiKey", min_length=1)

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {"apiKey": "super-secret-key"}
        },
    }


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "<jwt>",
                "refresh_token": "<jwt>",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    }


class RefreshRequest(BaseModel):
    refresh_token: str

    model_config = {
        "json_schema_extra": {
            "example": {"refresh_token": "<jwt>"}
        }
    }
