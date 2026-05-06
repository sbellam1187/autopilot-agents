"""
Database utility library for encrypted API key management.
Provides functions to retrieve and manage encrypted API keys from the database.

This module handles:
- Database connection management using SQLAlchemy
- Encrypted API key retrieval and decryption
- Service-specific key management
- User authentication and authorization
- Error handling and logging

Database Schema:
- Table: public.mcp_keys
- Columns: id, user_id, service, api_key, expiration_date, updated_at, is_active
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from .database_factory import create_database_config, DatabaseConfig
from .encryption_utils import decrypt_token, EncryptionError
from .debug_utils import debug_print


class DatabaseKeyError(Exception):
    """Exception raised when database key operations fail."""
    pass


class ApiKeyManager:
    """Manager for encrypted API key operations."""
    
    def __init__(self, agent_name: str = "API_KEY_MANAGER"):
        """
        Initialize API key manager.
        
        Args:
            agent_name: Name of the agent for debugging purposes
        """
        self.agent_name = agent_name
        self.db_config: Optional[DatabaseConfig] = None
        self._connection_cache: Dict[str, Any] = {}
    
    def _normalize_user_id(self, user_id: int) -> int:
        """
        Normalize user_id by stripping leading zeros if present.
        
        Args:
            user_id: The user ID to normalize
            
        Returns:
            Normalized user ID with leading zeros stripped
        """
        # Convert to string, strip leading zeros, then back to int
        # This handles cases where user_id might be stored as "00123" -> 123
        user_id_str = str(user_id).lstrip('0')
        # Handle edge case where user_id is all zeros
        if not user_id_str:
            return 0
        return int(user_id_str)
    
    def _get_db_config(self) -> DatabaseConfig:
        """
        Get or create database configuration.
        
        Returns:
            DatabaseConfig instance
            
        Raises:
            DatabaseKeyError: If database configuration is not available
        """
        if self.db_config is None:
            self.db_config = create_database_config(self.agent_name)
            
        if not self.db_config.available:
            raise DatabaseKeyError("Database configuration is not available")
            
        return self.db_config
    
    async def get_api_key(self, user_id: int, service: str) -> Optional[str]:
        """
        Retrieve and decrypt an API key for a user and service (async version).
        
        Args:
            user_id: The user ID to retrieve the key for
            service: The service name (e.g., 'github', 'openai', etc.)
            
        Returns:
            Decrypted API key if found and valid, None otherwise
            
        Raises:
            DatabaseKeyError: If database operations fail
            EncryptionError: If decryption fails
        """
        # Normalize user_id by stripping leading zeros
        user_id = self._normalize_user_id(user_id)
        
        await debug_print(
            f"DEBUG: Retrieving API key for user_id={user_id}, service={service}", 
            agent_name=self.agent_name
        )
        
        try:
            db_config = self._get_db_config()
            sync_conn_str, async_conn_str = await db_config.get_connection_strings()
            
            # Create async engine using SQLAlchemy
            engine = create_async_engine(async_conn_str, echo=False)
            
            try:
                async with engine.begin() as conn:
                    # Query for the API key using SQLAlchemy text query
                    query = text("""
                        SELECT id, user_id, service, api_key, expiration_date, updated_at, is_active
                        FROM public.mcp_keys
                        WHERE user_id = :user_id AND service = :service AND is_active = true
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """)
                    
                    await debug_print(
                        f"DEBUG: Executing query with params user_id={user_id}, service={service}", 
                        agent_name=self.agent_name
                    )
                    
                    result = await conn.execute(query, {"user_id": user_id, "service": service})
                    row = result.fetchone()
                    
                    if row is None:
                        await debug_print(
                            f"DEBUG: No API key found for user_id={user_id}, service={service}", 
                            agent_name=self.agent_name
                        )
                        return None
                    
                    # Convert row to dict-like access
                    row_dict = row._asdict()
                    
                    # # Check expiration
                    # if row_dict['expiration_date'] and row_dict['expiration_date'] < datetime.now(row_dict['expiration_date'].tzinfo):
                    #     await debug_print(
                    #         f"DEBUG: API key expired for user_id={user_id}, service={service}. "
                    #         f"Expired at: {row_dict['expiration_date']}", 
                    #         agent_name=self.agent_name
                    #     )
                    #     return None
                    
                    # Decrypt the API key
                    encrypted_key = row_dict['api_key']
                    if not encrypted_key:
                        await debug_print(
                            f"DEBUG: Empty API key for user_id={user_id}, service={service}", 
                            agent_name=self.agent_name
                        )
                        return None
                    
                    await debug_print(
                        f"DEBUG: Found encrypted API key for user_id={user_id}, service={service}. "
                        f"Key length: {len(encrypted_key)} chars", 
                        agent_name=self.agent_name
                    )
                    
                    # Decrypt the key
                    import asyncio
                    decrypted_key = await asyncio.to_thread(decrypt_token, encrypted_key, self.agent_name)
                    
                    await debug_print(
                        f"DEBUG: Successfully decrypted API key for user_id={user_id}, service={service}", 
                        agent_name=self.agent_name
                    )
                    
                    return decrypted_key
                    
            finally:
                await engine.dispose()
                
        except SQLAlchemyError as e:
            await debug_print(
                f"ERROR: Database error while retrieving API key: {e}", 
                agent_name=self.agent_name
            )
            raise DatabaseKeyError(f"Database operation failed: {e}") from e
        except EncryptionError:
            # Re-raise encryption errors as-is
            raise
        except Exception as e:
            await debug_print(
                f"ERROR: Unexpected error while retrieving API key: {e}", 
                agent_name=self.agent_name
            )
            raise DatabaseKeyError(f"Failed to retrieve API key: {e}") from e

    async def get_user_keys(self, user_id: int) -> Dict[str, str]:
        """
        Retrieve all active API keys for a user.
        
        Args:
            user_id: The user ID to retrieve keys for
            
        Returns:
            Dictionary mapping service names to decrypted API keys
            
        Raises:
            DatabaseKeyError: If database operations fail
        """
        # Normalize user_id by stripping leading zeros
        user_id = self._normalize_user_id(user_id)
        
        await debug_print(
            f"DEBUG: Retrieving all API keys for user_id={user_id}", 
            agent_name=self.agent_name
        )
        
        try:
            db_config = self._get_db_config()
            sync_conn_str, async_conn_str = await db_config.get_connection_strings()
            
            # Create async engine using SQLAlchemy
            engine = create_async_engine(async_conn_str, echo=False)
            
            try:
                async with engine.begin() as conn:
                    # Query for all API keys using SQLAlchemy text query
                    query = text("""
                        SELECT DISTINCT ON (service) 
                               id, user_id, service, api_key, expiration_date, updated_at, is_active
                        FROM public.mcp_keys
                        WHERE user_id = :user_id AND is_active = true
                        ORDER BY service, updated_at DESC
                    """)
                    
                    result = await conn.execute(query, {"user_id": user_id})
                    rows = result.fetchall()
                    
                    keys = {}
                    current_time = datetime.now()
                    
                    for row in rows:
                        # Convert row to dict-like access
                        row_dict = row._asdict()
                        service = row_dict['service']
                        
                        # Decrypt the API key
                        encrypted_key = row_dict['api_key']
                        if not encrypted_key:
                            await debug_print(
                                f"DEBUG: Skipping empty key for service={service}, user_id={user_id}", 
                                agent_name=self.agent_name
                            )
                            continue
                        
                        try:
                            import asyncio
                            decrypted_key = await asyncio.to_thread(decrypt_token, encrypted_key, self.agent_name)
                            keys[service] = decrypted_key
                            await debug_print(
                                f"DEBUG: Successfully decrypted key for service={service}, user_id={user_id}", 
                                agent_name=self.agent_name
                            )
                        except EncryptionError as e:
                            await debug_print(
                                f"WARNING: Failed to decrypt key for service={service}, user_id={user_id}: {e}", 
                                agent_name=self.agent_name
                            )
                            continue
                    
                    await debug_print(
                        f"DEBUG: Retrieved {len(keys)} valid API keys for user_id={user_id}", 
                        agent_name=self.agent_name
                    )
                    
                    return keys
                    
            finally:
                await engine.dispose()
                
        except SQLAlchemyError as e:
            await debug_print(
                f"ERROR: Database error while retrieving user keys: {e}", 
                agent_name=self.agent_name
            )
            raise DatabaseKeyError(f"Database operation failed: {e}") from e
        except Exception as e:
            await debug_print(
                f"ERROR: Unexpected error while retrieving user keys: {e}", 
                agent_name=self.agent_name
            )
            raise DatabaseKeyError(f"Failed to retrieve user keys: {e}") from e
    

# Convenience functions for easy usage

def create_api_key_manager(agent_name: str) -> ApiKeyManager:
    """
    Create an API key manager instance for an agent.
    
    Args:
        agent_name: Name of the agent requesting API key services
        
    Returns:
        ApiKeyManager instance
    """
    return ApiKeyManager(agent_name)


async def get_user_api_key(user_id: int, service: str, agent_name: str = "API_KEY_MANAGER") -> Optional[str]:
    """
    Retrieve and decrypt an API key for a user and service (async).
    
    Args:
        user_id: The user ID to retrieve the key for
        service: The service name (e.g., 'github', 'openai', etc.)
        agent_name: Name of the agent for debugging purposes
        
    Returns:
        Decrypted API key if found and valid, None otherwise
        
    Raises:
        DatabaseKeyError: If database operations fail
        EncryptionError: If decryption fails
    """
    manager = create_api_key_manager(agent_name)
    return await manager.get_api_key(user_id, service)


async def get_user_keys_async(user_id: int, agent_name: str = "API_KEY_MANAGER") -> Dict[str, str]:
    """
    Retrieve all active API keys for a user (async).
    
    Args:
        user_id: The user ID to retrieve keys for
        agent_name: Name of the agent for debugging purposes
        
    Returns:
        Dictionary mapping service names to decrypted API keys
        
    Raises:
        DatabaseKeyError: If database operations fail
    """
    manager = create_api_key_manager(agent_name)
    return await manager.get_user_keys(user_id)


async def is_api_key_service_available(agent_name: str = "API_KEY_MANAGER") -> bool:
    """
    Check if API key service is available and properly configured.
    
    Args:
        agent_name: Name of the agent checking service availability
        
    Returns:
        True if service is available, False otherwise
    """
    try:
        from .database_factory import is_database_available
        from .encryption_utils import is_encryption_available
        
        db_available = await is_database_available(agent_name)
        encryption_available = is_encryption_available(agent_name)
        
        available = db_available and encryption_available
        
        await debug_print(
            f"DEBUG: API key service availability check - "
            f"Database: {db_available}, Encryption: {encryption_available}, "
            f"Overall: {available}", 
            agent_name=agent_name
        )
        
        return available
        
    except Exception as e:
        await debug_print(
            f"DEBUG: API key service availability check failed: {e}", 
            agent_name=agent_name
        )
        return False
