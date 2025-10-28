# Testing Guide - Content Creation Agent

**Last Updated**: January 23, 2025
**Test Framework**: pytest + pytest-asyncio
**Coverage Target**: 70%

---

## Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated unit tests
│   ├── test_cost_calculator.py
│   └── test_database_retry.py
├── integration/             # Service integration tests (future)
├── e2e/                     # End-to-end workflow tests
│   ├── test_e2e_workflow.py
│   ├── test_supervisor_chat.py
│   └── test_video_response_handling.py
└── test_supervisor_knowledge.py
```

---

## Running Tests

### Run All Tests

```bash
cd ContentCreationAgent
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# Slow tests (>5s)
pytest -m slow
```

### Run with Coverage Report

```bash
pytest --cov=backend --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Run Specific Test File

```bash
pytest backend/tests/unit/test_cost_calculator.py
```

---

## Test Fixtures

### Available Fixtures (from conftest.py)

- `mock_settings`: Mock application settings
- `mock_mem0_client`: Mock Mem0 client
- `mock_mcp_client`: Mock MCP client
- `mock_workflow_state`: Sample workflow state
- `mock_database_session`: Mock database session

### Using Fixtures

```python
def test_something(mock_settings, mock_mem0_client):
    # Use fixtures in test
    result = some_function(mock_settings, mock_mem0_client)
    assert result == expected
```

---

## Test Categories

### Unit Tests (`unit/`)

**Speed**: Fast (<1s each)
**Dependencies**: None
**Mocking**: Heavy

**Example**: `test_cost_calculator.py`

- Tests cost calculation logic
- No external services required
- Fast and isolated

### Integration Tests (`integration/`)

**Speed**: Medium (1-5s each)
**Dependencies**: Services available
**Mocking**: Minimal

**Example**: Database connection tests

- Requires actual database
- Tests real interactions
- More realistic scenarios

### End-to-End Tests (`e2e/`)

**Speed**: Slow (>5s each)
**Dependencies**: All services running
**Mocking**: None

**Example**: `test_e2e_workflow.py`

- Full workflow execution
- Real API calls
- Production-like environment

---

## Test Coverage

### Current Coverage

- Unit Tests: `test_cost_calculator.py` (completed)
- Unit Tests: `test_database_retry.py` (completed)
- E2E Tests: `test_e2e_workflow.py` (existing)
- E2E Tests: `test_supervisor_chat.py` (existing)
- E2E Tests: `test_video_response_handling.py` (existing)

### Target Coverage Areas

- [x] Cost calculation utilities
- [x] Database retry logic
- [x] Workflow execution
- [x] Agent interactions
- [x] Video response handling
- [ ] API endpoint tests
- [ ] Memory integration tests
- [ ] MCP integration tests

---

## Writing New Tests

### Unit Test Template

```python
"""
Test Module Name

Description of what is being tested.
"""

import pytest


class TestClassName:
    """Test class description."""

    def test_specific_functionality(self):
        """Test specific behavior."""
        # Arrange
        expected = "result"

        # Act
        actual = function_to_test()

        # Assert
        assert actual == expected
```

### Async Test Template

```python
@pytest.mark.asyncio
class TestAsyncFunction:
    """Test async functionality."""

    async def test_async_behavior(self):
        """Test async behavior."""
        result = await async_function()
        assert result is not None
```

### Integration Test Template

```python
@pytest.mark.integration
@pytest.mark.requires_db
class TestDatabaseIntegration:
    """Test database integration."""

    async def test_database_operation(self, mock_database_session):
        """Test database operations."""
        # Test database operations
        pass
```

---

## Mocking Best Practices

### Mock External Services

Always mock:

- API calls (OpenAI, Anthropic, etc.)
- Database sessions (in unit tests)
- File I/O operations
- Network requests

### Example: Mocking API Calls

```python
@pytest.fixture
def mock_openai_client():
    client = AsyncMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Response"))]
    )
    return client

def test_api_call(mock_openai_client):
    result = call_api(mock_openai_client)
    assert result == "Response"
```

---

## Continuous Integration

### Pre-commit Checks

```bash
# Run tests
pytest

# Check coverage
pytest --cov=backend --cov-report=term --cov-fail-under=70

# Lint
ruff check backend/

# Format
black --check backend/
```

### CI/CD Pipeline

```yaml
# Example GitHub Actions
- name: Run Tests
  run: pytest --cov=backend --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

---

## Test Data Management

### Test Data Directory

```
tests/
├── fixtures/
│   ├── sample_workflow_state.json
│   ├── sample_agent_response.json
│   └── sample_video_metadata.json
└── mocks/
    ├── mock_openai_response.json
    └── mock_anthropic_response.json
```

### Loading Test Data

```python
import json
from pathlib import Path

@pytest.fixture
def sample_workflow_state():
    """Load sample workflow state from file."""
    file_path = Path(__file__).parent / "fixtures" / "sample_workflow_state.json"
    with open(file_path) as f:
        return json.load(f)
```

---

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `backend/` is in PYTHONPATH
2. **Async Test Errors**: Use `pytest.mark.asyncio` marker
3. **Database Errors**: Use `@pytest.mark.requires_db` and setup test DB
4. **Mock Issues**: Check fixture is being used correctly

### Debug Mode

```bash
# Verbose output
pytest -v

# Extra verbose
pytest -vv

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

---

## Test Maintenance

### Keep Tests Updated

- Update tests when code changes
- Remove obsolete tests
- Add tests for new features
- Maintain high coverage (70%+)

### Test Review Checklist

- [ ] Tests are fast and isolated
- [ ] Tests use appropriate mocking
- [ ] Tests have clear descriptions
- [ ] Tests cover edge cases
- [ ] Tests maintain good coverage

---

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Mock Object](https://docs.python.org/3/library/unittest.mock.html)
