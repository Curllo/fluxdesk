import os
from fastapi import HTTPException, Header
from fastapi import status


async def verify_api_token(authorization: str = Header(...)):
    expected = os.environ.get("FLUXDESK_API_TOKEN", "dev-token")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    token = authorization[7:]
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AUTH_INVALID",
        )
    return token
