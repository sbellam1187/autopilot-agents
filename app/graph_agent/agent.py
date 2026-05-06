"""
Graph Agent using LangGraph's create_react_agent.
This agent handles graph database operations using MCP servers.

Debug Configuration:
- Set environment variable GRAPH_AGENT_DEBUG=false to disable debug output
- Default: debug output is enabled
"""

from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState, StateGraph, END
import os
import asyncio

# Import utility functions
from app.utils import create_llm_model, debug_print, handle_graph_compilation_error, get_debug_enabled
from app.utils.prompt_loader import load_prompt
from app.auth.user_context import require_user

# Define agent name for debugging
AGENT_NAME = "GRAPH_AGENT"

class GraphAgentState(MessagesState):
    """State for the Graph Agent"""
    pass

def get_mcp_config(token: str) -> dict:
    """Get MCP configuration"""
    # Ensure the token has the proper Bearer prefix
    if not token.startswith('Bearer '):
        token = f"Bearer {token}"
        
    return {
        "graph-mcp-server": {
            "url": os.environ.get("GRAPH_MCP_SERVER_URL", "http://localhost:8002/mcp"),
            "transport": "streamable_http",
            "headers": {
                "Authorization": token
            },
        },
    }

async def graph_node(state: GraphAgentState, config: RunnableConfig):
    """
    Agent node that uses MCP tools dynamically.
    """
    await debug_print("DEBUG: ===== EXECUTING AGENT NODE =====", agent_name=AGENT_NAME)
    
    try:
        # Get auth token and MCP configuration
        user_ctx, user_token = require_user(config)
        if user_token is None:
            raise ValueError("Authentication token is required but not provided")
        mcp_config = get_mcp_config(user_token)
        
        # Set up the MCP client and get tools dynamically
        client = MultiServerMCPClient(mcp_config)  # type: ignore
        mcp_tools = await client.get_tools()
        await debug_print(f"DEBUG: Loaded {len(mcp_tools)} MCP tools", agent_name=AGENT_NAME)
        
        # Create the React agent with MCP tools
        react_agent = create_react_agent(
            model=create_llm_model(AGENT_NAME),
            tools=mcp_tools,
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
    Workflow with dynamic MCP tool loading.
    """
    await debug_print("DEBUG: ===== BUILDING AGENT WORKFLOW =====", agent_name=AGENT_NAME)

    try:
        # Define the workflow graph
        workflow = StateGraph(GraphAgentState)
        workflow.add_node("graph_node", graph_node)
        workflow.set_entry_point("graph_node")
        workflow.add_edge("graph_node", END)
        
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