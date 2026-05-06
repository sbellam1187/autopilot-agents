"""
Centralized Debug Utilities for all agents.
This module consolidates the debug functions that were duplicated
across multiple agent files.
"""

import os
import json
import traceback
from typing import Any, Optional, Union, Callable
from langchain_core.messages import AIMessage
from langgraph.types import Command
from langgraph.graph import END

def get_debug_enabled(agent_name: str) -> bool:
    """
    Get debug status for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., "AZURE", "SUPERVISOR", "GITHUB")
        
    Returns:
        bool: True if debug is enabled for this agent
        
    Environment variables checked (in order of preference):
    1. {AGENT_NAME}_AGENT_DEBUG (e.g., AZURE_AGENT_DEBUG)
    2. {AGENT_NAME}_DEBUG (e.g., AZURE_DEBUG)
    3. GLOBAL_DEBUG (fallback for all agents)
    
    Accepted values for enabling: "true", "1", "yes" (case insensitive)
    Default: false (debug disabled)
    """
    agent_upper = agent_name.upper()
    
    # Check agent-specific debug flags in order of preference
    env_vars = [
        f"{agent_upper}_AGENT_DEBUG",
        f"{agent_upper}_DEBUG", 
        "GLOBAL_DEBUG"
    ]
    
    for env_var in env_vars:
        value = os.environ.get(env_var)
        if value is not None:
            return value.lower() in ("true", "1", "yes")
    
    # Default to false if no debug flags are set
    return False


async def debug_print(*args, agent_name: str = "UNKNOWN", **kwargs):
    """
    Conditional debug print function (async version).
    
    Args:
        *args: Arguments to print
        agent_name: Name of the agent calling this function
        **kwargs: Keyword arguments for print function
    """
    if get_debug_enabled(agent_name):
        print(f"[{agent_name}]", *args, **kwargs)


def debug_print_sync(*args, agent_name: str = "UNKNOWN", **kwargs):
    """
    Conditional debug print function (sync version for module initialization).
    
    Args:
        *args: Arguments to print
        agent_name: Name of the agent calling this function
        **kwargs: Keyword arguments for print function
    """
    if get_debug_enabled(agent_name):
        print(f"[{agent_name}]", *args, **kwargs)


async def debug_state(state: Any, label: str = "State", agent_name: str = "UNKNOWN"):
    """
    Helper function to safely debug state objects.
    
    Args:
        state: State object to debug
        label: Label for the debug output
        agent_name: Name of the agent calling this function
    """
    if not get_debug_enabled(agent_name):
        return
        
    try:
        await debug_print(f"DEBUG: {label} type: {type(state)}", agent_name=agent_name)
        await debug_print(f"DEBUG: {label} dir: {dir(state)}", agent_name=agent_name)
        
        if hasattr(state, 'keys'):
            await debug_print(f"DEBUG: {label} keys: {list(state.keys())}", agent_name=agent_name)
            for key in state.keys():
                try:
                    value = state[key]
                    await debug_print(f"DEBUG: {label}['{key}'] = {type(value).__name__}: {str(value)[:200]}...", agent_name=agent_name)
                except Exception as e:
                    await debug_print(f"DEBUG: {label}['{key}'] - Error accessing: {e}", agent_name=agent_name)
        else:
            await debug_print(f"DEBUG: {label} value: {str(state)[:200]}...", agent_name=agent_name)
            
    except Exception as e:
        await debug_print(f"DEBUG: Error debugging {label}: {e}", agent_name=agent_name)


async def safe_json_serialize(obj: Any, label: str = "Object", agent_name: str = "UNKNOWN") -> str:
    """
    Helper to safely serialize objects for debugging.
    
    Args:
        obj: Object to serialize
        label: Label for the object
        agent_name: Name of the agent calling this function
        
    Returns:
        str: JSON representation or error message
    """
    if not get_debug_enabled(agent_name):
        return "<Debug disabled>"
        
    try:
        return json.dumps(obj, default=str, indent=2)
    except Exception as e:
        await debug_print(f"DEBUG: Cannot serialize {label}: {e}", agent_name=agent_name)
        return f"<Non-serializable {type(obj).__name__}>"


async def error_print(*args, **kwargs):
    """
    Always print error messages regardless of debug settings (async version).
    
    Args:
        *args: Arguments to print
        **kwargs: Keyword arguments for print function
    """
    print(*args, **kwargs)


def error_print_sync(*args, **kwargs):
    """
    Always print error messages regardless of debug settings (sync version).
    
    Args:
        *args: Arguments to print
        **kwargs: Keyword arguments for print function
    """
    print(*args, **kwargs)


async def handle_agent_error(
    error: Exception, 
    context: str, 
    agent_name: str = "UNKNOWN",
    include_traceback: bool = True,
    fallback_message: Optional[str] = None
):
    """
    Centralized error handling for all agents.
    
    Args:
        error: The exception that occurred
        context: Context description for the error (e.g., "chat_node", "tool_node")
        agent_name: Name of the agent where error occurred
        include_traceback: Whether to include full traceback in error output
        fallback_message: Custom fallback message for users
        
    Returns:
        Command with error handling that goes to END (if langgraph available)
    """
    # Always print ERROR messages regardless of debug flag
    await error_print(f"ERROR: Exception in {agent_name} {context}: {str(error)}")
    await error_print(f"ERROR: Exception type: {type(error)}")
    
    if include_traceback:
        await error_print(f"ERROR: Traceback: {traceback.format_exc()}")
    
    # Create user-friendly error message
    if fallback_message:
        user_message = fallback_message
    else:
        user_message = f"I encountered an error while processing your request: {str(error)}. Please try again or rephrase your question."
    
    return Command(goto=END, update={"messages": [AIMessage(content=user_message)]})


async def handle_graph_compilation_error(
    error: Exception, 
    agent_name: str,
    fallback_graph_creator: Optional[Callable] = None
):
    """
    Handle graph compilation errors with optional fallback.
    
    Args:
        error: The compilation exception
        agent_name: Name of the agent
        fallback_graph_creator: Optional function to create a fallback graph
        
    Returns:
        Either re-raises the error or returns a fallback graph
    """
    await error_print(f"ERROR: Failed to compile {agent_name} agent graph: {str(error)}")
    await error_print(f"ERROR: Traceback: {traceback.format_exc()}")
    
    if fallback_graph_creator:
        try:
            await error_print(f"WARNING: Creating fallback graph for {agent_name} agent")
            return fallback_graph_creator()
        except Exception as fallback_error:
            await error_print(f"ERROR: Fallback graph creation also failed: {str(fallback_error)}")
    
    # Re-raise the original error if no fallback or fallback failed
    raise error


async def log_error_context(
    error: Exception,
    context: str,
    agent_name: str,
    additional_info: Optional[dict] = None
):
    """
    Log error with additional context for debugging.
    
    Args:
        error: The exception that occurred
        context: Context description
        agent_name: Name of the agent
        additional_info: Optional dict with additional debugging info
    """
    await debug_print(f"ERROR CONTEXT: {context}", agent_name=agent_name)
    await debug_print(f"ERROR DETAILS: {str(error)}", agent_name=agent_name)
    await debug_print(f"ERROR TYPE: {type(error)}", agent_name=agent_name)
    
    if additional_info:
        for key, value in additional_info.items():
            await debug_print(f"ERROR INFO - {key}: {value}", agent_name=agent_name)
    
    await debug_print(f"ERROR TRACEBACK: {traceback.format_exc()}", agent_name=agent_name)
