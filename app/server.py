"""
FastAPI server for multiple LangGraph agents with token usage tracking.
"""

import os
import sys
import logging
import json
import uvicorn
from typing import Optional, List, Any, Dict
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from collections import defaultdict
from dotenv import load_dotenv
from langgraph.types import Command
load_dotenv()

# Add the app directory to Python path when running directly
if __name__ == "__main__":
    # Add the directory containing this file to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging for token tracking
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Import your graphs
from app.auth.fastapi_auth import get_current_user, get_auth_token
from app.graph_agent.agent import graph as graph_agent_graph
from app.rag_agent.agent import graph as rag_agent_graph
from app.github_agent.agent import graph as github_agent_graph
from app.azure_agent.agent import graph as azure_agent_graph
from app.caas_agent.agent import graph as caas_agent_graph
from app.doc_agent.agent import graph as doc_agent_graph
from app.deep_agent.agent import graph as deep_agent_graph
from app.supervisor_agent.agent import graph as supervisor_agent_graph

app = FastAPI()

AGENTS = {
    "supervisor_agent": {
        "name": "supervisor_agent",
        "description": "Supervisor agent that intelligently routes requests to specialized agents.",
        "graph": supervisor_agent_graph,
    },
    "graph_agent": {
        "name": "graph_agent",
        "description": "An graph agent to use as a starting point for initiating graph requests.",
        "graph": graph_agent_graph,
    },
    "rag_agent": {
        "name": "rag_agent",
        "description": "An RAG agent that searches documentation and project information to answer questions.",
        "graph": rag_agent_graph,
    },
    "github_agent": {
        "name": "github_agent",
        "description": "An github agent to use as a starting point for initiating GitHub requests.",
        "graph": github_agent_graph,
    },
    "azure_agent": {
        "name": "azure_agent",
        "description": "An azure agent to use as a starting point for initiating Azure requests.",
        "graph": azure_agent_graph,
    },
    "caas_agent": {
        "name": "caas_agent",
        "description": "An CAAS agent to use as a starting point for initiating CAAS requests.",
        "graph": caas_agent_graph,
    },
    "doc_agent": {
        "name": "doc_agent",
        "description": "An doc agent to use as a starting point for generating document requests.",
        "graph": doc_agent_graph,
    },
    "deep_agent": {
        "name": "deep_agent",
        "description": "An deep agent to use as a starting point for generating deep research or complex tasks requests.",
        "graph": deep_agent_graph,
    }
}

AGENT_REGISTRY = {
    "supervisor_agent": supervisor_agent_graph,
    "graph_agent": graph_agent_graph,
    "rag_agent": rag_agent_graph,
    "github_agent": github_agent_graph,
    "azure_agent": azure_agent_graph,
    "caas_agent": caas_agent_graph,
    "doc_agent": doc_agent_graph,
    "deep_agent": deep_agent_graph,
}

AUTH_JWKS = os.getenv("PF_JWKS")
AUTH_ISSUER = os.getenv("PF_ISSUER")
AUTH_AUDIENCE = os.getenv("PF_AUDIENCE")

if not AUTH_JWKS or not AUTH_ISSUER or not AUTH_AUDIENCE:
    raise Exception("PF_JWKS, PF_ISSUER, or PF_AUDIENCE environment variables are not set")

# Note: Authentication is now handled via FastAPI dependencies rather than middleware
# The auth logic is in app.auth.fastapi_auth and reuses the LangGraph JWT provider

origins =[
    "http://localhost:3000",
    "https://autopilot-nonprod.cloud.aa.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AISDKMessage(BaseModel):
    role: str
    content: str
    id: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[AISDKMessage]
    agent: Optional[str] = 'supervisor_agent'
    sessionId: str

def convert_to_langchain_messages(messages: List[AISDKMessage]) -> List[Any]:
    '''Convert AI SDK messages to LangChain format.'''

    lc_messages = []

    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content, id=msg.id))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content, id=msg.id))
        elif msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content, id=msg.id))
        else:
            raise ValueError(f"Unknown message role: {msg.role}")
    return lc_messages

@app.post("/api/chat")
async def chat_with_agent(
    request: ChatRequest, 
    user: Dict[str, Any] = Depends(get_current_user),
    auth_token: str = Depends(get_auth_token)
):
    """
    Chat endpoint that requires authentication.
    
    The user information and auth token are automatically injected via FastAPI dependencies.
    """
    try:
        agent_name = request.agent or "supervisor_agent"
        session_id = request.sessionId

        if agent_name not in AGENT_REGISTRY:
            raise HTTPException(status_code=400, detail=f"Agent `{agent_name}` not found. Available agents: {list(AGENT_REGISTRY.keys())}")

        lc_messages = convert_to_langchain_messages(request.messages)
        agent_graph = AGENT_REGISTRY[agent_name]

        # Include user context and auth token in the agent configuration
        config = {
            "thread_id": session_id,
            "checkpoint_ns": f"{agent_name}_checkpoint",
            "checkpoint_id": f"{agent_name}_{session_id}",
            "configurable": {
                "langgraph_auth_user": user,
                "authorization": auth_token,
                "user_id": user["identity"]
            }
        }

        try:
            current_state = await agent_graph.aget_state(config)
            is_continuing_conversation = current_state.values is not None and len(current_state.values.get("messages", [])) > 0
            logger.info("Found existing conversation state")
        except:
            is_continuing_conversation = False
            logger.info("No existing conversation state")

        # Prepare the state for the agent
        if is_continuing_conversation:
            if lc_messages:
                new_message = lc_messages[-1]
                state = {
                    "messages": [new_message],
                    "thoughts": [],
                    "tool_calls_made": []
                }
            else:
                raise HTTPException(status_code=400, detail="No messages provided")
        else:
            state = {
                "messages": lc_messages,
                "thoughts": [],
                "tool_calls_made": []
            }

        async def stream():
            tools = defaultdict(int)
            supervisor_text_started = False

            async for event in agent_graph.astream_events(state, config=config, version="v2"):
                # Extract agent name from event metadata, fallback to original agent name
                event_agent_name = event.get("metadata", {}).get("agent_name", agent_name)

                if event["event"] == "on_chat_model_start":
                    data = {"type": "start", "messageId": event["run_id"]}
                    yield f"data: {json.dumps(data)}\n\n"

                elif event["event"] == "on_chat_model_stream":
                    chunk_content = event['data']['chunk'].content

                    # Only stream text deltas from supervisor_agent
                    if chunk_content is not None and chunk_content != "" and event_agent_name == "supervisor_agent":
                        if not supervisor_text_started:
                            supervisor_text_started = True
                            data = {"type": "text-start", "id": event["run_id"]}
                            yield f"data: {json.dumps(data)}\n\n"

                        data = {"type": "text-delta", "id": event["run_id"], "delta": event['data']['chunk'].content}
                        yield f"data: {json.dumps(data)}\n\n"

                    # Stream all tool calls regardless of agent
                    message_chunk = event['data']['chunk']
                    if hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
                        tool_chunks = message_chunk.tool_call_chunks

                        for chunk in tool_chunks:
                            try:
                                # Ensure chunk has required properties
                                if not isinstance(chunk, dict):
                                    continue

                                chunk_index = chunk.get("index")
                                chunk_id = chunk.get("id")
                                chunk_name = chunk.get("name")
                                chunk_args = chunk.get("args", "")

                                if chunk_index is None:
                                    continue

                                if chunk_name and chunk_id:  # Starting a new tool call
                                    tools[chunk_index] = chunk_id
                                    data = {
                                        "type": "tool-input-start",
                                        "toolCallId": chunk_id,
                                        "toolName": chunk_name
                                    }
                                    yield f"data: {json.dumps(data)}\n\n"
                                elif chunk_args:  # Continuing tool call with arguments
                                    tool_call_id = tools.get(chunk_index)
                                    if tool_call_id:
                                        data = {
                                            "type": "tool-input-delta",
                                            "toolCallId": tool_call_id,
                                            "inputTextDelta": chunk_args
                                        }
                                        yield f"data: {json.dumps(data)}\n\n"
                            except Exception as e:
                                logger.error(f"Error in tool calling: {e}")
                                continue

                elif event["event"] == "on_chat_model_end":
                    # Only emit text-end for supervisor_agent when it was actually streaming
                    if supervisor_text_started and event_agent_name == "supervisor_agent":
                        data = {"type": "text-end", "id": event["run_id"]}
                        yield f"data: {json.dumps(data)}\n\n"
                        supervisor_text_started = False

                    # Stream all tool-input-available events regardless of agent
                    if event['data']['output'].tool_calls:
                        tool_calls = event['data']['output'].tool_calls

                        for call in tool_calls:
                            data = {"type": "tool-input-available", "toolCallId": call["id"], "toolName": call["name"], "input": call["args"]}
                            yield f"data: {json.dumps(data)}\n\n"

                    data = {"type": "finish"}
                    yield f"data: {json.dumps(data)}\n\n"
                    tools = defaultdict(int)

                if event["event"] == "on_tool_end":
                    output = event["data"]["output"]

                    if isinstance(output, ToolMessage):
                        data = {"type": "tool-output-available", "toolCallId": output.tool_call_id, "output": output.content}
                        yield f"data: {json.dumps(data)}\n\n"
                    elif isinstance(output, Command):
                            # Handle Command outputs (typically for agent routing)
                            tool_call_id = event["data"].get("input", {}).get("tool_call_id")
                            if tool_call_id:
                                # Extract relevant information from the Command
                                command_info = {
                                    "goto": getattr(output, "goto", None),
                                    "update": getattr(output, "update", None)
                                }

                                # Create a descriptive output message
                                if hasattr(output, "goto") and output.goto:
                                    output_content = f"Routing to agent: {output.goto}"
                                else:
                                    output_content = f"Command executed: {command_info}"

                                data = {
                                    "type": "tool-output-available",
                                    "toolCallId": tool_call_id,
                                    "output": output_content
                                }
                                yield f"data: {json.dumps(data)}\n\n"

            yield "data: [DONE]\n\n"

        response = stream()

        return StreamingResponse(response,
                                media_type="text/event-stream",
                                headers={"Cache-Control": "no-cache",
                                        "Connection": "keep-alive",
                                        "Content-Type": "text/plain; charset=utf-8",
                                        "x-vercel-ai-data-stream": "v1"})

    except Exception as e:
        logger.error(f"Error in chat with agent post: {e}")

# Add a health check endpoint
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok", "auth_system": "langgraph_jwt"}


# Add an endpoint to list available agents
@app.get("/api/agents")
async def list_agents(user: Dict[str, Any] = Depends(get_current_user)):
    """List all available agents. Requires authentication."""
    return {
        "agents": list(AGENTS.keys()),
        "user": user["identity"],
        "agent_details": AGENTS
    }


# Add an endpoint to get user information
@app.get("/api/user")
async def get_user_info(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information. Requires authentication."""
    return {
        "user": user,
        "authenticated": True
    }

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))

    # Determine if we should enable reload based on environment
    # Disable reload by default to prevent double loading during startup
    reload = os.getenv("RELOAD", "false").lower() == "true"

    # Determine the module string based on how we're running
    if __name__ == "__main__":
        # Running directly, use the current module
        module_str = "__main__:app"
    else:
        # Running via Poetry/package, use the full module path
        module_str = "app.server:app"

    uvicorn.run(
        module_str,
        host="0.0.0.0",
        port=port,
        reload=reload,
    )

if __name__ == "__main__":
    main()
