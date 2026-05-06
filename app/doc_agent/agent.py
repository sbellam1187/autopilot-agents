"""
Graph Agent using LangGraph's create_react_agent.
This agent handles document generation using multi-agents.

Debug Configuration:
- Set environment variable DOC_AGENT_DEBUG=false to disable debug output
- Default: debug output is enabled
"""

from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState, StateGraph, END
from typing_extensions import Dict, List, Any, Optional
import os
import asyncio

# Import utility functions
from app.utils import create_llm_model, debug_print, handle_graph_compilation_error, get_debug_enabled
from app.utils.prompt_loader import load_prompt
from app.auth.user_context import require_user

# Import specialized agents
from app.graph_agent.agent import graph as graph_agent
from app.rag_agent.agent import graph as rag_agent
from app.github_agent.agent import graph as github_agent

# Define agent name for debugging
AGENT_NAME = "DOC_AGENT"

class DocAgentState(MessagesState):
    """State for the Document Agent"""
    # Documentation requirements
    github_repos: Optional[List[str]]
    application_shortname: Optional[str]
    documentation_types: Optional[List[str]]
    
    # Analysis results
    application_details: Optional[Dict[str, Any]]
    repository_analysis: Optional[Dict[str, Any]]
    
    # Generated documentation
    generated_docs: Optional[Dict[str, str]]

# Get document pattern based on type
def get_doc_template(doc_type: str) -> str:
    """
    Get the markdown template content based on the documentation type.
    
    Parameters:
    doc_type (str): The type of documentation template to retrieve.
                   Valid values: 'architecture', 'dependency', 'deployment'
    
    Returns:
    str: The content of the corresponding markdown template file.
    
    Raises:
    ValueError: If doc_type is not one of the valid values.
    FileNotFoundError: If the template file is not found.
    """
    # Map documentation types to template files
    templates = {
        'architecture': 'ARCHITECTURE_TEMPLATE.md',
        'dependency': 'DEPENDENCY_TEMPLATE.md', 
        'deployment': 'DEPLOYMENT_TEMPLATE.md'
    }
    
    # Validate doc_type
    if doc_type.lower() not in templates:
        raise ValueError(f"Invalid doc_type: {doc_type}")
    
    # Read and return template content
    template_file = templates[doc_type.lower()]
    files_dir = os.path.join(os.path.dirname(__file__), 'files')
    template_path = os.path.join(files_dir, template_file)
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()
    
async def doc_node(state: DocAgentState, config: RunnableConfig):
    """
    Doc agent node that creates and uses supervisor workflow dynamically.
    """
    await debug_print("DEBUG: ===== EXECUTING AGENT NODE =====", agent_name=AGENT_NAME)
    
    try:
        # Get specialized agents
        agents = [graph_agent, rag_agent, github_agent]
        await debug_print(f"DEBUG: Loaded {len(agents)} specialized agents", agent_name=AGENT_NAME)
        
        # Create the doc agent workflow dynamically
        agent = create_supervisor(
            agents=agents,
            model=create_llm_model(AGENT_NAME),
            tools=[get_doc_template],
            prompt=await load_prompt(AGENT_NAME.lower()),
            parallel_tool_calls=False,
            output_mode="last_message",
            add_handoff_messages=True,
            supervisor_name=AGENT_NAME.lower()
        )
        
        # Compile the doc agent workflow
        doc_agent = agent.compile(name=AGENT_NAME.lower())
        await debug_print("DEBUG: Supervisor workflow created and compiled", agent_name=AGENT_NAME)
        
        # Prepare input for the doc agent
        agent_input = {
            "messages": state["messages"]
        }
        
        # Execute the doc agent using ainvoke with metadata
        agent_config: RunnableConfig = {
            "metadata": {"agent_name": AGENT_NAME.lower()},
            "tags": [AGENT_NAME.lower()]
        }
        
        if get_debug_enabled(AGENT_NAME):
            agent_response = await doc_agent.ainvoke(agent_input, config=agent_config, print_mode="values")
        else:
            agent_response = await doc_agent.ainvoke(agent_input, config=agent_config)

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
    """
    await debug_print("DEBUG: ===== BUILDING AGENT WORKFLOW =====", agent_name=AGENT_NAME)

    try:
        # Define the workflow graph
        workflow = StateGraph(DocAgentState)
        workflow.add_node("doc_node", doc_node)
        workflow.set_entry_point("doc_node")
        workflow.add_edge("doc_node", END)

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