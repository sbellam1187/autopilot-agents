"""
Deep Agent using LangGraph's create_deep_agent.
This agent handles deep research and tasks using multi-agents and mcp servers.

Debug Configuration:
- Set environment variable DEEP_AGENT_DEBUG=false to disable debug output
- Default: debug output is enabled
"""

from deepagents import create_deep_agent, SubAgent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState, StateGraph, END
import os
import asyncio

# Import utility functions
from app.utils import create_llm_model, debug_print, handle_graph_compilation_error, get_debug_enabled, get_user_api_key
from app.utils.prompt_loader import load_prompt
from app.auth.user_context import require_user

# Define agent name for debugging
AGENT_NAME = "DEEP_AGENT"

class DeepAgentState(MessagesState):
    """State for the Deep Agent"""
    pass

# MCP configuration
def get_mcp_config(token: str, github_token: str) -> dict:
    """Get MCP configuration"""
    # Ensure the token has the proper Bearer prefix
    if not token.startswith('Bearer '):
        token = f"Bearer {token}"
    if not github_token.startswith('Bearer '):
        github_token = f"Bearer {github_token}"

    return {
        "github-mcp-server": {
            "url": os.environ.get("GITHUB_MCP_SERVER_URL", "http://localhost:5007/mcp"),
            "transport": "streamable_http",
            "headers": {
                "Authorization": github_token
            },
        },
        # "azure-mcp-server": {
        #     "url": os.environ.get("AZURE_MCP_SERVER_URL", "http://localhost:5008/mcp"),
        #     "transport": "streamable_http",
        #     "headers": {
        #         "Authorization": azure_token
        #     },
        # },
        "graph-mcp-server": {
            "url": os.environ.get("GRAPH_MCP_SERVER_URL", "http://localhost:8002/mcp"),
            "transport": "streamable_http",
            "headers": {
                "Authorization": token
            },
        },
        "caas-mcp-server": {
            "url": os.environ.get("CAAS_MCP_SERVER_URL", "http://localhost:8003/mcp"),
            "transport": "streamable_http",
            "headers": {
                "Authorization": token
            },
        },
    }

async def deep_node(state: DeepAgentState, config: RunnableConfig):
    """
    Deep agent node that creates and uses deep_agent workflow dynamically.
    """
    await debug_print("DEBUG: ===== EXECUTING AGENT NODE =====", agent_name=AGENT_NAME)
    
    try:
        # Get auth token and MCP configuration
        user_ctx, user_token = require_user(config)
        user_id = user_ctx["identity"]
        if user_token is None:
            raise ValueError("Authentication token is required but not provided")

        # Retrieve decrypted API key from database
        github_key = await get_user_api_key(int(user_id), "github", AGENT_NAME)
        if not github_key:
            return {"messages": [{"role": "assistant", "content": "Error: GitHub API key not found. Please configure your GitHub token in the system."}]}

        mcp_config = get_mcp_config(token=user_token, github_token=github_key)

        # Set up the MCP client and get tools dynamically
        client = MultiServerMCPClient(mcp_config)  # type: ignore
        mcp_tools = await client.get_tools()
        await debug_print(f"DEBUG: Loaded {len(mcp_tools)} MCP tools", agent_name=AGENT_NAME)

        # Create specialized agents
        sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.
            Conduct thorough research and then reply to the user with a detailed answer to their question
            only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""

        research_sub_agent = SubAgent(
            name="research-agent",
            description="Used to research more in depth questions. Only give this researcher one topic at a time. Do not pass multiple sub questions to this researcher. Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question.",
            prompt=sub_research_prompt,
            tools=[tool.name for tool in mcp_tools]
        )

        sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.
            You can find the report at `final_report.md`.
            You can find the question/topic for this report at `question.txt`.
            The user may ask for specific areas to critique the report in. Respond to the user with a detailed critique of the report. Things that could be improved.
            Do not write to the `final_report.md` yourself.
            Things to check:
            - Check that each section is appropriately named
            - Check that the report is written as you would find in an essay or a textbook - it should be text heavy, do not let it just be a list of bullet points!
            - Check that the report is comprehensive. If any paragraphs or sections are short, or missing important details, point it out.
            - Check that the article covers key areas of the industry, ensures overall understanding, and does not omit important parts.
            - Check that the article deeply analyzes causes, impacts, and trends, providing valuable insights
            - Check that the article closely follows the research topic and directly answers questions
            - Check that the article has a clear structure, fluent language, and is easy to understand.
            """

        critique_sub_agent = SubAgent(
            name="critique-agent",
            description="Used to critique the final report. Give this agent some infomration about how you want it to critique the report.",
            prompt=sub_critique_prompt,
        )

        agents = [research_sub_agent, critique_sub_agent]
        await debug_print(f"DEBUG: Loaded {len(agents)} specialized agents", agent_name=AGENT_NAME)
        
        # Create the deep agent workflow dynamically
        deep_agent = create_deep_agent(
            tools=mcp_tools,
            instructions=await load_prompt(AGENT_NAME.lower()),
            model=create_llm_model(AGENT_NAME),
            subagents=agents,
        ).with_config({"recursion_limit": 1000})
        
        # Prepare input for the deep agent
        agent_input = {
            "messages": state["messages"]
        }
        
        # Execute the deep agent using ainvoke with metadata
        agent_config: RunnableConfig = {
            "metadata": {"agent_name": AGENT_NAME.lower()},
            "tags": [AGENT_NAME.lower()]
        }
        
        if get_debug_enabled(AGENT_NAME):
            agent_response = await deep_agent.ainvoke(agent_input, config=agent_config, print_mode="values")
        else:
            agent_response = await deep_agent.ainvoke(agent_input, config=agent_config)

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
        workflow = StateGraph(DeepAgentState)
        workflow.add_node("deep_node", deep_node)
        workflow.set_entry_point("deep_node")
        workflow.add_edge("deep_node", END)

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