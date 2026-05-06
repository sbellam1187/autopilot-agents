"""
RAG Agent using LangGraph's create_react_agent.
This agent performs agentic RAG against existing vector database using LlamaIndex.

Debug Configuration:
- Set environment variable RAG_AGENT_DEBUG=false to disable debug output
- Default: debug output is enabled
"""

from typing import List, Dict, Any, Optional, Union
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState, StateGraph, END
from langchain.tools import tool
import asyncio

# Import utility functions
from app.utils import create_llm_model, debug_print, handle_graph_compilation_error, get_debug_enabled, create_rag_query_engine, search_documentation
from app.utils.prompt_loader import load_prompt

# Define agent name for debugging
AGENT_NAME = "RAG_AGENT"

class RAGAgentState(MessagesState):
    """State for the RAG Agent"""
    rag_results: Optional[List[Dict[str, Any]]]

# Initialize global query engine
_query_engine = create_rag_query_engine(AGENT_NAME)

@tool
def search_documentation_tool(query: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Search documentation, tech radar, project information, and knowledge base using RAG.
    
    Args:
        query: Search query (string) or query parameters (dict)
        
    Returns:
        Dict containing search results and source information
    """
    return search_documentation(AGENT_NAME, query)

async def rag_node(state: RAGAgentState, config: RunnableConfig):
    """
    RAG agent node that uses search tools dynamically.
    """
    await debug_print("DEBUG: ===== EXECUTING AGENT NODE =====", agent_name=AGENT_NAME)
    
    try:
        # Create the React agent with RAG tools
        react_agent = create_react_agent(
            model=create_llm_model(AGENT_NAME),
            tools=[search_documentation_tool],
            prompt=await load_prompt(AGENT_NAME.lower()),
            name=AGENT_NAME.lower()
        )
        
        # Prepare input for the react agent
        agent_input = {
            "messages": state["messages"]
        }
        
        # Execute the react agent using ainvoke with metadata
        agent_config: RunnableConfig = {
            "metadata": {"agent_name": AGENT_NAME.lower()},
            "tags": [AGENT_NAME.lower()]
        }
        
        if get_debug_enabled(AGENT_NAME):
            agent_response = await react_agent.ainvoke(agent_input, config=agent_config, print_mode="values")
        else:
            agent_response = await react_agent.ainvoke(agent_input, config=agent_config)
        
        await debug_print("DEBUG: Agent completed successfully", agent_name=AGENT_NAME)
        
        # Return the updated messages
        return {"messages": agent_response.get("messages", [])}
            
    except Exception as e:
        await debug_print(f"ERROR: Failed to execute agent: {str(e)}", agent_name=AGENT_NAME)
        await handle_graph_compilation_error(e, AGENT_NAME)
        raise

async def create_graph():
    """
    Create the graph following LangGraph patterns.
    Workflow with dynamic RAG tool loading.
    """
    await debug_print("DEBUG: ===== BUILDING AGENT WORKFLOW =====", agent_name=AGENT_NAME)
    
    try:
        # Define the workflow graph
        workflow = StateGraph(RAGAgentState)
        workflow.add_node("rag_node", rag_node)
        workflow.set_entry_point("rag_node")
        workflow.add_edge("rag_node", END)
        
        # Compile the workflow graph
        graph = workflow.compile(name=f"{AGENT_NAME.lower()}")
        
        await debug_print("DEBUG: Agent workflow created successfully", agent_name=AGENT_NAME)
        return graph
        
    except Exception as e:
        await debug_print(f"ERROR: Failed to build agent workflow: {str(e)}", agent_name=AGENT_NAME)
        await handle_graph_compilation_error(e, AGENT_NAME)
        raise

# Create and export the graph
graph = asyncio.run(create_graph())