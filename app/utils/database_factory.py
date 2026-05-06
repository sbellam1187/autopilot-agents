"""
Database connection factory utilities for autopilot agents.
Provides reusable database authentication and configuration for PostgreSQL and vector stores.

This module centralizes database connection logic to support:
- Basic username/password authentication
- Azure service principal authentication
- Vector store configuration with PGVector
- Connection string generation with proper SSL settings
"""

from typing import Dict, Any, Optional, Tuple
from sqlalchemy import make_url
from azure.identity import ClientSecretCredential
from urllib.parse import quote_plus
import os
import traceback

from .debug_utils import debug_print


class DatabaseConfig:
    """Database configuration and authentication manager."""
    
    def __init__(self, agent_name: str = "DATABASE_FACTORY"):
        """
        Initialize database configuration.
        
        Args:
            agent_name: Name of the agent for debugging purposes
        """
        self.agent_name = agent_name
        self.available = True
        self.db_config: Dict[str, Any] = {}
        self.azure_config: Dict[str, str] = {}
        self._config_initialized = False
        
        # Setup will be done lazily on first use
    
    async def _ensure_config_initialized(self):
        """Ensure configuration is initialized."""
        if not self._config_initialized:
            await self._setup_db_config()
            self._config_initialized = True
    
    async def _setup_db_config(self) -> None:
        """Parse JDBC URL and setup database authentication configuration."""
        try:
            jdbc_url = os.environ.get(
                "JDBC_URL", 
                "postgresql://username:password@localhost:5432/vector_db?sslmode=require"
            )
            url = make_url(jdbc_url)  # type: ignore
            
            self.db_config = {
                'host': url.host or "localhost",
                'port': url.port or 5432,
                'database': url.database or "vector_db",
                'user': url.username or "username",
                'password': url.password or "password",
                'sslmode': url.query.get('sslmode', 'require') if url.query else 'require',
            }
            
            # Azure service principal configuration
            self.azure_config = {
                'auth_method': os.environ.get("DB_AUTH_METHOD", "basic").lower(),
                'client_id': os.environ.get("ARM_CLIENT_ID", ""),
                'client_secret': os.environ.get("ARM_CLIENT_SECRET", ""),
                'tenant_id': os.environ.get("ARM_TENANT_ID", ""),
            }
            
            await debug_print(
                f"DEBUG: Database config parsed - host={self.db_config['host']}, "
                f"port={self.db_config['port']}, database={self.db_config['database']}, "
                f"user={self.db_config['user']}, sslmode={self.db_config['sslmode']}", 
                agent_name=self.agent_name
            )
            await debug_print(
                f"DEBUG: Authentication method: {self.azure_config['auth_method']}", 
                agent_name=self.agent_name
            )
            
        except Exception as e:
            await debug_print(
                f"ERROR: Failed to parse database configuration: {e}", 
                agent_name=self.agent_name
            )
            self.available = False
    
    async def get_database_password(self) -> str:
        """
        Get the database password based on the authentication method.
        
        Returns:
            Database password or Azure access token
            
        Raises:
            ValueError: If Azure service principal configuration is incomplete
            Exception: If Azure token acquisition fails
        """
        await self._ensure_config_initialized()
        auth_method = self.azure_config['auth_method']
        
        if auth_method == 'service_principal':
            return await self._get_azure_access_token()
        else:
            # Basic username/password authentication
            return self.db_config['password']
    
    async def _get_azure_access_token(self) -> str:
        """
        Get Azure access token for service principal authentication.
        
        Returns:
            Azure access token string
            
        Raises:
            ValueError: If required Azure environment variables are missing
            Exception: If token acquisition fails
        """
        client_id = self.azure_config['client_id']
        client_secret = self.azure_config['client_secret']
        tenant_id = self.azure_config['tenant_id']
        
        if not all([client_id, client_secret, tenant_id]):
            raise ValueError(
                "Azure service principal authentication requires ARM_CLIENT_ID, "
                "ARM_CLIENT_SECRET, and ARM_TENANT_ID environment variables"
            )
        
        try:
            await debug_print("DEBUG: Acquiring Azure access token...", agent_name=self.agent_name)
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Use the correct scope for Azure PostgreSQL
            # Wrap the synchronous get_token call to prevent blocking I/O
            import asyncio
            access_token = await asyncio.to_thread(
                credential.get_token, 
                'https://ossrdbms-aad.database.windows.net/.default'
            )
            await debug_print(
                f"DEBUG: Successfully acquired Azure access token (length: {len(access_token.token)} chars)", 
                agent_name=self.agent_name
            )
            return access_token.token
            
        except Exception as e:
            await debug_print(
                f"ERROR: Failed to acquire Azure access token: {str(e)}", 
                agent_name=self.agent_name
            )
            raise
    
    def _setup_db_config_sync(self) -> None:
        """Setup database configuration synchronously for sync methods."""
        try:
            jdbc_url = os.environ.get(
                "JDBC_URL", 
                "postgresql://username:password@localhost:5432/vector_db?sslmode=require"
            )
            url = make_url(jdbc_url)  # type: ignore
            
            self.db_config = {
                'host': url.host or "localhost",
                'port': url.port or 5432,
                'database': url.database or "vector_db",
                'user': url.username or "username",
                'password': url.password or "password",
                'sslmode': url.query.get('sslmode', 'require') if url.query else 'require',
            }
            
            # Azure service principal configuration
            self.azure_config = {
                'auth_method': os.environ.get("DB_AUTH_METHOD", "basic").lower(),
                'client_id': os.environ.get("ARM_CLIENT_ID", ""),
                'client_secret': os.environ.get("ARM_CLIENT_SECRET", ""),
                'tenant_id': os.environ.get("ARM_TENANT_ID", ""),
            }
            
            from .debug_utils import debug_print_sync
            debug_print_sync(
                f"DEBUG: Database config parsed - host={self.db_config['host']}, "
                f"port={self.db_config['port']}, database={self.db_config['database']}, "
                f"user={self.db_config['user']}, sslmode={self.db_config['sslmode']}", 
                agent_name=self.agent_name
            )
            debug_print_sync(
                f"DEBUG: Authentication method: {self.azure_config['auth_method']}", 
                agent_name=self.agent_name
            )
            
        except Exception as e:
            from .debug_utils import debug_print_sync
            debug_print_sync(
                f"ERROR: Failed to parse database configuration: {e}", 
                agent_name=self.agent_name
            )
            self.available = False

    def get_database_password_sync(self) -> str:
        """
        Get the database password based on the authentication method (sync version).
        
        Returns:
            Database password or Azure access token
            
        Raises:
            ValueError: If Azure service principal configuration is incomplete
            Exception: If Azure token acquisition fails
        """
        # Ensure config is initialized
        if not hasattr(self, 'db_config') or not self.db_config:
            self._setup_db_config_sync()
            
        auth_method = self.azure_config['auth_method']
        
        if auth_method == 'service_principal':
            return self._get_azure_access_token_sync()
        else:
            # Basic username/password authentication
            return self.db_config['password']

    def _get_azure_access_token_sync(self) -> str:
        """
        Get Azure access token for service principal authentication (sync version).
        
        Returns:
            Azure access token string
            
        Raises:
            ValueError: If required Azure environment variables are missing
            Exception: If token acquisition fails
        """
        client_id = self.azure_config['client_id']
        client_secret = self.azure_config['client_secret']
        tenant_id = self.azure_config['tenant_id']
        
        if not all([client_id, client_secret, tenant_id]):
            raise ValueError(
                "Azure service principal authentication requires ARM_CLIENT_ID, "
                "ARM_CLIENT_SECRET, and ARM_TENANT_ID environment variables"
            )
        
        try:
            from .debug_utils import debug_print_sync
            debug_print_sync("DEBUG: Acquiring Azure access token (sync)...", agent_name=self.agent_name)
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Use the correct scope for Azure PostgreSQL (sync call)
            access_token = credential.get_token('https://ossrdbms-aad.database.windows.net/.default')
            debug_print_sync(
                f"DEBUG: Successfully acquired Azure access token (sync) (length: {len(access_token.token)} chars)", 
                agent_name=self.agent_name
            )
            return access_token.token
            
        except Exception as e:
            from .debug_utils import debug_print_sync
            debug_print_sync(
                f"ERROR: Failed to acquire Azure access token (sync): {str(e)}", 
                agent_name=self.agent_name
            )
            raise

    def get_connection_strings_sync(self) -> Tuple[str, str]:
        """
        Generate sync and async connection strings for PostgreSQL (sync version).
        Supports both basic auth and Azure AD tokens like the async version.
        
        Returns:
            Tuple of (sync_connection_string, async_connection_string)
            
        Raises:
            Exception: If database configuration is not available
        """
        # Ensure config is initialized
        if not hasattr(self, 'db_config') or not self.db_config:
            self._setup_db_config_sync()
            
        if not self.available:
            raise Exception("Database configuration is not available")
        
        try:
            # Get the appropriate password/token based on auth method
            password = self.get_database_password_sync()
            
            # URL encode the password to handle special characters in tokens
            encoded_password = quote_plus(password)
            
            from .debug_utils import debug_print_sync
            
            # Construct connection strings with proper SSL and authentication parameters
            if self.azure_config['auth_method'] == 'service_principal':
                debug_print_sync(
                    "DEBUG: Using Azure AD authentication for database connection (sync)", 
                    agent_name=self.agent_name
                )
                
                # For Azure AD, include connect_timeout and ensure proper SSL mode
                sync_connection_string = (
                    f"postgresql://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?sslmode={self.db_config['sslmode']}&connect_timeout=30"
                )
                
                # Async connection string for asyncpg
                async_connection_string = (
                    f"postgresql+asyncpg://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?ssl=require"
                )
                
                debug_print_sync(
                    f"DEBUG: Using Azure connection with SSL mode: {self.db_config['sslmode']}", 
                    agent_name=self.agent_name
                )
                
            else:
                debug_print_sync(
                    "DEBUG: Using basic authentication for database connection (sync)", 
                    agent_name=self.agent_name
                )
                
                # For basic auth, simpler connection string
                sync_connection_string = (
                    f"postgresql://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?sslmode={self.db_config['sslmode']}"
                )
                
                async_connection_string = (
                    f"postgresql+asyncpg://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?ssl={self.db_config['sslmode']}"
                )
            
            debug_print_sync(
                "DEBUG: Connection strings generated successfully (sync)", 
                agent_name=self.agent_name
            )
            
            return sync_connection_string, async_connection_string
            
        except Exception as e:
            from .debug_utils import debug_print_sync
            debug_print_sync(
                f"ERROR: Failed to generate connection strings (sync): {str(e)}", 
                agent_name=self.agent_name
            )
            debug_print_sync(
                f"DEBUG: Full traceback: {traceback.format_exc()}", 
                agent_name=self.agent_name
            )
            raise

    async def get_connection_strings(self) -> Tuple[str, str]:
        """
        Generate sync and async connection strings for PostgreSQL.
        
        Returns:
            Tuple of (sync_connection_string, async_connection_string)
            
        Raises:
            Exception: If database configuration is not available
        """
        await self._ensure_config_initialized()
        if not self.available:
            raise Exception("Database configuration is not available")
        
        try:
            # Get the appropriate password/token based on auth method
            password = await self.get_database_password()
            
            # URL encode the password to handle special characters in tokens
            encoded_password = quote_plus(password)
            
            # Construct connection strings with proper SSL and authentication parameters
            if self.azure_config['auth_method'] == 'service_principal':
                await debug_print(
                    "DEBUG: Using Azure AD authentication for database connection", 
                    agent_name=self.agent_name
                )
                
                # For Azure AD, include connect_timeout and ensure proper SSL mode
                sync_connection_string = (
                    f"postgresql://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?sslmode={self.db_config['sslmode']}&connect_timeout=30"
                )
                
                # Async connection string for asyncpg
                async_connection_string = (
                    f"postgresql+asyncpg://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?ssl=require"
                )
                
                await debug_print(
                    f"DEBUG: Using Azure connection with SSL mode: {self.db_config['sslmode']}", 
                    agent_name=self.agent_name
                )
                
            else:
                await debug_print(
                    "DEBUG: Using basic authentication for database connection", 
                    agent_name=self.agent_name
                )
                
                # For basic auth, simpler connection string
                sync_connection_string = (
                    f"postgresql://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?sslmode={self.db_config['sslmode']}"
                )
                
                async_connection_string = (
                    f"postgresql+asyncpg://{self.db_config['user']}:{encoded_password}@"
                    f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                    f"?ssl={self.db_config['sslmode']}"
                )
            
            await debug_print(
                "DEBUG: Connection strings generated successfully", 
                agent_name=self.agent_name
            )
            
            return sync_connection_string, async_connection_string
            
        except Exception as e:
            await debug_print(
                f"ERROR: Failed to generate connection strings: {str(e)}", 
                agent_name=self.agent_name
            )
            await debug_print(
                f"DEBUG: Full traceback: {traceback.format_exc()}", 
                agent_name=self.agent_name
            )
            raise


def create_database_config(agent_name: str) -> DatabaseConfig:
    """
    Create a database configuration instance for an agent.
    
    Args:
        agent_name: Name of the agent requesting database access
        
    Returns:
        DatabaseConfig instance
    """
    return DatabaseConfig(agent_name)


async def get_database_connection_strings(agent_name: str) -> Tuple[str, str]:
    """
    Get sync and async database connection strings for an agent.
    
    Args:
        agent_name: Name of the agent requesting database access
        
    Returns:
        Tuple of (sync_connection_string, async_connection_string)
        
    Raises:
        Exception: If database configuration fails or is unavailable
    """
    db_config = create_database_config(agent_name)
    return await db_config.get_connection_strings()


def get_database_connection_strings_sync(agent_name: str) -> Tuple[str, str]:
    """
    Get sync and async database connection strings for an agent (sync version).
    
    Args:
        agent_name: Name of the agent requesting database access
        
    Returns:
        Tuple of (sync_connection_string, async_connection_string)
        
    Raises:
        Exception: If database configuration fails or is unavailable
    """
    db_config = create_database_config(agent_name)
    return db_config.get_connection_strings_sync()


async def is_database_available(agent_name: str) -> bool:
    """
    Check if database configuration is available and valid.
    
    Args:
        agent_name: Name of the agent checking database availability
        
    Returns:
        True if database is available, False otherwise
    """
    try:
        db_config = create_database_config(agent_name)
        return db_config.available
    except Exception as e:
        await debug_print(
            f"DEBUG: Database availability check failed: {e}", 
            agent_name=agent_name
        )
        return False
