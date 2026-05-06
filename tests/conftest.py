"""
Pytest configuration and shared fixtures for the Navigator Backend test suite.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add the app directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment before running tests."""
    # Set test environment variables
    os.environ.setdefault("TESTING", "true")
    yield
    # Cleanup after tests
    os.environ.pop("TESTING", None)


@pytest.fixture
def mock_env_vars():
    """Provide a fixture for mocking environment variables."""
    def _mock_env(**kwargs):
        return patch.dict(os.environ, kwargs)
    return _mock_env
