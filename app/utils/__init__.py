"""
Utilities package for autopilot agents.
"""

from .llm_factory import create_llm_model, create_agent_specific_llm, get_agent_model_config

from .debug_utils import (
    debug_print,
    debug_print_sync,
    debug_state,
    safe_json_serialize,
    error_print,
    error_print_sync,
    get_debug_enabled,
    handle_agent_error,
    handle_graph_compilation_error,
    log_error_context,
)

from .database_factory import (
    DatabaseConfig,
    create_database_config,
    get_database_connection_strings,
    is_database_available,
)

from .vector_store_factory import (
    VectorStoreConfig,
    create_vector_store_config,
    get_vector_store,
    create_query_engine,
    is_vector_store_available,
)

from .rag_utils import (
    RAGQueryEngine,
    create_rag_query_engine,
    execute_rag_query,
    search_documentation,
    is_rag_available,
)

from .encryption_utils import (
    EncryptionUtils,
    EncryptionError,
    create_encryption_utils,
    encrypt_token,
    decrypt_token,
    is_encryption_available,
)

from .api_key_manager import (
    ApiKeyManager,
    DatabaseKeyError,
    create_api_key_manager,
    get_user_api_key,
    get_user_keys_async,
    is_api_key_service_available,
)

__all__ = [
    # LLM Factory
    'create_llm_model',
    'create_agent_specific_llm',
    'get_agent_model_config',
    # Debug Utils
    'debug_print',
    'debug_print_sync',
    'debug_state',
    'safe_json_serialize',
    'error_print',
    'error_print_sync',
    'get_debug_enabled',
    'handle_agent_error',
    'handle_graph_compilation_error',
    'log_error_context',
    # Database Factory
    'DatabaseConfig',
    'create_database_config',
    'get_database_connection_strings',
    'is_database_available',
    # Vector Store Factory
    'VectorStoreConfig',
    'create_vector_store_config',
    'get_vector_store',
    'create_query_engine',
    'is_vector_store_available',
    # RAG Utils
    'RAGQueryEngine',
    'create_rag_query_engine',
    'execute_rag_query',
    'search_documentation',
    'is_rag_available',
    # Encryption Utils
    'EncryptionUtils',
    'EncryptionError',
    'create_encryption_utils',
    'encrypt_token',
    'decrypt_token',
    'is_encryption_available',
    # API Key Manager
    'ApiKeyManager',
    'DatabaseKeyError',
    'create_api_key_manager',
    'get_user_api_key',
    'get_user_keys_async',
    'is_api_key_service_available',
]
