"""
Test suite for navigator-backend FastAPI application.

This test suite includes:
- Unit tests for individual components
- Integration tests for API endpoints  
- Performance and load tests
- Agent-specific tests for sample agent and MCP agent

Test Categories:
- Unit tests: Fast, isolated tests for individual functions/classes
- Integration tests: Tests that verify component interactions
- Slow tests: Performance, load, and stress tests

To run tests:
- All tests: pytest
- Unit tests only: pytest -m unit
- Integration tests only: pytest -m integration
- Exclude slow tests: pytest -m "not slow"
- With coverage: pytest --cov=.

Test Fixtures:
- client: FastAPI test client
- mock_openai: Mocked OpenAI API
- mock_tavily: Mocked Tavily search API
- Various agent state fixtures
"""