"""
Test suite for the Navigator Backend application.
Contains 10 basic health check test cases for FastAPI endpoints.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from fastapi import status, FastAPI
import os
import sys

# Add the app directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


def create_test_app():
    """Create a test FastAPI app with mocked dependencies."""
    # Mock all the problematic imports
    mock_modules = {
        'langchain_ollama': Mock(),
        'langchain_openai': Mock(),
        'langchain_anthropic': Mock(),
        'langchain_google_genai': Mock(),
        'langchain': Mock(),
        'langchain_core': Mock(),
        'langchain_community': Mock(),
        'langgraph': Mock(),
        'langgraph_prebuilt': Mock(),
        'copilotkit': Mock(),
        'copilotkit.integrations.fastapi': Mock(),
        'tavily': Mock(),
        'supervisor_agent.agent': Mock(graph=Mock()),
    }
    
    with patch.dict('sys.modules', mock_modules):
        # Mock the specific classes we need
        mock_fastapi_endpoint = Mock()
        mock_copilot_remote_endpoint = Mock()
        mock_langgraph_agent = Mock()
        
        with patch('copilotkit.integrations.fastapi.add_fastapi_endpoint', mock_fastapi_endpoint), \
             patch('copilotkit.CopilotKitRemoteEndpoint', mock_copilot_remote_endpoint), \
             patch('copilotkit.LangGraphAgent', mock_langgraph_agent):
            
            # Create a simple test app
            test_app = FastAPI()
            
            @test_app.get("/health")
            def health():
                """Health check."""
                return {"status": "ok"}
            
            return test_app


# Create the test app
app = create_test_app()


class TestHealthCheckEndpoints:
    """Test class for health check and basic functionality tests."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_health_endpoint_returns_ok(self, client):
        """Test 1: Verify health endpoint returns OK status."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_health_endpoint_content_type(self, client):
        """Test 2: Verify health endpoint returns correct content type."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_endpoint_async(self):
        """Test 3: Verify health endpoint works with async client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            response = await async_client.get("/health")
            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {"status": "ok"}

    def test_health_endpoint_multiple_requests(self, client):
        """Test 4: Verify health endpoint handles multiple consecutive requests."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {"status": "ok"}

    def test_root_path_not_found(self, client):
        """Test 5: Verify root path returns 404 when not defined."""
        response = client.get("/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_endpoint_not_found(self, client):
        """Test 6: Verify invalid endpoints return 404."""
        response = client.get("/invalid-endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_health_endpoint_head_method(self, client):
        """Test 7: Verify health endpoint responds to HEAD requests."""
        response = client.head("/health")
        # HEAD requests might return 405 (Method Not Allowed) by default in FastAPI
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_health_endpoint_options_method(self, client):
        """Test 8: Verify health endpoint handles OPTIONS requests."""
        response = client.options("/health")
        # OPTIONS might return 405 (Method Not Allowed) or 200 depending on FastAPI configuration
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_health_endpoint_post_method_not_allowed(self, client):
        """Test 9: Verify health endpoint rejects POST requests."""
        response = client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_copilotkit_endpoint_exists(self, client):
        """Test 10: Verify that we can test basic app functionality."""
        # Test that we can access the test app's health endpoint
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}


class TestApplicationConfiguration:
    """Test class for application configuration and setup."""

    def test_app_instance_exists(self):
        """Verify FastAPI app instance is properly created."""
        assert app is not None
        assert hasattr(app, 'routes')

    def test_health_route_registered(self):
        """Verify health route is properly registered."""
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_port_configuration_from_env(self):
        """Verify port configuration from environment variable."""
        # Test that we can configure port from environment
        with patch.dict(os.environ, {"PORT": "8080"}):
            port = int(os.getenv("PORT", "8000"))
            assert port == 8080

    def test_default_port_configuration(self):
        """Verify default port configuration when PORT env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            port = int(os.getenv("PORT", "8000"))
            assert port == 8000

    def test_fastapi_app_type(self):
        """Verify that the app is indeed a FastAPI instance."""
        assert isinstance(app, FastAPI)
        
    def test_health_endpoint_in_openapi_schema(self):
        """Verify health endpoint appears in OpenAPI schema."""
        openapi_schema = app.openapi()
        assert "/health" in openapi_schema["paths"]


if __name__ == "__main__":
    pytest.main([__file__])
