"""
LangGraph authentication handler for JWT/JWKS validation.

This replaces the FastAPI AuthMiddleware for LangGraph Server.
"""
import time
import os
from typing import List, Dict, Any, Optional
import httpx
from jwt import decode, get_unverified_header, InvalidTokenError, ExpiredSignatureError, PyJWK
from pydantic import BaseModel
from langgraph_sdk import Auth

# Initialize the auth system
auth = Auth()

class JWKPayload(BaseModel):
    """Model for JWKS response payload."""
    keys: List[dict]

class LangGraphJWKProvider:
    """
    LangGraph-compatible JWT/JWKS authentication provider.
    
    This class handles JWT token validation using JWKS endpoints,
    similar to the existing JWKProvider but adapted for LangGraph.
    """
    
    HEADERS = {"Accept": "application/json"}
    
    def __init__(self):
        # Load configuration from environment variables
        self.jwks_url = os.getenv("PF_JWKS")
        self.issuer = os.getenv("PF_ISSUER")
        self.audience = os.getenv("PF_AUDIENCE")
        self.algorithms = ["RS256"]
        
        if not all([self.jwks_url, self.issuer, self.audience]):
            raise ValueError(
                "PF_JWKS, PF_ISSUER, and PF_AUDIENCE environment variables must be set"
            )
        
        # Ensure URLs are strings (not None)
        self.jwks_url = str(self.jwks_url)
        self.issuer = str(self.issuer)
        self.audience = str(self.audience)
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token using JWKS.
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing decoded token payload
            
        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token is expired
        """
        try:
            # Decode the token header to extract the 'kid'
            unverified_header = get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise InvalidTokenError("No 'kid' found in token header")
            
            # Get the signing key
            pyjwk = await self._get_signing_key_from_kid(kid)
            
            # Verify and decode the token
            payload = decode(
                token,
                pyjwk.key,  # Use the .key property of PyJWK
                algorithms=self.algorithms,
                issuer=self.issuer,
                audience=self.audience
            )
            
            # Additional validation
            if payload.get("aud") != self.audience:
                raise InvalidTokenError("Invalid audience")
            if payload.get("iss") != self.issuer:
                raise InvalidTokenError("Invalid issuer")
            if payload.get("exp", 0) < time.time():
                raise ExpiredSignatureError("Token has expired")
                
            return payload
            
        except Exception as e:
            raise InvalidTokenError(f"Token validation failed: {str(e)}")
    
    async def _get_signing_key_from_kid(self, kid: str) -> PyJWK:
        """Get the signing key for the given key ID."""
        for key in await self._get_signing_keys():
            if key.key_id == kid:
                return key
        raise InvalidTokenError(f"No matching JWK found for kid: {kid}")
    
    async def _get_signing_keys(self) -> List[PyJWK]:
        """Fetch and parse signing keys from JWKS endpoint."""
        if not self.jwks_url:
            raise InvalidTokenError("JWKS URL not configured")
            
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_url, headers=self.HEADERS)
            response.raise_for_status()
            
            jwk_payload = JWKPayload(**response.json())
            pyjwk_keys: List[PyJWK] = []
            for key in jwk_payload.keys:
                pyjwk_keys.append(PyJWK(key))
            return pyjwk_keys


# Initialize the provider lazily
_jwk_provider = None

def get_jwk_provider() -> LangGraphJWKProvider:
    """Get or create the JWK provider instance."""
    global _jwk_provider
    if _jwk_provider is None:
        _jwk_provider = LangGraphJWKProvider()
    return _jwk_provider


@auth.authenticate
async def authenticate(authorization: Optional[str] = None) -> Auth.types.MinimalUserDict:
    """
    LangGraph authentication handler.
    
    This function is called by LangGraph for every request to validate
    the user's credentials and return user information.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        
    Returns:
        MinimalUserDict containing user identity and permissions
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token from Authorization header
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # Verify the token
        jwk_provider = get_jwk_provider()
        payload = await jwk_provider.verify_token(token)
        
        # Extract user information from token
        user_id = payload.get("sub")
        if not user_id:
            raise Auth.exceptions.HTTPException(
                status_code=401,
                detail="Token missing 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # You can extract additional information from the token payload
        # and add it to the user object as needed
        permissions = payload.get("permissions", [])
        
        # Return user information that will be available in authorization handlers
        return {
            "identity": user_id,
            "is_authenticated": True,
            "permissions": permissions,
            "display_name": payload.get("name", user_id)
        }
        
    except ExpiredSignatureError:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except InvalidTokenError as e:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Authorization handlers for different resources
@auth.on
async def authorize_default(ctx: Auth.types.AuthContext, value: Any) -> bool:
    """
    Default authorization handler for all resources.
    
    This allows authenticated users to access all resources.
    You can customize this based on your authorization requirements.
    """
    # Allow all authenticated users by default
    # You can implement more sophisticated authorization logic here
    return True


# Example: More specific authorization for different resources
@auth.on.threads.create
async def authorize_thread_create(
    ctx: Auth.types.AuthContext, 
    value: Auth.types.on.threads.create.value
) -> Dict[str, Any]:
    """
    Authorization handler for thread creation.
    
    Adds user ownership metadata to threads.
    """
    # Add metadata to track thread ownership
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user.identity
    metadata["created_by"] = ctx.user.identity
    
    # Return filter for this user's threads
    return {"owner": ctx.user.identity}


@auth.on.threads.read
async def authorize_thread_read(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.read.value
) -> Dict[str, Any]:
    """
    Authorization handler for thread reading.
    
    Ensures users can only read their own threads.
    """
    # Filter to show only threads owned by this user
    return {"owner": ctx.user.identity}


@auth.on.threads.create_run
async def authorize_run_create(
    ctx: Auth.types.AuthContext,
    value: Auth.types.on.threads.create_run.value
) -> Dict[str, Any]:
    """
    Authorization handler for run creation.
    
    Inherits thread ownership and adds run metadata.
    """
    # Add metadata to track run ownership
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user.identity
    metadata["created_by"] = ctx.user.identity
    
    # Return filter for this user's resources
    return {"owner": ctx.user.identity}
