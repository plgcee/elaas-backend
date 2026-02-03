import hashlib
import time
from supabase import Client, create_client
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, RegisterResponse, SetSuperUserRequest
from app.config.settings import settings
from fastapi import HTTPException
from typing import Dict, Any

# In-memory cache for get_current_user to reduce Supabase auth calls (e.g. many parallel requests with same token)
_AUTH_USER_CACHE: Dict[str, tuple] = {}
_AUTH_CACHE_TTL_SEC = 60
_AUTH_CACHE_MAX_SIZE = 500


class AuthService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def register(self, register_data: RegisterRequest) -> RegisterResponse:
        """Register a new user using Supabase Auth"""
        try:
            # Prepare user metadata
            user_metadata = {}
            if register_data.full_name:
                user_metadata["full_name"] = register_data.full_name
            
            # Sign up user with Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": register_data.email,
                "password": register_data.password,
                "options": {
                    "data": user_metadata
                }
            })
            
            if not auth_response.user:
                raise HTTPException(status_code=400, detail="Failed to register user")
            
            return RegisterResponse(
                user_id=auth_response.user.id,
                email=auth_response.user.email or register_data.email,
                message="User registered successfully"
            )
        except Exception as e:
            error_message = str(e)
            if "already registered" in error_message.lower() or "already exists" in error_message.lower():
                raise HTTPException(status_code=400, detail="User already exists")
            raise HTTPException(status_code=500, detail=f"Registration failed: {error_message}")
    
    def login(self, login_data: LoginRequest) -> TokenResponse:
        """Authenticate user using Supabase Auth"""
        try:
            # Sign in with password
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            
            if not auth_response.user or not auth_response.session:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            return TokenResponse(
                access_token=auth_response.session.access_token,
                token_type="bearer",
                user_id=auth_response.user.id,
                email=auth_response.user.email or login_data.email
            )
        except Exception as e:
            error_message = str(e)
            if "invalid" in error_message.lower() or "credentials" in error_message.lower():
                raise HTTPException(status_code=401, detail="Invalid email or password")
            raise HTTPException(status_code=500, detail=f"Login failed: {error_message}")
    
    def get_current_user(self, token: str) -> Dict[str, Any]:
        """Get current user details from Supabase Auth token. Uses short TTL cache to reduce auth API calls."""
        try:
            cache_key = hashlib.sha256(token.encode()).hexdigest()
            now = time.monotonic()
            if cache_key in _AUTH_USER_CACHE:
                user_data, expiry = _AUTH_USER_CACHE[cache_key]
                if now < expiry:
                    return user_data
                del _AUTH_USER_CACHE[cache_key]
            user_response = self.supabase.auth.get_user(jwt=token)
            if not user_response.user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            user = user_response.user
            user_data = {
                "id": user.id,
                "email": user.email,
                "user_metadata": user.user_metadata or {},
                "app_metadata": user.app_metadata or {},
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            if len(_AUTH_USER_CACHE) < _AUTH_CACHE_MAX_SIZE:
                _AUTH_USER_CACHE[cache_key] = (user_data, now + _AUTH_CACHE_TTL_SEC)
            return user_data
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e)
            if "JWT" in error_msg or "expired" in error_msg.lower() or "invalid" in error_msg.lower():
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    def logout(self, token: str) -> bool:
        """Logout user using Supabase Auth"""
        try:
            # Sign out the user
            # Note: Supabase Auth tokens are stateless JWTs, so logout is mainly client-side
            # The token will naturally expire based on its expiration time
            self.supabase.auth.sign_out()
            return True
        except Exception:
            return False
    
    def set_super_user(self, user_id: str, is_super_user: bool = True) -> bool:
        """Set super_user status in app_metadata (requires service role key)"""
        try:
            # Use service role client for admin operations
            # Note: This requires SUPABASE_SERVICE_ROLE_KEY in environment
            service_role_key = getattr(settings, 'supabase_service_role_key', None)
            if not service_role_key:
                raise HTTPException(
                    status_code=500,
                    detail="Service role key not configured. Cannot update app_metadata."
                )
            
            # Create admin client with service role key
            admin_client = create_client(settings.supabase_url, service_role_key)
            
            # Update app_metadata
            app_metadata = {"type": "super_user"} if is_super_user else {}
            
            # Use Supabase Admin API to update user
            response = admin_client.auth.admin.update_user_by_id(
                user_id,
                {"app_metadata": app_metadata}
            )
            
            if not response.user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return True
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update super_user status: {str(e)}"
            )
