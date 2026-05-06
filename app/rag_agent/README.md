# RAG Agent Documentation

## Overview

The RAG (Retrieval-Augmented Generation) Agent is a specialized agent within the autopilot-agents system that performs agentic RAG against an existing vector database. It uses LlamaIndex libraries for RAG retrieval and embedding to query tech radar, technology standards, tools, frameworks, and project information.

## Features

- **Vector Database Integration**: Connects to PostgreSQL with pgvector extension
- **LlamaIndex Integration**: Uses LlamaIndex for embeddings and vector search
- **Tech Radar Queries**: Specialized in querying tech radar documentation
- **Project Documentation**: Access to Project Yoda and Autopilot documentation
- **Flexible LLM Support**: Works with both OpenAI and Ollama models
- **Source Attribution**: Provides source references with relevance scores

## Architecture

The RAG agent consists of several key components:

1. **Vector Store Management**: PostgreSQL with pgvector for vector storage
2. **Embedding Models**: Ollama-based embeddings (mxbai-embed-large by default)
3. **LLM Integration**: Support for OpenAI and Ollama language models
4. **Query Processing**: LlamaIndex query engine for retrieval and generation
5. **Tool Integration**: LangChain tool system for agentic behavior

## Configuration

### Environment Variables

The RAG agent requires the following environment variables:

#### Database Configuration
```bash
DB_HOST=localhost          # PostgreSQL host
DB_PORT=5432              # PostgreSQL port
DB_NAME=vector_db         # Database name
DB_USER=username          # Database user
DB_PASSWORD=password      # Database password
VECTOR_TABLE_NAME=document_embeddings      # Vector table name
EMBEDDING_DIM=1024           # Embedding dimensions
```

#### LLM Configuration
```bash
LLM_PROVIDER=openai          # "openai" or "ollama"
OPENAI_MODEL=gpt-4o          # OpenAI model name
OPENAI_API_KEY=your_key      # OpenAI API key
OPENAI_BASE_URL=https://api.openai.com/v1  # OpenAI base URL
OLLAMA_MODEL=qwen3           # Ollama model name
OLLAMA_BASE_URL=http://localhost:11434     # Ollama base URL
MODEL_TEMPERATURE=0          # Model temperature
```

#### Embedding Configuration
```bash
EMBEDDING_MODEL=mxbai-embed-large  # Embedding model name
CHUNK_SIZE=512                 # Text chunk size
CHUNK_OVERLAP=50              # Chunk overlap
```

#### Debug Configuration
```bash
RAG_AGENT_DEBUG=false        # Enable debug output
```

## Usage

### Integration with Supervisor Agent

The RAG agent is automatically integrated with the supervisor agent and will be invoked when users ask questions about:

- Tech radar and technology standards
- Tools and frameworks
- Project Yoda documentation
- Autopilot project information
- Technology best practices

### Direct Usage

You can also use the RAG agent directly:

```python
from app.rag_agent.agent import graph, AgentState
from langchain_core.messages import HumanMessage

# Create initial state
initial_state = AgentState()
initial_state["messages"] = [HumanMessage(content="What is the tech radar?")]

# Invoke the graph
config = {"configurable": {"thread_id": "example"}}
result = await graph.ainvoke(initial_state, config)

# Get the response
response = result["messages"][-1].content
print(response)
```

### Search Tool

The RAG agent provides a `search_documentation` tool that can be used independently:

```python
from app.rag_agent.agent import search_documentation, RAGQuery

# Create a search query
query = RAGQuery(
    query="What are the recommended web frameworks?",
    top_k=5,
    repository_filter=None  # Optional filter
)

# Execute search
results = search_documentation.invoke({"query": query})

# Process results
print(f"Query: {results['query']}")
print(f"Response: {results['response']}")
print(f"Sources found: {len(results['source_nodes'])}")
```

## Database Setup

The RAG agent expects a PostgreSQL database with pgvector extension and pre-populated vector data. 

### Prerequisites

1. PostgreSQL with pgvector extension
2. Vector database populated with tech radar and project documentation
3. Appropriate database permissions

### Vector Database Schema

The agent expects the following table structure:

```sql
CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY,
    text TEXT,
    metadata JSONB,
    embedding VECTOR(1024)  -- Adjust dimension as needed
);

-- Create HNSW index for fast similarity search
CREATE INDEX ON document_embeddings USING hnsw (embedding vector_cosine_ops);
```

## Error Handling

The RAG agent includes comprehensive error handling:

1. **LlamaIndex Availability**: Gracefully handles missing LlamaIndex dependencies
2. **Database Connectivity**: Provides meaningful error messages for connection issues
3. **Query Failures**: Returns structured error responses for failed queries
4. **Missing Data**: Handles cases where no relevant documents are found

## Development

### Running Tests

```bash
cd /path/to/autopilot-agents
python test_rag_integration.py
```

### Demo Script

```bash
cd /path/to/autopilot-agents
python -m app.rag_agent.demo
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export RAG_AGENT_DEBUG=true
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure LlamaIndex dependencies are installed
2. **Database Connection**: Verify PostgreSQL connection parameters
3. **Empty Results**: Check if vector database contains relevant data
4. **Performance Issues**: Adjust chunk size and top_k parameters

### Installation

If you encounter import errors, install the required dependencies:

```bash
pip install llama-index llama-index-llms-openai llama-index-llms-ollama llama-index-embeddings-ollama llama-index-vector-stores-postgres psycopg2-binary sqlalchemy
```

## Integration Points

### Supervisor Agent

The RAG agent is integrated into the supervisor agent routing system:

```python
# Routing guidelines in supervisor agent:
# - Tech radar, technology standards → rag_agent
# - Tools and frameworks → rag_agent  
# - Project Yoda, Autopilot → rag_agent
# - Weather, general conversation → sample_agent
# - Data queries, calculations → mcp_agent
```

### Response Format

The RAG agent returns responses in markdown format with source attribution:

```markdown
## Answer

Based on the tech radar documentation, here are the recommended frameworks...

### Sources
1. **tech-radar.md** (Score: 0.892)
2. **framework-standards.md** (Score: 0.845)
3. **best-practices.md** (Score: 0.798)
```

## Future Enhancements

Potential improvements for the RAG agent:

1. **Multi-modal Support**: Support for images and other file types
2. **Advanced Filtering**: More sophisticated repository and metadata filtering
3. **Caching**: Result caching for improved performance
4. **Analytics**: Query analytics and usage tracking
5. **Real-time Updates**: Automatic vector database updates
