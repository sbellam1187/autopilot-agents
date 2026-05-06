# API Key Management Utilities

This document describes the API key management utilities for the autopilot agents system. These utilities provide secure, encrypted storage and retrieval of API keys from the database.

## Overview

The API key management system consists of two main components:

1. **Encryption Utilities** (`encryption_utils.py`) - Handles AES-256-GCM encryption/decryption
2. **API Key Manager** (`api_key_manager.py`) - Manages database operations for encrypted API keys

## Features

- **🔐 Secure Encryption**: AES-256-GCM encryption compatible with the UI encryption scheme
- **🗄️ Database Integration**: Seamless integration with PostgreSQL database
- **⚡ Async Support**: Both synchronous and asynchronous operations
- **🔧 Easy Integration**: Simple functions for use in any agent
- **🛡️ Error Handling**: Comprehensive error handling and logging
- **⏰ Expiration Handling**: Automatic handling of expired API keys

## Database Schema

The system uses the `public.mcp_keys` table with the following structure:

```sql
CREATE TABLE public.mcp_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    service VARCHAR(50) NOT NULL,
    api_key TEXT NOT NULL,
    expiration_date TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, service)
);
```

## Environment Variables

The following environment variables are required:

```bash
# Encryption key (32-byte hex string for AES-256)
ENCRYPTION_SECRET_KEY=7373d8a5dfd21481cfbe823be393e26790666c1b80e5323f022fa80043283704

# Database connection (PostgreSQL JDBC URL)
JDBC_URL=postgresql://username:password@localhost:5432/vector_db?sslmode=require

# Optional: Database authentication method
DB_AUTH_METHOD=basic  # or 'service_principal' for Azure AD

# Optional: Azure service principal (if using service_principal auth)
ARM_CLIENT_ID=your-client-id
ARM_CLIENT_SECRET=your-client-secret
ARM_TENANT_ID=your-tenant-id
```

## Quick Start

### 1. Basic Usage

```python
from app.utils import get_user_api_key
from app.auth.auth_middleware import auth_context

# In your agent
async def my_agent_node(state, config):
    # Get user ID from auth context
    auth = auth_context.get()
    user_id = auth["user_id"]
    
    # Retrieve GitHub API key
    github_token = await get_user_api_key_async(user_id, "github", "MY_AGENT")
    
    if github_token:
        # Use the API key
        print(f"Got GitHub token: {github_token[:10]}...")
    else:
        print("No GitHub token found")
```

### 2. Synchronous Usage

```python
from app.utils import get_user_api_key

# Simple synchronous call
def get_github_key(user_id: int) -> str:
    return get_user_api_key(user_id, "github", "MY_AGENT")
```

### 3. Advanced Usage with Manager

```python
from app.utils import create_api_key_manager

# Create manager instance
manager = create_api_key_manager("MY_AGENT")

# Get specific key
github_key = await manager.get_api_key_async(user_id, "github")

# Get all keys for a user
all_keys = await manager.get_user_keys_async(user_id)
print(f"Available services: {list(all_keys.keys())}")
```

## API Reference

### Core Functions

#### `get_user_api_key(user_id, service, agent_name)`
Retrieve and decrypt an API key (synchronous).

**Parameters:**
- `user_id` (int): User ID from auth context
- `service` (str): Service name (e.g., 'github', 'openai')
- `agent_name` (str): Agent name for debugging

**Returns:** Decrypted API key string or None

#### `get_user_api_key_async(user_id, service, agent_name)`
Retrieve and decrypt an API key (asynchronous).

**Parameters:** Same as above
**Returns:** Decrypted API key string or None

#### `get_all_user_keys_async(user_id, agent_name)`
Retrieve all active API keys for a user.

**Parameters:**
- `user_id` (int): User ID
- `agent_name` (str): Agent name for debugging

**Returns:** Dictionary mapping service names to decrypted keys

### Utility Functions

#### `is_api_key_service_available(agent_name)`
Check if the API key service is available and properly configured.

**Returns:** Boolean indicating availability

#### `encrypt_token(plaintext, agent_name)`
Encrypt a token using AES-256-GCM.

#### `decrypt_token(encrypted_data, agent_name)`
Decrypt an encrypted token.

### Manager Class

#### `ApiKeyManager(agent_name)`
Full-featured manager class for API key operations.

**Methods:**
- `get_api_key_async(user_id, service)` - Async key retrieval
- `get_api_key_sync(user_id, service)` - Sync key retrieval  
- `get_user_keys_async(user_id)` - Get all user keys

## Integration Guide

### LangGraph Agent Integration

```python
from langgraph.graph import MessagesState, StateGraph, END
from app.utils import get_user_api_key_async
from app.auth.auth_middleware import auth_context

async def my_agent_node(state: MessagesState, config):
    """Agent node with API key integration."""
    
    try:
        # Get authenticated user
        auth = auth_context.get()
        user_id = auth["user_id"]
        
        # Retrieve service-specific API key
        api_key = await get_user_api_key_async(user_id, "github", "MY_AGENT")
        
        if not api_key:
            # Handle missing key (fallback, error, etc.)
            raise ValueError("No API key configured for GitHub")
        
        # Use API key for service operations
        # Example: Configure MCP client, HTTP headers, etc.
        
        # Your agent logic here...
        
    except Exception as e:
        # Handle errors appropriately
        raise
```

### MCP Client Configuration

```python
async def configure_mcp_with_api_key(user_id: int, service: str):
    """Configure MCP client with database API key."""
    
    # Get API key from database
    api_key = await get_user_api_key_async(user_id, service, "MCP_CLIENT")
    
    if not api_key:
        raise ValueError(f"No API key found for service: {service}")
    
    # Configure MCP client
    mcp_config = {
        "github-mcp-server": {
            "url": "http://localhost:5007/mcp",
            "transport": "streamable_http",
            "headers": {
                "Authorization": f"Bearer {api_key}"
            },
        },
    }
    
    return mcp_config
```

## Error Handling

The system provides comprehensive error handling:

```python
from app.utils import get_user_api_key_async, DatabaseKeyError, EncryptionError

try:
    api_key = await get_user_api_key_async(user_id, "github", "MY_AGENT")
except DatabaseKeyError as e:
    print(f"Database error: {e}")
except EncryptionError as e:
    print(f"Encryption error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Security Considerations

1. **Environment Variables**: Keep `ENCRYPTION_SECRET_KEY` secure and never log it
2. **Key Rotation**: Regularly rotate encryption keys and API keys
3. **Access Control**: Ensure proper user authentication before API key access
4. **Logging**: Be careful not to log decrypted API keys
5. **Network Security**: Use SSL/TLS for database connections

## Troubleshooting

### Common Issues

1. **"ENCRYPTION_SECRET_KEY environment variable is not set"**
   - Ensure the environment variable is set with a 64-character hex string (32 bytes)

2. **"Database configuration is not available"**
   - Check `JDBC_URL` environment variable
   - Verify database connectivity

3. **"Authentication failed - encrypted data is invalid"**
   - API key may be corrupted in database
   - Encryption key may have changed

4. **"No API key found for user"**
   - User may not have an API key configured for the service
   - Check database for user_id and service combination

### Debug Mode

Enable debug logging by setting agent-specific debug environment variables:

```bash
GITHUB_AGENT_DEBUG=true
MY_AGENT_DEBUG=true
```

## Testing

Run the test script to verify functionality:

```bash
cd /path/to/autopilot-agents
python test_api_key_utils.py
```

Run the usage examples:

```bash
python example_api_key_usage.py
```

## Dependencies

The utilities require these Python packages:

- `cryptography` - For AES encryption
- `asyncpg` - For async PostgreSQL operations  
- `psycopg2-binary` - For sync PostgreSQL operations
- `sqlalchemy` - For database URL parsing

Install with:

```bash
poetry install
# or
pip install cryptography asyncpg psycopg2-binary sqlalchemy
```

## Performance Considerations

- **Connection Pooling**: Consider implementing connection pooling for high-volume usage
- **Caching**: Cache decrypted keys temporarily (with proper security considerations)
- **Async Operations**: Use async versions for better performance in async contexts

## Migration from Existing Code

If you're migrating from existing token handling:

```python
# Before (using auth token directly)
auth = auth_context.get()
token = auth["token"]

# After (using database API key)
auth = auth_context.get()
user_id = auth["user_id"]
token = await get_user_api_key_async(user_id, "github", "MY_AGENT")
if not token:
    token = auth["token"]  # Fallback to auth token
```
