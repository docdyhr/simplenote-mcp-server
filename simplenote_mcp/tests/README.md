# Simplenote MCP Server Tests

This directory contains tests for the Simplenote MCP Server. These tests ensure that the server works correctly and help prevent regressions when making changes.

## Test Structure

The test suite is organized into the following categories:

- **Unit Tests**: Tests for individual components without external dependencies
- **Integration Tests**: Tests that interact with the Simplenote API
- **Test Utilities**: Scripts to help with testing

## Running Tests

### Prerequisites

1. Set up your environment variables:
   ```bash
   export SIMPLENOTE_EMAIL="your-email@example.com"
   export SIMPLENOTE_PASSWORD="your-password"
   ```

2. Install test dependencies:
   ```bash
   pip install pytest pytest-asyncio pytest-cov
   ```

### Using the Test Runner

The easiest way to run tests is using the `run_tests.py` script:

```bash
python simplenote_mcp/tests/run_tests.py
```

This will automatically discover and run all tests.

#### Options

- `--mode`: Choose test execution mode (`pytest` or `direct`)
- `--category`: Test category to run (`unit`, `integration`, or `all`)
- `--tests`: Specify individual test files to run
- `--verbose` or `-v`: Enable verbose output
- `--coverage`: Generate test coverage report
- `--junit`: Generate JUnit XML report
- `--no-env-check`: Skip environment variable check

Example:
```bash
python simplenote_mcp/tests/run_tests.py --mode=pytest --category=unit --coverage
```

### Using pytest Directly

You can also use pytest directly:

```bash
cd simplenote-mcp-server
python -m pytest simplenote_mcp/tests/
```

For more options, see [pytest documentation](https://docs.pytest.org/en/stable/usage.html).

## Writing Tests

Tests use pytest-style assertions for more descriptive error messages. When writing new tests:

1. Use descriptive test names (`test_function_does_something`)
2. Include helpful assertion messages
3. Group related tests into classes when appropriate
4. Use fixtures from `conftest.py` to reduce code duplication
5. Clean up any resources created during tests

### Example Test

```python
@pytest.mark.asyncio
async def test_note_operations():
    """Test basic note operations."""
    # Create test note
    content = "Test note content"
    note = {"content": content, "tags": ["test"]}
    
    # Test assertions
    result, status = client.add_note(note)
    assert status == 0, f"Failed to create note: status {status}"
    assert "key" in result, "Created note should have a key"
    
    # Clean up
    client.trash_note(result["key"])
```

## Continuous Integration

Tests are automatically run in the CI pipeline for all pull requests and commits to the main branch. Make sure your tests pass locally before submitting changes.

## Test Coverage

To generate a test coverage report:

```bash
python simplenote_mcp/tests/run_tests.py --coverage
```

This creates an HTML coverage report in the `htmlcov/` directory.
