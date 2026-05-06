# Testing Documentation

This document describes the test suite for the Navigator Backend application.

## Overview

The test suite includes 10+ basic health check test cases using `pytest` to ensure the FastAPI application works correctly.

## Test Categories

### Health Check Tests (TestHealthCheckEndpoints)
1. **test_health_endpoint_returns_ok** - Verifies health endpoint returns OK status
2. **test_health_endpoint_content_type** - Verifies correct content type in response
3. **test_health_endpoint_async** - Tests health endpoint with async client
4. **test_health_endpoint_multiple_requests** - Tests multiple consecutive requests
5. **test_root_path_not_found** - Verifies root path returns 404 when not defined
6. **test_invalid_endpoint_not_found** - Verifies invalid endpoints return 404
7. **test_health_endpoint_head_method** - Tests HEAD request handling
8. **test_health_endpoint_options_method** - Tests OPTIONS request handling
9. **test_health_endpoint_post_method_not_allowed** - Verifies POST is rejected
10. **test_copilotkit_endpoint_exists** - Tests basic app functionality

### Application Configuration Tests (TestApplicationConfiguration)
- **test_app_instance_exists** - Verifies FastAPI app creation
- **test_health_route_registered** - Verifies health route registration
- **test_port_configuration_from_env** - Tests environment variable configuration
- **test_default_port_configuration** - Tests default port configuration
- **test_fastapi_app_type** - Verifies app is FastAPI instance
- **test_health_endpoint_in_openapi_schema** - Verifies OpenAPI schema inclusion

## Dependencies

### Poetry Dependencies (pyproject.toml)
```toml
[tool.poetry.group.test.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.24.0"
httpx = "^0.27.0"
pytest-mock = "^3.12.0"
pytest-cov = "^4.0.0"
pytest-xdist = "^3.5.0"
faker = "^22.0.0"
factory-boy = "^3.3.0"
```

### Requirements File (unit-tests-prereqs.txt)
```
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
pytest-mock>=3.12.0
pytest-cov>=4.0.0
pytest-xdist>=3.5.0
faker>=22.0.0
factory-boy>=3.3.0
```

## Running Tests

### Using Poetry (Recommended)
```bash
# Install test dependencies
poetry install --with test

# Run health check tests only
poetry run python -m pytest tests/test_health_checks.py -v

# Run all tests
poetry run python -m pytest tests/ -v

# Run with coverage
poetry run python -m pytest tests/ --cov=app --cov-report=html
```

### Using Test Runner Script
```bash
# Run health check tests
python run_tests.py health

# Run all tests
python run_tests.py all

# Run with coverage report
python run_tests.py coverage

# Show help
python run_tests.py help
```

### Using pip
```bash
# Install dependencies
pip install -r unit-tests-prereqs.txt

# Run tests
python -m pytest tests/test_health_checks.py -v
```

## Test Configuration

### pytest.ini
The test configuration includes:
- Test discovery patterns
- Coverage settings (70% minimum)
- Async test support
- Warning filters
- Custom markers for test categorization

### conftest.py
Provides shared fixtures for:
- Test environment setup
- Environment variable mocking
- Session-wide configuration

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures and configuration
└── test_health_checks.py       # Main health check test suite
```

## Mocking Strategy

The tests use comprehensive mocking to avoid dependency issues:
- Mock LangChain components (`langchain_ollama`, `langchain_openai`, etc.)
- Mock CopilotKit components
- Mock agent graphs
- Isolated test FastAPI app creation

## Coverage

Run tests with coverage to ensure adequate test coverage:
```bash
poetry run python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
```

Coverage reports are generated in `htmlcov/index.html`.

## Continuous Integration

The test suite is designed to work in CI/CD environments with:
- Dependency isolation through mocking
- Environment variable configuration
- Clear pass/fail indicators
- Detailed test output

## Adding New Tests

1. Add new test functions to `test_health_checks.py` or create new test files
2. Follow the naming convention: `test_*.py` for files, `test_*` for functions
3. Use appropriate pytest markers (`@pytest.mark.asyncio` for async tests)
4. Mock external dependencies appropriately
5. Include docstrings explaining what each test verifies
