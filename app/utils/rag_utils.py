"""
RAG (Retrieval-Augmented Generation) utilities for autopilot agents.
Provides a simplified interface for RAG query execution using vector stores.

This module provides high-level RAG functionality by combining:
- Vector store configuration and management
- Query execution with source node extraction
- Error handling and result formatting
- Configurable similarity search parameters
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import traceback

from .debug_utils import debug_print_sync as debug_print
from .vector_store_factory import create_query_engine, is_vector_store_available


class RAGQueryEngine:
    """Simplified RAG query engine for vector search."""
    
    def __init__(self, agent_name: str = "RAG_ENGINE"):
        """
        Initialize RAG query engine.
        
        Args:
            agent_name: Name of the agent for debugging purposes
        """
        self.agent_name = agent_name
        self.available = is_vector_store_available(agent_name)
        
        debug_print(
            f"DEBUG: RAG query engine initialized, available: {self.available}", 
            agent_name=self.agent_name
        )
    
    def query(self, query_text: str, top_k: int = 5, response_mode: str = "compact") -> Dict[str, Any]:
        """
        Execute RAG query against the vector store.
        
        Args:
            query_text: The search query text
            top_k: Number of similar documents to retrieve
            response_mode: Response mode for the query engine
            
        Returns:
            Dictionary containing query results, response, source nodes, and metadata
        """
        if not self.available:
            return {
                'query': query_text,
                'error': 'Vector store not available. RAG functionality disabled.',
                'source_nodes': [],
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Create query engine using the vector store factory
            query_engine = create_query_engine(
                agent_name=self.agent_name,
                similarity_top_k=top_k,
                response_mode=response_mode
            )
            
            if not query_engine:
                return {
                    'query': query_text,
                    'error': 'Failed to create query engine',
                    'source_nodes': [],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Execute the query
            response = query_engine.query(query_text)
            
            results = {
                'query': query_text,
                'response': str(response),
                'source_nodes': [],
                'timestamp': datetime.now().isoformat(),
                'top_k': top_k,
                'response_mode': response_mode
            }
            
            # Extract source information
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source_info = self._extract_source_info(node)
                    results['source_nodes'].append(source_info)
            
            debug_print(
                f"DEBUG: Query completed. Found {len(results['source_nodes'])} sources", 
                agent_name=self.agent_name
            )
            return results
            
        except Exception as e:
            error_msg = f"Error during RAG query: {str(e)}"
            debug_print(
                f"DEBUG: {error_msg}\nTraceback: {traceback.format_exc()}", 
                agent_name=self.agent_name
            )
            return {
                'query': query_text,
                'error': error_msg,
                'source_nodes': [],
                'timestamp': datetime.now().isoformat()
            }
    
    def _extract_source_info(self, node) -> Dict[str, Any]:
        """
        Extract source information from a node.
        
        Args:
            node: Source node from query results
            
        Returns:
            Dictionary containing extracted source information
        """
        try:
            # Extract node text
            node_text = getattr(getattr(node, 'node', None), 'text', "")
            if not node_text and hasattr(getattr(node, 'node', None), 'get_content'):
                node_text = node.node.get_content()
            
            # Truncate long content for readability
            content = node_text[:500] + "..." if len(node_text) > 500 else node_text
            
            source_info = {
                'content': content,
                'score': getattr(node, 'score', 0),
                'metadata': getattr(getattr(node, 'node', None), 'metadata', {}),
                'node_id': getattr(getattr(node, 'node', None), 'node_id', None)
            }
            
            return source_info
            
        except Exception as e:
            debug_print(
                f"DEBUG: Failed to extract source info: {e}", 
                agent_name=self.agent_name
            )
            return {
                'content': 'Failed to extract content',
                'score': 0,
                'metadata': {},
                'error': str(e)
            }
    
    def batch_query(self, queries: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Execute multiple RAG queries.
        
        Args:
            queries: List of query texts
            top_k: Number of similar documents to retrieve for each query
            
        Returns:
            List of query results
        """
        results = []
        for query_text in queries:
            result = self.query(query_text, top_k=top_k)
            results.append(result)
        
        debug_print(
            f"DEBUG: Batch query completed for {len(queries)} queries", 
            agent_name=self.agent_name
        )
        return results


def create_rag_query_engine(agent_name: str) -> RAGQueryEngine:
    """
    Create a RAG query engine for an agent.
    
    Args:
        agent_name: Name of the agent requesting RAG functionality
        
    Returns:
        RAGQueryEngine instance
    """
    return RAGQueryEngine(agent_name)


def execute_rag_query(
    agent_name: str, 
    query_text: str, 
    top_k: int = 5, 
    response_mode: str = "compact"
) -> Dict[str, Any]:
    """
    Execute a single RAG query for an agent.
    
    Args:
        agent_name: Name of the agent requesting the query
        query_text: The search query text
        top_k: Number of similar documents to retrieve
        response_mode: Response mode for the query engine
        
    Returns:
        Dictionary containing query results
    """
    engine = create_rag_query_engine(agent_name)
    return engine.query(query_text, top_k=top_k, response_mode=response_mode)


def search_documentation(
    agent_name: str, 
    query: Union[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Search documentation using RAG with flexible query input.
    This function provides a standard interface for documentation search tools.
    
    Args:
        agent_name: Name of the agent performing the search
        query: Search query (string) or query parameters (dict)
        
    Returns:
        Dictionary containing search results and source information
    """
    # Normalize input
    if isinstance(query, str):
        query_text = query
        top_k = 5
    elif isinstance(query, dict):
        query_text = (
            query.get('query') or 
            query.get('text') or 
            query.get('search_query') or 
            query.get('question') or 
            "general search"
        )
        top_k = query.get('top_k', 5)
    else:
        query_text = str(query)
        top_k = 5
    
    return execute_rag_query(agent_name, query_text, top_k=top_k)


def is_rag_available(agent_name: str) -> bool:
    """
    Check if RAG functionality is available for an agent.
    
    Args:
        agent_name: Name of the agent checking RAG availability
        
    Returns:
        True if RAG is available, False otherwise
    """
    return is_vector_store_available(agent_name)
