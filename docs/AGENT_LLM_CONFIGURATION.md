# Agent-Specific LLM Configuration Guide

This guide explains how agents can customize their LLM configuration while using the centralized factory approach.

## Overview

The `create_llm_model` function now supports agent-specific configuration through multiple methods:

1. **Function Parameters**: Override specific parameters when calling the function
2. **Agent-Specific Environment Variables**: Set environment variables with agent name prefix
3. **Configuration Objects**: Define agent-specific configuration in code
4. **Convenience Functions**: Use helper functions for common scenarios

## Configuration Priority

Configuration is resolved in the following priority order (highest to lowest):

1. **Function Parameters** - Direct parameters passed to `create_llm_model()`
2. **Agent-Specific Environment Variables** - Variables prefixed with agent name
3. **Global Environment Variables** - Standard environment variables
4. **Default Values** - Built-in defaults

## Method 1: Function Parameters

Override specific parameters while keeping others default:

```python
# Use a different model for this agent
model = create_llm_model(
    agent_name="AZURE",
    model_name="gpt-3.5-turbo",
    temperature=0.7
)

# Use Ollama for this agent
model = create_llm_model(
    agent_name="GITHUB", 
    provider="ollama",
    model_name="codellama:7b",
    base_url="http://localhost:11434"
)
```

## Method 2: Agent-Specific Environment Variables

Set environment variables with the agent name prefix:

```bash
# Azure agent will use these settings
export AZURE_LLM_PROVIDER=openai
export AZURE_MODEL=gpt-3.5-turbo
export AZURE_TEMPERATURE=0.7
export AZURE_API_KEY=your_api_key

# GitHub agent will use these settings  
export GITHUB_LLM_PROVIDER=ollama
export GITHUB_MODEL=codellama:7b
export GITHUB_BASE_URL=http://localhost:11434

# All other agents will use global settings
export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-4o
```

Then in your agent code:
```python
# This will automatically use agent-specific env vars if they exist
model = create_llm_model("AZURE")
```

## Method 3: Configuration Objects

Define configuration in your agent code:

```python
AGENT_LLM_CONFIG = {
    "provider": "openai",
    "model_name": "gpt-3.5-turbo", 
    "temperature": 0.7,
    "max_tokens": 1000,
}

def get_agent_llm():
    if AGENT_LLM_CONFIG:
        return create_llm_model(AGENT_NAME, **AGENT_LLM_CONFIG)
    return create_llm_model(AGENT_NAME)
```

## Method 4: Convenience Functions

Use helper functions for common scenarios:

```python
from utils import create_agent_specific_llm

# Quick agent-specific configuration
model = create_agent_specific_llm(
    "AZURE",
    "openai", 
    "gpt-3.5-turbo",
    temperature=0.7
)
```

## Supported Parameters

All functions support these parameters:

- `provider`: "openai", "azureopenai", or "ollama"
- `model_name`: Specific model name (e.g., "gpt-4o", "codellama:7b")
- `temperature`: Model temperature (0.0 to 1.0)
- `api_key`: API key override
- `base_url`: Base URL override
- `deployment_name`: Azure OpenAI deployment name
- `api_version`: Azure OpenAI API version
- `**kwargs`: Additional model-specific parameters

## Environment Variable Reference

### Global Variables
- `LLM_PROVIDER`: Default provider for all agents
- `OPENAI_MODEL`: Default OpenAI model name
- `OPENAI_API_KEY`: Default OpenAI API key
- `OPENAI_BASE_URL`: Default OpenAI base URL
- `OLLAMA_MODEL`: Default Ollama model name
- `OLLAMA_BASE_URL`: Default Ollama base URL
- `MODEL_TEMPERATURE`: Default temperature

### Agent-Specific Variables
Replace `{AGENT}` with your agent name (e.g., AZURE, GITHUB):

- `{AGENT}_LLM_PROVIDER`: Provider override for specific agent
- `{AGENT}_MODEL`: Model name override for specific agent  
- `{AGENT}_TEMPERATURE`: Temperature override for specific agent
- `{AGENT}_API_KEY`: API key override for specific agent
- `{AGENT}_BASE_URL`: Base URL override for specific agent
- `{AGENT}_DEPLOYMENT_NAME`: Azure deployment override for specific agent
- `{AGENT}_API_VERSION`: Azure API version override for specific agent

## Configuration Debugging

Check what configuration an agent will use:

```python
from utils import get_agent_model_config

# See resolved configuration without creating model
config = get_agent_model_config("AZURE")
print(f"Azure agent config: {config}")
```

## Example: Multi-Agent Setup

```python
# Environment variables
export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-4o

# Azure agent uses GPT-3.5 with higher temperature
export AZURE_MODEL=gpt-3.5-turbo
export AZURE_TEMPERATURE=0.7

# GitHub agent uses local Ollama
export GITHUB_LLM_PROVIDER=ollama
export GITHUB_MODEL=codellama:7b

# Sample agent uses specific configuration in code
```

Agent implementations:
```python
# azure_agent.py
model = create_llm_model("AZURE")  # Uses gpt-3.5-turbo, temp=0.7

# github_agent.py  
model = create_llm_model("GITHUB")  # Uses Ollama codellama:7b

# sample_agent.py
model = create_llm_model("SAMPLE", model_name="gpt-3.5-turbo", temperature=0.5)

# supervisor_agent.py
model = create_llm_model("SUPERVISOR")  # Uses global defaults (gpt-4o)
```

This approach provides maximum flexibility while maintaining centralized management and consistency across agents.
