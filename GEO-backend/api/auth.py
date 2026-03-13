import os
import logging
from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, Depends, Header, Cookie, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from services.database_manager import (
    get_user_by_email,
    get_user_by_id,
    signup_user,
    get_subscription_status
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# ============= REQUEST MODELS =============
class SignUpRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    token: str

# ============= AUTHENTICATION HELPERS =============
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def create_jwt_token(user_id: str) -> str:
    """Create a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT may return bytes in some versions; ensure string is returned
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

def verify_jwt_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the user_id"""
    if not token:
        return None

    # Sanitize token (strip surrounding quotes/whitespace which can appear from bad storage)
    token = token.strip().strip('"').strip("'")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError as e:
        logger.info(f"JWT expired: {str(e)}")
        return None
    except jwt.InvalidTokenError as e:
        logger.info(f"Invalid JWT: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {str(e)}")
        return None

def get_current_user(authorization: Optional[str] = Header(None), token_cookie: Optional[str] = Cookie(None)) -> str:
    """Dependency to get current authenticated user. Accepts Authorization header or a 'token' cookie as fallback."""
    logger.info(f"Checking auth - Header present: {bool(authorization)}; Cookie token present: {bool(token_cookie)}")

    # If no Authorization header is provided but we have a token cookie, construct a Bearer header
    if not authorization and token_cookie:
        authorization = f"Bearer {token_cookie}"

    if not authorization:
        logger.info("Authorization missing in both header and cookie")
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Try to extract raw token for a masked preview (do NOT log the full token)
    raw_token = None
    try:
        parts = authorization.split()
        if len(parts) != 2:
            logger.info("Invalid auth header format")
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        scheme, token = parts
        if scheme.lower() != "bearer":
            logger.info(f"Invalid auth scheme: {scheme}")
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        raw_token = token
    except ValueError:
        logger.info("Invalid authorization header (ValueError)")
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    # Masked preview for debugging (length & format) - keeps token secret
    if raw_token:
        preview = (raw_token[:10] + '...') if len(raw_token) > 16 else raw_token
        logger.info(f"Auth token preview: {preview}; length={len(raw_token)}; dots={raw_token.count('.')}")

    # Sanitize token and verify
    raw_token = raw_token.strip().strip('"').strip("'") if raw_token else raw_token

    user_id = verify_jwt_token(raw_token)
    logger.info(f"Token verification result: {'valid' if user_id else 'invalid/expired'}")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id

# ============= AUTHENTICATION ENDPOINTS =============
@router.post("/auth/signup")
async def signup(request: SignUpRequest):
    """Register a new user"""
    try:
        if not request.email or not request.password:
            raise HTTPException(status_code=400, detail="Email and password are required")
        
        if len(request.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Check if user already exists
        existing_user = get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")
        
        # Hash password and create user
        password_hash = hash_password(request.password)
        user_id = signup_user(request.email, password_hash)
        
        if not user_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Create JWT token
        token = create_jwt_token(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "email": request.email,
            "token": token,
            "message": "User registered successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@router.post("/auth/login")
async def login(request: LoginRequest):
    """Login user and return JWT token"""
    try:
        if not request.email or not request.password:
            raise HTTPException(status_code=400, detail="Email and password are required")
        
        # Get user from database
        user = get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(request.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create JWT token
        token = create_jwt_token(user['id'])
        
        # Fetch subscription status to return alongside token
        sub_status = get_subscription_status(user['id'])

        return {
            "status": "success",
            "user_id": user['id'],
            "email": user['email'],
            "token": token,
            "subscription": sub_status,
            "message": "Login successful"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/auth/google")
async def google_auth(request: GoogleAuthRequest):
    """Verify Google token and login/signup user"""
    try:
        # Verify the Google token
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="Google Client ID not configured")
            
        try:
            idinfo = id_token.verify_oauth2_token(
                request.token, 
                google_requests.Request(), 
                client_id
            )
            
            # ID token is valid. Get the user's Google ID and email
            email = idinfo['email']
            google_id = idinfo['sub']
            
        except ValueError as e:
            # Invalid token
            logger.error(f"Invalid Google token: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid Google token")
        
        # Check if user already exists
        user = get_user_by_email(email)
        
        if not user:
            # Auto-signup for Google users
            # Use a placeholder hash since we don't have a password for Google users
            # The 'SOCIAL_AUTH' prefix helps identify these users
            placeholder_hash = "SOCIAL_AUTH_GOOGLE_" + google_id
            user_id = signup_user(email, placeholder_hash)
            
            if not user_id:
                raise HTTPException(status_code=500, detail="Failed to create user during Google sign-in")
                
            user = {"id": user_id, "email": email}
        
        # Create JWT token
        token = create_jwt_token(user['id'])

        # Fetch subscription status to return alongside token
        sub_status = get_subscription_status(user['id'])

        return {
            "status": "success",
            "user_id": user['id'],
            "email": user['email'],
            "token": token,
            "subscription": sub_status,
            "message": "Google Login successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")


@router.get("/auth/me")
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """Get current user information"""
    try:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "user": user
        }
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user info")

@router.get("/users/me")
async def get_current_user_info_alias(request: Request):
    """Alias for /api/auth/me — swallows calls from browser extensions silently."""
    # We bypass Depends(get_current_user) carefully so we don't spam the logs with 
    # "Checking auth..." and "Authorization missing" every time an extension hits this.
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        # Return 200 OK silently to prevent users from thinking the 401 log is a critical error
        return JSONResponse(status_code=200, content={"status": "not_logged_in", "user": None})
        
    try:
        token = auth_header.split()[1]
        user_id = verify_jwt_token(token)
        if not user_id:
            return JSONResponse(status_code=200, content={"status": "not_logged_in", "user": None})
            
        user = get_user_by_id(user_id)
        if not user:
            return JSONResponse(status_code=200, content={"status": "not_logged_in", "user": None})
            
        return {"status": "success", "user": user}
    except Exception:
        return JSONResponse(status_code=200, content={"status": "not_logged_in", "user": None})
