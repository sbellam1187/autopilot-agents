"""
Vector store factory utilities for autopilot agents.
Provides reusable vector store configuration and setup for LlamaIndex with PGVector.

This module centralizes vector store creation logic to support:
- PGVector store configuration with PostgreSQL backend
- Configurable table names and embedding dimensions
- Proper integration with database authentication
- LlamaIndex Settings configuration
"""

from typing import Optional, Dict, Any
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.postgres import PGVectorStore
import os
import traceback

from .debug_utils import debug_print_sync as debug_print
from .database_factory import create_database_config
from .embedding_factory import create_embedding_model
from .llm_factory import create_llamaindex_llm


class VectorStoreConfig:
    """Vector store configuration and setup manager."""
    
    def __init__(self, agent_name: str = "VECTOR_STORE_FACTORY"):
        """
        Initialize vector store configuration.
        
        Args:
            agent_name: Name of the agent for debugging purposes
        """
        self.agent_name = agent_name
        self.available = True
        self.vector_store: Optional[PGVectorStore] = None
        
        # Configure LlamaIndex and setup vector store
        self._configure_llama_index()
        if self.available:
            self._setup_vector_store()
    
    def _configure_llama_index(self) -> None:
        """Configure LlamaIndex global settings."""
        try:
            # Create embedding model and LLM using centralized factories
            embed_model = create_embedding_model(self.agent_name)
            llm = create_llamaindex_llm(self.agent_name)
            
            chunk_size = int(os.environ.get("CHUNK_SIZE", "512"))
            chunk_overlap = int(os.environ.get("CHUNK_OVERLAP", "50"))
            
            if embed_model and llm:
                Settings.llm = llm  # type: ignore
                Settings.embed_model = embed_model  # type: ignore
                Settings.chunk_size = chunk_size  # type: ignore
                Settings.chunk_overlap = chunk_overlap  # type: ignore
                Settings.node_parser = SentenceSplitter(  # type: ignore
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                debug_print(
                    "DEBUG: LlamaIndex configured successfully", 
                    agent_name=self.agent_name
                )
            else:
                debug_print(
                    "DEBUG: Failed to create embedding model or LLM", 
                    agent_name=self.agent_name
                )
                self.available = False
        except Exception as e:
            debug_print(
                f"DEBUG: LlamaIndex configuration failed: {e}", 
                agent_name=self.agent_name
            )
            self.available = False
    
    def _setup_vector_store(self) -> None:
        """Setup PostgreSQL vector store using database factory."""
        try:
            # Use database factory to get connection strings
            db_config = create_database_config(self.agent_name)
            if not db_config.available:
                debug_print(
                    "ERROR: Database configuration not available", 
                    agent_name=self.agent_name
                )
                self.available = False
                return
            
            sync_conn_str, async_conn_str = db_config.get_connection_strings_sync()
            
            debug_print(
                "DEBUG: Creating vector store with database factory connection strings", 
                agent_name=self.agent_name
            )
            
            self.vector_store = PGVectorStore.from_params(  # type: ignore
                connection_string=sync_conn_str,
                async_connection_string=async_conn_str,
                table_name=os.environ.get("VECTOR_TABLE_NAME", "json_data"),
                embed_dim=int(os.environ.get("EMBEDDING_DIM", "1024")),
                perform_setup=False
            )
            debug_print(
                "DEBUG: Vector store configured successfully", 
                agent_name=self.agent_name
            )
            
        except Exception as e:
            debug_print(
                f"ERROR: Vector store setup failed: {str(e)}", 
                agent_name=self.agent_name
            )
            debug_print(
                f"DEBUG: Full traceback: {traceback.format_exc()}", 
                agent_name=self.agent_name
            )
            self.available = False
    
    def get_vector_store(self) -> Optional[PGVectorStore]:
        """
        Get the configured vector store.
        
        Returns:
            PGVectorStore instance if available, None otherwise
        """
        return self.vector_store if self.available else None
    
    def create_storage_context(self) -> Optional[StorageContext]:
        """
        Create a storage context for LlamaIndex using the vector store.
        
        Returns:
            StorageContext instance if vector store is available, None otherwise
        """
        if not self.available or not self.vector_store:
            return None
        
        try:
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)  # type: ignore
            debug_print(
                "DEBUG: Storage context created successfully", 
                agent_name=self.agent_name
            )
            return storage_context
        except Exception as e:
            debug_print(
                f"ERROR: Failed to create storage context: {str(e)}", 
                agent_name=self.agent_name
            )
            return None
    
    def create_vector_index(self) -> Optional[VectorStoreIndex]:
        """
        Create a vector index for querying.
        
        Returns:
            VectorStoreIndex instance if successful, None otherwise
        """
        storage_context = self.create_storage_context()
        if not storage_context:
            return None
        
        try:
            index = VectorStoreIndex([], storage_context=storage_context)  # type: ignore
            debug_print(
                "DEBUG: Vector index created successfully", 
                agent_name=self.agent_name
            )
            return index
        except Exception as e:
            debug_print(
                f"ERROR: Failed to create vector index: {str(e)}", 
                agent_name=self.agent_name
            )
            return None


def create_vector_store_config(agent_name: str) -> VectorStoreConfig:
    """
    Create a vector store configuration instance for an agent.
    
    Args:
        agent_name: Name of the agent requesting vector store access
        
    Returns:
        VectorStoreConfig instance
    """
    return VectorStoreConfig(agent_name)


def get_vector_store(agent_name: str) -> Optional[PGVectorStore]:
    """
    Get a configured vector store for an agent.
    
    Args:
        agent_name: Name of the agent requesting vector store access
        
    Returns:
        PGVectorStore instance if successful, None otherwise
    """
    config = create_vector_store_config(agent_name)
    return config.get_vector_store()


def create_query_engine(agent_name: str, similarity_top_k: int = 5, response_mode: str = "compact"):
    """
    Create a query engine for vector search using the configured vector store.
    
    Args:
        agent_name: Name of the agent requesting query engine
        similarity_top_k: Number of similar documents to retrieve
        response_mode: Response mode for the query engine
        
    Returns:
        Query engine instance if successful, None otherwise
    """
    config = create_vector_store_config(agent_name)
    index = config.create_vector_index()
    
    if not index:
        debug_print(
            "ERROR: Failed to create vector index for query engine", 
            agent_name=agent_name
        )
        return None
    
    try:
        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k, 
            response_mode=response_mode
        )
        debug_print(
            f"DEBUG: Query engine created with top_k={similarity_top_k}, mode={response_mode}", 
            agent_name=agent_name
        )
        return query_engine
    except Exception as e:
        debug_print(
            f"ERROR: Failed to create query engine: {str(e)}", 
            agent_name=agent_name
        )
        return None


def is_vector_store_available(agent_name: str) -> bool:
    """
    Check if vector store configuration is available and valid.
    
    Args:
        agent_name: Name of the agent checking vector store availability
        
    Returns:
        True if vector store is available, False otherwise
    """
    try:
        config = create_vector_store_config(agent_name)
        return config.available
    except Exception as e:
        debug_print(
            f"DEBUG: Vector store availability check failed: {e}", 
            agent_name=agent_name
        )
        return False
