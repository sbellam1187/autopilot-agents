"""
Centralized LLM Factory for creating language models across all agents.
This module consolidates the create_llm_model function that was duplicated
across multiple agent files. Each agent can override specific parameters
to customize their LLM configuration while using the centralized factory.

Also supports LlamaIndex LLM models for RAG operations.
"""

import os
import traceback
from typing import Union, Optional, Dict, Any
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_ollama import ChatOllama
from llama_index.llms.ollama import Ollama as LlamaOllama
from llama_index.llms.azure_inference import AzureAICompletionsModel
from llama_index.llms.azure_openai import AzureOpenAI as LlamaAzureOpenAI
from llama_index.llms.openai import OpenAI as LlamaOpenAI

# Import debug utilities
from .debug_utils import debug_print_sync as debug_print, error_print_sync as error_print

def create_llm_model(
    agent_name: str = "unknown",
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    deployment_name: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs: Any
) -> Union[ChatOpenAI, AzureChatOpenAI, ChatOllama]:
    """
    Create and return the appropriate LLM model based on environment variables and optional overrides.
    
    Args:
        agent_name: Name of the agent calling this function (for debugging)
        provider: Override LLM provider ("openai", "azureopenai", or "ollama")
        model_name: Override model name (e.g., "gpt-4o", "qwen3")
        temperature: Override temperature (0.0 to 1.0)
        api_key: Override API key
        base_url: Override base URL
        deployment_name: Override Azure OpenAI deployment name
        api_version: Override Azure OpenAI API version
        **kwargs: Additional model-specific parameters
    
    Environment variables (used as defaults when overrides not provided):
    - LLM_PROVIDER: "openai", "azureopenai", or "ollama" (default: "openai")
    - OPENAI_MODEL: OpenAI model name (default: "gpt-4o")
    - OPENAI_API_KEY: OpenAI API key
    - OPENAI_BASE_URL: OpenAI base URL (default: "https://api.openai.com/v1")
    - OPENAI_DEPLOYMENT_NAME: Azure OpenAI deployment name (default: "gpt-4o-classification")
    - OPENAI_API_VERSION: Azure OpenAI API version (default: "2024-12-01-preview")
    - OLLAMA_MODEL: Ollama model name (default: "qwen3")
    - OLLAMA_BASE_URL: Ollama base URL (default: "http://localhost:11434")
    - MODEL_TEMPERATURE: Temperature for the model (default: 0)
    
    Agent-specific environment variables (highest priority):
    - {AGENT_NAME}_LLM_PROVIDER: Provider override for specific agent
    - {AGENT_NAME}_MODEL: Model name override for specific agent
    - {AGENT_NAME}_TEMPERATURE: Temperature override for specific agent
    - {AGENT_NAME}_API_KEY: API key override for specific agent
    - {AGENT_NAME}_BASE_URL: Base URL override for specific agent
    
    Returns:
        Union[ChatOpenAI, AzureChatOpenAI, ChatOllama]: Configured LLM model
        
    Raises:
        Exception: If model creation fails
        
    Example:
        # Use default configuration
        model = create_llm_model("AZURE")
        
        # Override to use Claude for specific agent
        model = create_llm_model("AZURE", provider="openai", model_name="gpt-3.5-turbo")
        
        # Use agent-specific environment variables
        # export AZURE_LLM_PROVIDER=ollama
        # export AZURE_MODEL=llama2
        model = create_llm_model("AZURE")
    """
    debug_print(f"DEBUG: Starting create_llm_model() in {agent_name}", agent_name=agent_name)
    
    try:
        # Get agent-specific configuration with fallbacks
        config = _get_agent_config(agent_name, provider, model_name, temperature, api_key, base_url, deployment_name, api_version)
        
        debug_print(f"DEBUG: LLM Provider: {config['provider']}", agent_name=agent_name)
        debug_print(f"DEBUG: Model Name: {config['model_name']}", agent_name=agent_name)
        debug_print(f"DEBUG: Temperature: {config['temperature']}", agent_name=agent_name)
        
        if config['provider'] == "ollama":
            return _create_ollama_model(config, agent_name, **kwargs)
        elif config['provider'] == "azureopenai":
            return _create_azure_openai_model(config, agent_name, **kwargs)
        else:  # Default to OpenAI
            return _create_openai_model(config, agent_name, **kwargs)
            
    except Exception as e:
        # Always print ERROR messages regardless of debug flag
        error_print(f"ERROR: Failed to create LLM model in {agent_name}: {str(e)}")
        error_print(f"ERROR: Traceback: {traceback.format_exc()}")
        raise


def _get_agent_config(
    agent_name: str,
    provider: Optional[str],
    model_name: Optional[str], 
    temperature: Optional[float],
    api_key: Optional[str],
    base_url: Optional[str],
    deployment_name: Optional[str],
    api_version: Optional[str]
) -> Dict[str, Any]:
    """
    Get configuration with priority: function params > agent-specific env vars > global env vars > defaults.
    """
    agent_prefix = agent_name.upper()
    
    # Provider selection with priority
    final_provider = (
        provider or
        os.environ.get(f"{agent_prefix}_LLM_PROVIDER") or
        os.environ.get("LLM_PROVIDER", "openai")
    ).lower()
    
    # Model name selection based on provider
    if final_provider == "ollama":
        default_model = "qwen3"
        env_key = "OLLAMA_MODEL"
        agent_env_key = f"{agent_prefix}_MODEL"
    else:
        default_model = "gpt-4o"
        env_key = "OPENAI_MODEL"
        agent_env_key = f"{agent_prefix}_MODEL"
    
    final_model_name = (
        model_name or
        os.environ.get(agent_env_key) or
        os.environ.get(env_key, default_model)
    )
    
    # Temperature selection
    final_temperature = temperature
    if final_temperature is None:
        temp_str = (
            os.environ.get(f"{agent_prefix}_TEMPERATURE") or
            os.environ.get("MODEL_TEMPERATURE", "0")
        )
        final_temperature = float(temp_str)
    
    # API key selection
    final_api_key = (
        api_key or
        os.environ.get(f"{agent_prefix}_API_KEY") or
        os.environ.get("OPENAI_API_KEY", "")
    )
    
    # Base URL selection with provider-specific logic
    if final_provider == "ollama":
        default_base_url = "http://localhost:11434"
        final_base_url = (
            base_url or
            os.environ.get(f"{agent_prefix}_BASE_URL") or
            os.environ.get("OLLAMA_BASE_URL") or
            default_base_url
        )
    elif final_provider == "azureopenai":
        default_base_url = "https://openai.azure.com/"
        final_base_url = (
            base_url or
            os.environ.get(f"{agent_prefix}_BASE_URL") or
            os.environ.get("OPENAI_BASE_URL") or
            default_base_url
        )
    else:  # OpenAI
        default_base_url = "https://api.openai.com/v1"
        final_base_url = (
            base_url or
            os.environ.get(f"{agent_prefix}_BASE_URL") or
            os.environ.get("OPENAI_BASE_URL") or
            default_base_url
        )
    
    # Azure-specific configurations
    final_deployment_name = (
        deployment_name or
        os.environ.get(f"{agent_prefix}_DEPLOYMENT_NAME") or
        os.environ.get("OPENAI_DEPLOYMENT_NAME", "gpt-4o-classification")
    )
    
    final_api_version = (
        api_version or
        os.environ.get(f"{agent_prefix}_API_VERSION") or
        os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview")
    )
    
    return {
        "provider": final_provider,
        "model_name": final_model_name,
        "temperature": final_temperature,
        "api_key": final_api_key,
        "base_url": final_base_url,
        "deployment_name": final_deployment_name,
        "api_version": final_api_version
    }
        

def _create_ollama_model(config: Dict[str, Any], agent_name: str, **kwargs: Any) -> ChatOllama:
    """Create Ollama model instance."""
    debug_print(f"DEBUG: Creating Ollama model: {config['model_name']} at {config['base_url']}", agent_name=agent_name)
    
    model_params = {
        "temperature": config['temperature'],
        "model": config['model_name'],
        "base_url": config['base_url'],
        **kwargs  # Allow additional parameters
    }
    
    model = ChatOllama(**model_params)
    debug_print("DEBUG: Ollama model created successfully (token tracking not supported)", agent_name=agent_name)
    return model


def _create_azure_openai_model(config: Dict[str, Any], agent_name: str, **kwargs: Any) -> AzureChatOpenAI:
    """Create Azure OpenAI model instance."""
    debug_print(f"DEBUG: Creating Azure OpenAI model: {config['model_name']} at {config['base_url']}", agent_name=agent_name)

    model_params = {
        "temperature": config['temperature'],
        "model": config['model_name'],
        "api_key": config['api_key'],
        "azure_endpoint": config['base_url'],
        "azure_deployment": config['deployment_name'],
        "api_version": config['api_version'],
        "stream_usage": True,  # Enable token usage tracking
        **kwargs  # Allow additional parameters
    }
    
    model = AzureChatOpenAI(**model_params)
    debug_print("DEBUG: Azure OpenAI model created successfully", agent_name=agent_name)
    return model


def _create_openai_model(config: Dict[str, Any], agent_name: str, **kwargs: Any) -> ChatOpenAI:
    """Create OpenAI model instance."""
    debug_print(f"DEBUG: Creating OpenAI model: {config['model_name']} at {config['base_url']}", agent_name=agent_name)
    
    model_params = {
        "temperature": config['temperature'],
        "model": config['model_name'],
        "api_key": config['api_key'],
        "base_url": config['base_url'],
        "stream_usage": True,  # Enable token usage tracking
        **kwargs  # Allow additional parameters
    }
    
    model = ChatOpenAI(**model_params)
    debug_print("DEBUG: OpenAI model created successfully", agent_name=agent_name)
    return model


def create_agent_specific_llm(
    agent_name: str,
    provider: str,
    model_name: str,
    temperature: float = 0.0,
    **kwargs: Any
) -> Union[ChatOpenAI, AzureChatOpenAI, ChatOllama]:
    """
    Convenience function for agents to create their specific LLM configuration.
    
    Args:
        agent_name: Name of the agent
        provider: LLM provider ("openai", "azureopenai", or "ollama")
        model_name: Specific model to use
        temperature: Model temperature (default: 0.0)
        **kwargs: Additional model-specific parameters
        
    Returns:
        Configured LLM model instance
        
    Example:
        # Azure agent wants to use GPT-3.5 Turbo with higher temperature
        model = create_agent_specific_llm(
            "AZURE", 
            "openai", 
            "gpt-3.5-turbo", 
            temperature=0.7,
            max_tokens=1000
        )
        
        # GitHub agent wants to use Ollama with local model
        model = create_agent_specific_llm(
            "GITHUB",
            "ollama", 
            "codellama:7b",
            base_url="http://localhost:11434"
        )
    """
    return create_llm_model(
        agent_name=agent_name,
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )


def get_agent_model_config(agent_name: str) -> Dict[str, Any]:
    """
    Get the current model configuration for an agent without creating the model.
    Useful for debugging or configuration validation.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Dictionary containing the resolved configuration
        
    Example:
        config = get_agent_model_config("AZURE")
        print(f"Azure agent will use: {config['provider']} - {config['model_name']}")
    """
    return _get_agent_config(agent_name, None, None, None, None, None, None, None)


def create_llamaindex_llm(
    agent_name: str = "unknown",
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    deployment_name: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs: Any
) -> Union[object, None]:
    """
    Create and return the appropriate LlamaIndex LLM model.
    
    Args:
        agent_name: Name of the agent calling this function (for debugging)
        provider: Override LLM provider ("openai", "azureopenai", or "ollama")
        model_name: Override model name (e.g., "gpt-4o", "qwen3")
        temperature: Override temperature (0.0 to 1.0)
        api_key: Override API key
        base_url: Override base URL
        deployment_name: Override Azure OpenAI deployment name
        api_version: Override Azure OpenAI API version
        **kwargs: Additional model-specific parameters
    
    Returns:
        LlamaIndex LLM model or None if LlamaIndex not available
        
    Raises:
        Exception: If model creation fails
    """  
    try:
        # Get agent-specific configuration with fallbacks
        config = _get_agent_config(agent_name, provider, model_name, temperature, api_key, base_url, deployment_name, api_version)
        
        debug_print(f"DEBUG: LlamaIndex LLM Provider: {config['provider']}", agent_name=agent_name)
        debug_print(f"DEBUG: LlamaIndex Model Name: {config['model_name']}", agent_name=agent_name)
        debug_print(f"DEBUG: LlamaIndex Temperature: {config['temperature']}", agent_name=agent_name)
        
        if config['provider'] == "ollama":
            return _create_llamaindex_ollama(config, agent_name, **kwargs)
        elif config['provider'] == "azureopenai":
            return _create_llamaindex_azure_openai(config, agent_name, **kwargs)
        else:  # Default to OpenAI
            return _create_llamaindex_openai(config, agent_name, **kwargs)
            
    except Exception as e:
        error_print(f"ERROR: Failed to create LlamaIndex LLM model in {agent_name}: {str(e)}")
        raise


def _create_llamaindex_ollama(config: Dict[str, Any], agent_name: str, **kwargs: Any):
    """Create LlamaIndex Ollama model instance."""
    debug_print(f"DEBUG: Creating LlamaIndex Ollama model: {config['model_name']} at {config['base_url']}", agent_name=agent_name)
    
    model_params = {
        "model": config['model_name'],
        "base_url": config['base_url'],
        "temperature": config['temperature'],
        "request_timeout": 120,
        **kwargs
    }
    
    return LlamaOllama(**model_params)


def _create_llamaindex_azure_openai(config: Dict[str, Any], agent_name: str, **kwargs: Any):
    """Create LlamaIndex Azure OpenAI model instance."""
        
    debug_print(f"DEBUG: Creating LlamaIndex Azure OpenAI model: {config['model_name']} at {config['base_url']}", agent_name=agent_name)
    
    model_params = {
        "model": config['model_name'],
        "azure_endpoint": config['base_url'],
        "api_key": config['api_key'],
        "api_version": config['api_version'],
        "engine": config['deployment_name'],
        "temperature": config['temperature'],
        **kwargs
    }
    
    return LlamaAzureOpenAI(**model_params)


def _create_llamaindex_openai(config: Dict[str, Any], agent_name: str, **kwargs: Any):
    """Create LlamaIndex OpenAI model instance."""
        
    debug_print(f"DEBUG: Creating LlamaIndex OpenAI model: {config['model_name']} at {config['base_url']}", agent_name=agent_name)
    
    # For standard OpenAI, use the OpenAI class
    if "api.openai.com" in config['base_url']:
        model_params = {
            "model": config['model_name'],
            "api_key": config['api_key'],
            "temperature": config['temperature'],
            **kwargs
        }
        return LlamaOpenAI(**model_params)
    else:
        # For other endpoints, use Azure AI Completions
        model_params = {
            "model_name": config['model_name'],
            "endpoint": config['base_url'],
            "credential": config['api_key'],
            "temperature": config['temperature'],
            **kwargs
        }
        return AzureAICompletionsModel(**model_params)
