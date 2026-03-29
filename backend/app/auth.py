import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


def hash_password(plain: str) -> str:
    """PBKDF2-SHA256 hash using JWT_SECRET_KEY as salt. Returns hex string."""
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), settings.JWT_SECRET_KEY.encode(), 600_000)
    return dk.hex()


def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(plain), hashed)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expire}, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    """Decode token and return username. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    username: str | None = payload.get("sub")
    if username != settings.APP_USERNAME:
        raise JWTError("Invalid subject")
    return username


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        return verify_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
