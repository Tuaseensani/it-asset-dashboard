"""
security.py - JWT creation and verification + FastAPI dependencies.

Tokens carry just the username and role. No password, ever.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from auth import get_user_by_username

load_dotenv()

JWT_SECRET         = os.getenv("JWT_SECRET")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in .env")

# tokenUrl points at the login endpoint we'll create next.
# FastAPI uses this for the Swagger "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def create_token(username: str, role: str) -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub":  username,
        "role": role,
        "iat":  int(now.timestamp()),
        "exp":  int((now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Return the payload if valid, or None if invalid/expired."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency. Extracts the token, validates it, and
    returns the corresponding Users row from SQL Server.
    Raises 401 if the token is missing/invalid or the user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    username = payload.get("sub")
    if not username:
        raise credentials_exception

    user = get_user_by_username(username)
    if user is None or not user["IsActive"]:
        raise credentials_exception

    return user


def require_role(*allowed_roles: str):
    """
    Dependency factory. Use as:  Depends(require_role("Admin", "Manager"))
    Raises 403 if the current user's AppRole is not in the allowed list.
    """
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["AppRole"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker