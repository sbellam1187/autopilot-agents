"""
FastAPI authentication dependency using LangGraph authentication logic.

This provides a FastAPI-compatible authentication system that reuses
the JWT/JWKS validation logic from the LangGraph authentication module.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import the LangGraph JWT provider
from app.auth.langgraph_auth import get_jwk_provider
from jwt import InvalidTokenError, ExpiredSignatureError


# Initialize FastAPI HTTP Bearer security
security = HTTPBearer()


class FastAPIAuthProvider:
    """
    FastAPI authentication provider that reuses LangGraph JWT validation logic.
    """
    
    def __init__(self):
        # Use lazy loading for the JWK provider
        self._jwk_provider = None
    
    @property
    def jwk_provider(self):
        """Lazy-load the JWK provider."""
        if self._jwk_provider is None:
            self._jwk_provider = get_jwk_provider()
        return self._jwk_provider
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """
        Verify JWT token and return user information.
        
        Args:
            credentials: FastAPI HTTPAuthorizationCredentials containing the token
            
        Returns:
            Dict containing user authentication information
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Use the same JWT validation logic as LangGraph
            payload = await self.jwk_provider.verify_token(credentials.credentials)
            
            # Extract user information from token
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing 'sub' claim",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Return user information in a format compatible with FastAPI
            return {
                "identity": user_id,
                "is_authenticated": True,
                "permissions": payload.get("permissions", []),
                "display_name": payload.get("name", user_id),
                "token_payload": payload
            }
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"}
            )


# Initialize the provider
auth_provider = FastAPIAuthProvider()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user.
    
    This can be used as a dependency in FastAPI route handlers to ensure
    the user is authenticated and to get user information.
    
    Args:
        credentials: HTTP Bearer credentials (injected by FastAPI)
        
    Returns:
        Dict containing user authentication information
        
    Example:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['display_name']}"}
    """
    return await auth_provider.verify_token(credentials)


async def get_auth_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency to get the raw authentication token.
    
    This can be used when you need to pass the token to other services
    or include it in agent configurations.
    
    Args:
        credentials: HTTP Bearer credentials (injected by FastAPI)
        
    Returns:
        The raw JWT token string (without 'Bearer ' prefix)
    """
    # Verify the token first to ensure it's valid
    await auth_provider.verify_token(credentials)
    # Return the raw token (without Bearer prefix)
    return credentials.credentials


async def get_auth_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency to get the full Authorization header value.
    
    This returns the complete "Bearer <token>" string that can be directly
    used in HTTP Authorization headers for other services.
    
    Args:
        credentials: HTTP Bearer credentials (injected by FastAPI)
        
    Returns:
        The full Authorization header value ("Bearer <token>")
    """
    # Verify the token first to ensure it's valid
    await auth_provider.verify_token(credentials)
    # Return the full authorization header
    return f"{credentials.scheme} {credentials.credentials}"


# Optional: Dependency for getting user ID only
async def get_user_id(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    FastAPI dependency to get just the user ID.
    
    Args:
        user: User information (injected by get_current_user dependency)
        
    Returns:
        User identity string
    """
    return user["identity"]
