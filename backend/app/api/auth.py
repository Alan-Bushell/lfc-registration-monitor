import logging
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
from google.oauth2 import id_token
from google.auth.transport import requests

router = APIRouter()
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/calendar.events"]

# In prod this should match your registered redirect URI exactly
REDIRECT_URI = settings.REDIRECT_URI

@router.get("/login")
def login():
    # Build a standard web OAuth URL (no PKCE) to keep callback exchange stateless on Cloud Run.
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"url": url}

@router.post("/callback")
async def callback(payload: dict, db: AsyncSession = Depends(get_db)):
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    
    try:
        # Exchange auth code for tokens using direct token endpoint call.
        # This avoids PKCE verifier state issues in stateless deployments.
        token_res = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=20.0,
        )
        token_data = token_res.json()
        if token_res.status_code != 200:
            logger.error("Google token exchange failed. status=%s redirect_uri=%s response=%s", token_res.status_code, REDIRECT_URI, token_data)
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_data}")

        id_token_jwt = token_data.get("id_token")
        refresh_token = token_data.get("refresh_token")
        if not id_token_jwt:
            raise HTTPException(status_code=400, detail="Missing id_token in token response")

        id_info = id_token.verify_oauth2_token(id_token_jwt, requests.Request(), GOOGLE_CLIENT_ID)
        email = id_info.get("email")
        
        # Upsert User
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            user = User(email=email, google_refresh_token=refresh_token)
            db.add(user)
        elif refresh_token:
            user.google_refresh_token = refresh_token
            
        await db.commit()
        await db.refresh(user)
        
        return {"user": user.email, "status": user.subscription_status, "id": user.id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
