<div align="center">

# Autopilot Canvas
   
![CopilotKit-Banner](https://github.com/user-attachments/assets/8167c845-0381-45d9-ad1c-83f995d48290)
</div>


![multi-agent-canvas](https://github.com/user-attachments/assets/5953a5a6-5686-4722-9477-5279b67b3dba)


Autopilot Canvas, based on [CopilotKit](https://github.com/CopilotKit/CopilotKit) is an open-source multi-agent chat interface that lets you manage multiple agents in one dynamic conversation. It's built with Next.js, LangGraph Agents, and CopilotKit to help with general AA QnA, exploring the Apollo supergraph, retrieve and generate documents, and general-purpose tasks through MCP servers.

## Existing Agents

This project includes built-in agents:
- **MCP Agent**: A general-purpose agent capable of handling various tasks through configurable MCP servers.
- **Sample Agent**: A simple agent for weather queries and general conversation.
- **RAG Agent**: A specialized Retrieval-Augmented Generation agent for tech radar, technology standards, and project documentation.
- **Supervisor Agent**: An intelligent routing agent that analyzes user requests and delegates to the most appropriate specialized agent.

## Agent Architecture

### Supervisor Agent
The Supervisor Agent acts as an intelligent router that:
- Analyzes incoming user requests
- Determines which specialized agent is best suited to handle the request
- Routes to the Sample Agent, MCP Agent, or RAG Agent based on context
- Provides clear reasoning for its routing decisions

#### Routing Logic
- **Routes to Sample Agent**: Weather queries, general conversation, proverbs
- **Routes to MCP Agent**: Mathematical calculations, data queries, AA Graph queries, technical integrations
- **Routes to RAG Agent**: Tech radar queries, technology standards, tools, frameworks, Project Yoda, Autopilot documentation

### Sample Agent
A general-purpose conversational agent that can:
- Get weather information for any location
- Handle basic conversational queries
- Provide general assistance
- Work with proverbs and sayings

### MCP Agent
A specialized agent for complex operations that can:
- Query the AA Graph for airline/aviation data
- Perform mathematical calculations
- Access MCP (Model Context Protocol) servers
- Handle complex data queries and integrations

### RAG Agent
A Retrieval-Augmented Generation agent that can:
- Search tech radar documentation
- Find information about technology standards and best practices
- Retrieve details about tools and frameworks
- Access Project Yoda and Autopilot documentation
- Provide context-aware responses with source attribution

## Getting Started

This project is designed to work with [LangGraph Server](https://langchain-ai.github.io/langgraph/concepts/langgraph_server/#langgraph-server) and [LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/), a visual debugging IDE for LangGraph applications.

### Prerequisites

1. **Install dependencies**:

```sh
# Create python 3.12 virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
poetry install
```

2. **Configure environment variables**:

```sh
cp example.env .env
```

### LLM Provider Configuration

The backend supports multiple LLM providers. Configure your preferred provider in the `.env` file:

#### For OpenAI (default):
```sh
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_TEMPERATURE=0
```

#### For Azure OpenAI:
```sh
LLM_PROVIDER=azureopenai
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
MODEL_TEMPERATURE=0
```

#### For Ollama:
```sh
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3
OLLAMA_BASE_URL=http://localhost:11434
MODEL_TEMPERATURE=0
```

### Running with LangGraph Server

3. **Start the LangGraph Server**:

```sh
langgraph dev --port 8123
```

This will start the server at `http://localhost:8123` and automatically open LangGraph Studio in your browser.

### Using LangGraph Studio

LangGraph Studio provides a visual interface for:
- **Interactive debugging**: Step through your agent workflows
- **State inspection**: View and edit agent state at any point
- **Real-time development**: Hot reload changes as you edit your code
- **Multi-agent visualization**: See how agents interact and route requests

### Available Agents

The following agents are configured and available in LangGraph Studio:

- **`supervisor_agent`**: Intelligent routing agent that delegates to specialized agents
- **`graph_agent`**: Handles AA Graph and airline data queries  
- **`rag_agent`**: Retrieval-Augmented Generation for documentation and tech radar
- **`github_agent`**: GitHub operations and repository management
- **`azure_agent`**: Azure cloud services and operations
- **`caas_agent`**: Container-as-a-Service operations
- **`doc_agent`**: Document generation and management
- **`deep_agent`**: Complex research and analysis tasks

### Development Workflow

1. **Make changes** to your agent code in the `app/` directory
2. **Save your changes** - LangGraph Server will automatically reload
3. **Test in Studio** - Use the interactive interface to debug
4. **Iterate** - Edit state, rerun from checkpoints, and refine your agents

### Agent Reasoning Configuration

Control agent verbosity and reasoning display:

```sh
# Set to 'true' for more direct responses without reasoning steps
DISABLE_REASONING=false

# Debug output control (per agent)
SUPERVISOR_DEBUG=true
RAG_AGENT_DEBUG=true
# ... other agent debug flags
```

### Alternative: Running the FastAPI Server

If you prefer the traditional FastAPI interface:

```sh
poetry run start
# or 
python app/server.py
```

### Running a Development Tunnel

For external access, you can use a tunnel service. Update the port to match your LangGraph server (`8123`):

```sh
# Example with your preferred tunnel service
your-tunnel-tool --port 8123
```


## Documentation 
- [CopilotKit Docs](https://docs.copilotkit.ai/coagents)
- [LangGraph Platform Docs](https://langchain-ai.github.io/langgraph/cloud/deployment/cloud/)
- [Model Context Protocol (MCP) Docs](https://github.com/langchain-ai/langgraph/tree/main/examples/mcp)

## License
Distributed under the MIT License. See LICENSE for more info.
