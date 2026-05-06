"""
Supervisor Agent using LangGraph Supervisor library.
This agent coordinates between specialized agents using the pre-built supervisor pattern.

Debug Configuration:
- Set environment variable SUPERVISOR_DEBUG=false to disable debug output
- Accepted values for disabling: "false", "0", "no" (case insensitive)
- Default: debug output is enabled
- ERROR messages are always printed regardless of debug setting
"""

from typing import Optional
from langgraph_supervisor import create_supervisor
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState, StateGraph, END
import asyncio

# Import utility functions
from app.utils import create_llm_model, debug_print, handle_graph_compilation_error, get_debug_enabled
from app.utils.prompt_loader import load_prompt

# Import specialized agents
from app.graph_agent.agent import graph as graph_agent
from app.rag_agent.agent import graph as rag_agent
from app.caas_agent.agent import graph as caas_agent
from app.github_agent.agent import graph as github_agent
from app.azure_agent.agent import graph as azure_agent
from app.doc_agent.agent import graph as doc_agent
from app.deep_agent.agent import graph as deep_agent

# Define agent name for debugging
AGENT_NAME = "SUPERVISOR_AGENT"

class SupervisorAgentState(MessagesState):
    """
    State for the Supervisor Agent
    """
    selected_agent: Optional[str]
    routing_reason: Optional[str]

async def supervisor_node(state: SupervisorAgentState, config: RunnableConfig):
    """
    Supervisor agent node that creates and uses supervisor workflow dynamically.
    """
    await debug_print("DEBUG: ===== EXECUTING AGENT NODE =====", agent_name=AGENT_NAME)
    
    try:
        # Get specialized agents
        agents = [graph_agent, rag_agent, caas_agent, github_agent, azure_agent, doc_agent, deep_agent]
        await debug_print(f"DEBUG: Loaded {len(agents)} specialized agents", agent_name=AGENT_NAME)
        
        # Create the supervisor workflow dynamically
        supervisor_workflow = create_supervisor(
            agents=agents,
            model=create_llm_model(AGENT_NAME),
            prompt=await load_prompt(AGENT_NAME.lower()),
            parallel_tool_calls=False,
            output_mode="last_message",
            add_handoff_messages=True,
            supervisor_name=AGENT_NAME.lower()
        )
        
        # Compile the supervisor workflow
        supervisor_app = supervisor_workflow.compile(name=AGENT_NAME.lower())
        await debug_print("DEBUG: Supervisor workflow created and compiled", agent_name=AGENT_NAME)
        
        # Prepare input for the supervisor
        supervisor_input = {
            "messages": state["messages"]
        }
        
        # Execute the supervisor using ainvoke with metadata
        supervisor_config: RunnableConfig = {
            "metadata": {"agent_name": AGENT_NAME.lower()},
            "tags": [AGENT_NAME.lower()]
        }
        
        if get_debug_enabled(AGENT_NAME):
            supervisor_response = await supervisor_app.ainvoke(supervisor_input, config=supervisor_config, print_mode="values")
        else:
            supervisor_response = await supervisor_app.ainvoke(supervisor_input, config=supervisor_config)

        await debug_print("DEBUG: Agent completed successfully", agent_name=AGENT_NAME)

        # Return the updated messages
        return {"messages": supervisor_response.get("messages", [])}
            
    except Exception as e:
        await debug_print(f"ERROR: Failed to execute agent: {str(e)}", agent_name=AGENT_NAME)
        await handle_graph_compilation_error(e, AGENT_NAME)
        raise

async def create_graph():
    """
    Create the graph following LangGraph patterns.
    Workflow with dynamic supervisor creation.
    """
    await debug_print("DEBUG: ===== BUILDING AGENT WORKFLOW =====", agent_name=AGENT_NAME)
    
    try:
        # Define the workflow graph
        workflow = StateGraph(SupervisorAgentState)
        workflow.add_node("supervisor_node", supervisor_node)
        workflow.set_entry_point("supervisor_node")
        workflow.add_edge("supervisor_node", END)
        
        # Compile the workflow graph
        graph = workflow.compile(name=f"{AGENT_NAME.lower()}_workflow")
        
        await debug_print("DEBUG: Agent workflow created successfully", agent_name=AGENT_NAME)
        return graph
        
    except Exception as e:
        await debug_print(f"ERROR: Failed to build agent workflow: {str(e)}", agent_name=AGENT_NAME)
        await handle_graph_compilation_error(e, AGENT_NAME)
        raise

# Create and export the graph
graph = asyncio.run(create_graph())