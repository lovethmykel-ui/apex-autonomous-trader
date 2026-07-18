"""
Apex Autonomous Trader — Auth Router
======================================
Simple authentication for the web dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from apps.api.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.password != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    # Simple static token for dashboard access
    return {"access_token": settings.SECRET_KEY, "token_type": "bearer"}

def verify_token(token: str):
    if token != settings.SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True
