from fastapi import APIRouter, HTTPException

from ..auth import LoginRequest, TokenResponse, verify_password, create_access_token
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    if body.username != settings.APP_USERNAME or not verify_password(body.password, settings.APP_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(body.username)
    return TokenResponse(access_token=token)
