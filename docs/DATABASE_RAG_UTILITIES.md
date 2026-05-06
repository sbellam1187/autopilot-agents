# Database and RAG Utilities

This directory contains reusable utilities for database connectivity, vector store management, and RAG (Retrieval-Augmented Generation) functionality across autopilot agents.

## Overview

The utilities are organized into three main modules:

1. **`database_factory.py`** - Database connection and authentication management
2. **`vector_store_factory.py`** - Vector store configuration using LlamaIndex and PGVector
3. **`rag_utils.py`** - High-level RAG query execution interface

## Key Features

### Database Factory (`database_factory.py`)

- **Multi-Authentication Support**: Basic username/password and Azure service principal authentication
- **Connection String Generation**: Automatic sync and async PostgreSQL connection string creation
- **Environment Configuration**: Configurable via environment variables
- **SSL Support**: Proper SSL configuration for secure connections

#### Usage Example

```python
from utils.database_factory import create_database_config, get_database_connection_strings

# Create database config for an agent
db_config = create_database_config("MY_AGENT")

# Get connection strings
sync_conn, async_conn = get_database_connection_strings("MY_AGENT")

# Check availability
from utils.database_factory import is_database_available
if is_database_available("MY_AGENT"):
    print("Database is ready!")
```

#### Environment Variables

- `JDBC_URL`: PostgreSQL connection URL (default: `postgresql://username:password@localhost:5432/vector_db?sslmode=require`)
- `DB_AUTH_METHOD`: Authentication method - `basic` or `service_principal` (default: `basic`)
- `ARM_CLIENT_ID`: Azure service principal client ID (required for service_principal auth)
- `ARM_CLIENT_SECRET`: Azure service principal client secret (required for service_principal auth)
- `ARM_TENANT_ID`: Azure tenant ID (required for service_principal auth)

### Vector Store Factory (`vector_store_factory.py`)

- **LlamaIndex Integration**: Automatic LlamaIndex Settings configuration
- **PGVector Support**: PostgreSQL vector store with embedding support
- **Configurable Parameters**: Chunk size, overlap, embedding dimensions
- **Query Engine Creation**: Ready-to-use query engines for vector search

#### Usage Example

```python
from utils.vector_store_factory import create_query_engine, is_vector_store_available

# Check if vector store is available
if is_vector_store_available("MY_AGENT"):
    # Create a query engine
    query_engine = create_query_engine("MY_AGENT", similarity_top_k=10)
    
    if query_engine:
        response = query_engine.query("What is the project architecture?")
        print(response)
```

#### Environment Variables

- `VECTOR_TABLE_NAME`: PostgreSQL table name for vectors (default: `json_data`)
- `EMBEDDING_DIM`: Embedding dimension (default: `1024`)
- `CHUNK_SIZE`: Text chunk size for processing (default: `512`)
- `CHUNK_OVERLAP`: Overlap between chunks (default: `50`)

### RAG Utils (`rag_utils.py`)

- **Simplified Interface**: Easy-to-use RAG query execution
- **Flexible Query Input**: Support for string and dictionary query parameters
- **Source Extraction**: Automatic extraction of source nodes and metadata
- **Error Handling**: Comprehensive error handling with fallback responses
- **Batch Processing**: Support for multiple queries

#### Usage Example

```python
from utils.rag_utils import execute_rag_query, search_documentation

# Simple query execution
result = execute_rag_query("MY_AGENT", "How do I configure the database?")
print(f"Response: {result['response']}")
print(f"Sources: {len(result['source_nodes'])}")

# Using the standardized search interface
result = search_documentation("MY_AGENT", {
    "query": "deployment best practices",
    "top_k": 10
})

# Check availability
from utils.rag_utils import is_rag_available
if is_rag_available("MY_AGENT"):
    print("RAG functionality is ready!")
```

## Agent Integration

### Creating RAG-Enabled Tools

```python
from langchain.tools import tool
from utils.rag_utils import search_documentation

@tool
def search_documentation_tool(query: str) -> dict:
    """Search documentation using RAG."""
    return search_documentation("MY_AGENT", query)
```

### Using in LangGraph Agents

```python
from langgraph.prebuilt import create_react_agent
from utils import create_llm_model
from utils.rag_utils import search_documentation

def create_my_agent():
    @tool
    def search_docs(query: str) -> dict:
        return search_documentation("MY_AGENT", query)
    
    return create_react_agent(
        model=create_llm_model("MY_AGENT"),
        tools=[search_docs],
        name="my_agent"
    )
```

## Architecture Benefits

### Before Refactoring
- Database connection logic duplicated across agents
- Vector store setup repeated in each agent
- Authentication code scattered throughout codebase
- Difficult to maintain and update database configurations

### After Refactoring
- **DRY Principle**: Single source of truth for database and vector store logic
- **Separation of Concerns**: Clear separation between business logic and infrastructure
- **Reusability**: Utilities can be used by any agent needing RAG functionality
- **Maintainability**: Changes to database or vector store configuration happen in one place
- **Testability**: Utilities can be unit tested independently
- **Configurability**: Environment-driven configuration for different deployment scenarios

## Error Handling

All utilities include comprehensive error handling:

- **Graceful Degradation**: Functions return appropriate error states when services are unavailable
- **Debug Logging**: Detailed debug output for troubleshooting (uses existing debug utilities)
- **Exception Safety**: Proper exception handling with meaningful error messages
- **Availability Checks**: Helper functions to check service availability before use

## Best Practices

1. **Always Check Availability**: Use `is_database_available()`, `is_vector_store_available()`, or `is_rag_available()` before using services
2. **Agent-Specific Naming**: Pass agent names to utilities for proper logging and debugging
3. **Environment Configuration**: Configure services via environment variables for different environments
4. **Error Handling**: Handle service unavailability gracefully in your agents
5. **Resource Management**: The utilities handle connection pooling and resource management automatically

## Migration Guide

To migrate existing agents to use these utilities:

1. **Replace Database Logic**: Remove custom database connection code and use `database_factory`
2. **Replace Vector Store Setup**: Remove custom vector store initialization and use `vector_store_factory`
3. **Simplify RAG Queries**: Replace complex RAG query logic with `rag_utils.search_documentation`
4. **Update Imports**: Import utilities from the `utils` package
5. **Environment Variables**: Ensure required environment variables are set

### Example Migration

**Before:**
```python
# Custom database and vector store setup (200+ lines)
class CustomRAGEngine:
    def __init__(self):
        # Database connection logic
        # Azure authentication
        # Vector store setup
        # LlamaIndex configuration
```

**After:**
```python
from utils.rag_utils import create_rag_query_engine

# Simple initialization
query_engine = create_rag_query_engine("MY_AGENT")
```

This represents a significant reduction in code complexity while maintaining all functionality and improving maintainability.
