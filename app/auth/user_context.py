"""
Helper functions for accessing user authentication context in LangGraph agents.
"""
from typing import Dict, Any, Optional
from langchain_core.runnables.config import RunnableConfig


def get_user_context(config: RunnableConfig) -> Optional[Dict[str, Any]]:
    """
    Extract user authentication context from LangGraph config.
    
    Args:
        config: LangGraph configuration passed to agent nodes
        
    Returns:
        Dictionary containing user authentication information, or None if not available
    """
    # In LangGraph, user auth context is stored in configurable
    configurable = config.get("configurable", {})
    return configurable.get("langgraph_auth_user")


def get_user_id(config: RunnableConfig) -> Optional[str]:
    """
    Get the authenticated user's identity from config.
    
    Args:
        config: LangGraph configuration passed to agent nodes
        
    Returns:
        User identity string, or None if not authenticated
    """
    user_ctx = get_user_context(config)
    return user_ctx.get("identity") if user_ctx else None


def get_user_permissions(config: RunnableConfig) -> list:
    """
    Get the authenticated user's permissions from config.
    
    Args:
        config: LangGraph configuration passed to agent nodes
        
    Returns:
        List of user permissions, empty list if not available
    """
    user_ctx = get_user_context(config)
    return user_ctx.get("permissions", []) if user_ctx else []


def get_auth_token(config: RunnableConfig) -> Optional[str]:
    """
    Extract authorization token from LangGraph configuration.
    
    Args:
        config: LangGraph configuration passed to agent nodes
        
    Returns:
        Authorization token if available, None otherwise
    """
    configurable = config.get("configurable", {})
    return configurable.get("authorization")


def require_user(config: RunnableConfig) -> tuple[Dict[str, Any], Optional[str]]:
    """
    Get user context, raising an error if user is not authenticated.
    
    Args:
        config: LangGraph configuration passed to agent nodes
        
    Returns:
        Tuple containing user authentication information and auth token
        
    Raises:
        ValueError: If user is not authenticated
    """
    user_ctx = get_user_context(config)
    user_token = get_auth_token(config)
    if not user_ctx:
        raise ValueError("User authentication required but not found in config")
    return user_ctx, user_token