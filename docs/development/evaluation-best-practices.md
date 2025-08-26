# Evaluation Best Practices Guide

This guide provides comprehensive best practices for writing, running, and maintaining evaluations for the Simplenote MCP Server using the mcp-evals framework.

## Table of Contents

- [Overview](#overview)
- [Evaluation Framework](#evaluation-framework)
- [Writing Effective Evaluations](#writing-effective-evaluations)
- [Evaluation Types and Categories](#evaluation-types-and-categories)
- [Best Practices](#best-practices)
- [Running Evaluations](#running-evaluations)
- [Troubleshooting](#troubleshooting)
- [Contributing New Evaluations](#contributing-new-evaluations)

## Overview

The Simplenote MCP Server uses a comprehensive evaluation framework based on `mcp-evals` to ensure reliability, performance, and correctness of the MCP implementation. Evaluations are automated tests that use real Language Models to interact with the server, providing realistic validation of functionality.

### Why Evaluations Matter

- **Real-world validation**: Use actual LLMs to test server behavior
- **Regression detection**: Catch breaking changes before deployment  
- **Performance monitoring**: Track response times and resource usage
- **User experience validation**: Ensure tools work as users expect
- **Documentation verification**: Validate that examples actually work

## Evaluation Framework

### Architecture

```
mcp-evals Framework
├── YAML Configuration Files (evals/*.yaml)
├── TypeScript Wrapper (mcp-server-wrapper.ts)
├── Test Execution Engine (mcp-eval CLI)
└── Result Analysis & Reporting
```

### Evaluation Suites

The project includes three evaluation suites:

1. **Smoke Tests** (`smoke-tests.yaml`) - Quick validation (2-3 minutes)
2. **Basic Tests** (`simplenote-evals.yaml`) - Core functionality (5-10 minutes)
3. **Comprehensive Tests** (`comprehensive-evals.yaml`) - Full validation (15-30 minutes)

### Configuration Structure

Each evaluation YAML file follows this structure:

```yaml
model:
  provider: openai
  name: gpt-4o
  # Uses environment variables for authentication

evals:
  - name: evaluation_name
    description: Human-readable description
    prompt: |
      Multi-line prompt describing what the LLM should do.
      Should include specific steps and expected tool usage.
    expected_result: |
      Description of what constitutes a successful result.
      Include expected JSON structure or behavior patterns.
```

## Writing Effective Evaluations

### 1. Clear and Specific Prompts

**Good Example:**
```yaml
prompt: |
  Perform a complete note lifecycle test:
  1. Create a new note with content "Test Note Content"
  2. Retrieve the created note and verify its content
  3. Update the note by appending "\n\nUpdated content"
  4. Delete the created note
  Each step should succeed and the note should be properly cleaned up.
```

**Bad Example:**
```yaml
prompt: |
  Test note operations and make sure they work correctly.
```

### 2. Comprehensive Expected Results

**Good Example:**
```yaml
expected_result: |
  Should complete all operations successfully:
  - create_note returns: {"success": true, "note_id": "<string>", "message": "Note created successfully"}
  - get_note returns the full content with proper formatting
  - update_note preserves existing content and adds new content
  - delete_note removes the note successfully
```

**Bad Example:**
```yaml
expected_result: "Should work"
```

### 3. Include Cleanup Steps

Always include cleanup in your evaluation prompts:

```yaml
prompt: |
  1. Create test data
  2. Perform operations
  3. Verify results
  4. Clean up all test data (delete created notes, etc.)
```

### 4. Test Both Success and Failure Scenarios

```yaml
- name: error_handling_invalid_note_id
  description: Test handling of non-existent note IDs
  prompt: |
    Try to retrieve a note with a clearly invalid ID "non-existent-note-12345-invalid".
    The system should handle this gracefully with appropriate error messaging.
  expected_result: |
    Should return an error response with structure:
    {
      "success": false,
      "error": "Note not found" or similar,
      "error_type": "ResourceNotFoundError" or similar
    }
```

## Evaluation Types and Categories

### 1. Core Functionality Tests

Test basic CRUD operations and essential features:

```yaml
- name: note_lifecycle_basic
  description: Test complete note lifecycle
  # Tests: create, read, update, delete
  
- name: tag_operations_comprehensive  
  description: Test all tag operations
  # Tests: add_tags, remove_tags, replace_tags
```

### 2. Realistic User Workflow Tests

Simulate actual user scenarios:

```yaml
- name: workflow_meeting_notes
  description: Simulate real meeting notes workflow
  # Simulates: creating meeting notes, updating during meeting, tagging, archiving

- name: workflow_research_collection
  description: Simulate research note collection and organization
  # Simulates: multiple related notes, consistent tagging, organization
```

### 3. Performance and Scale Tests

Test system behavior under load:

```yaml
- name: performance_concurrent_operations
  description: Test system under concurrent load
  # Tests: multiple simultaneous operations, race conditions

- name: performance_large_content_handling
  description: Test handling of large note content
  # Tests: large content (>10KB), response times, memory usage
```

### 4. Advanced Search and Query Tests

Test search functionality comprehensively:

```yaml
- name: search_advanced_queries
  description: Test complex search queries and filters
  # Tests: tag filtering, text search, combined filters

- name: search_edge_cases_and_special_characters
  description: Test search with special characters and edge cases
  # Tests: Unicode, special characters, empty queries
```

### 5. Error Handling and Edge Case Tests

Validate error scenarios and boundary conditions:

```yaml
- name: error_comprehensive_validation
  description: Test all parameter validation scenarios
  # Tests: missing parameters, invalid values, malformed requests

- name: edge_cases_special_content
  description: Test handling of special content types
  # Tests: whitespace, very long lines, Unicode, code snippets
```

## Best Practices

### Writing Prompts

1. **Be Specific**: Include exact content, parameters, and expected sequences
2. **Use Realistic Data**: Mirror real user scenarios and content
3. **Include Verification**: Ask the LLM to verify results at each step
4. **Plan for Cleanup**: Always clean up test data
5. **Handle Failures**: Include instructions for error scenarios

### Expected Results

1. **Define Success Clearly**: Specify exact JSON structures or behavior patterns
2. **Include Response Times**: Set reasonable performance expectations
3. **Cover Error Cases**: Define expected error responses
4. **Be Measurable**: Use objective criteria that can be programmatically verified

### Test Data Management

1. **Use Unique Identifiers**: Include timestamps or UUIDs in test content
2. **Avoid Conflicts**: Use prefixes like "Test -" or "Eval -" for test notes
3. **Clean Up Thoroughly**: Remove all test data, even after failures
4. **Use Realistic Content**: Mirror actual user data patterns

### Performance Considerations

1. **Set Reasonable Timeouts**: Account for network latency and processing time
2. **Monitor Resource Usage**: Include memory and CPU impact in expectations
3. **Test Concurrency**: Verify behavior under simultaneous operations
4. **Scale Testing**: Test with varying amounts of data

## Running Evaluations

### Quick Start

```bash
# Install dependencies
npm install

# Validate evaluation files
npm run validate:evals

# Run smoke tests (fastest)
npm run eval:smoke

# Run basic functionality tests  
npm run eval:basic

# Run comprehensive tests (thorough)
npm run eval:comprehensive

# Run all evaluation suites
npm run eval:all
```

### Environment Setup

```bash
# Required environment variables
export OPENAI_API_KEY="your-api-key-here"
export SIMPLENOTE_EMAIL="your-test-account@example.com"
export SIMPLENOTE_PASSWORD="your-test-password"

# Optional: Use offline mode for development
export SIMPLENOTE_OFFLINE_MODE="true"
```

### Development Workflow

```bash
# Test your changes with smoke tests first
npm run eval:smoke

# If smoke tests pass, run basic tests
npm run eval:basic

# For major changes, run comprehensive tests
npm run eval:comprehensive

# Before releases, always run all tests
npm run eval:all
```

### Continuous Integration

The evaluation suites are integrated into the CI/CD pipeline:

- **Pull Requests**: Run smoke tests for quick validation
- **Main Branch**: Run basic tests for regression detection
- **Releases**: Run comprehensive tests for full validation

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

```bash
# Check environment variables
echo $SIMPLENOTE_EMAIL
echo $SIMPLENOTE_PASSWORD

# Test authentication separately
python -c "from simplenote_mcp.server.server import get_simplenote_client; client = get_simplenote_client(); print('Auth OK')"
```

#### 2. Test Data Cleanup Issues

- Use unique test data identifiers
- Implement robust cleanup logic
- Check for leftover test notes manually:

```bash
# Search for test notes
python -c "
from simplenote_mcp.server.server import get_simplenote_client
client = get_simplenote_client()
notes = client.get_note_list()
test_notes = [n for n in notes if 'test' in n.get('content', '').lower()]
print(f'Found {len(test_notes)} test notes')
"
```

#### 3. Performance Issues

- Check system resources during tests
- Monitor network latency to Simplenote API
- Use offline mode for development testing
- Reduce test data size for faster iterations

#### 4. LLM Response Variability

- Make prompts more specific and deterministic
- Include explicit verification steps
- Use consistent expected result patterns
- Consider using temperature=0 for more deterministic responses

### Debugging Failed Evaluations

1. **Check the full evaluation output**: Look for specific error messages
2. **Run individual evaluations**: Isolate failing tests
3. **Validate YAML syntax**: Ensure proper formatting
4. **Test server manually**: Use tools directly to verify behavior
5. **Check rate limits**: Ensure API quotas aren't exceeded

## Contributing New Evaluations

### 1. Identify the Need

- **Missing functionality**: New features need corresponding tests
- **Bug reports**: Create evaluations to reproduce and prevent regressions  
- **User scenarios**: Common user workflows should be tested
- **Edge cases**: Unusual but valid scenarios should be covered

### 2. Choose the Right Suite

- **Smoke tests**: Critical functionality, must be fast (<3 minutes)
- **Basic tests**: Common user scenarios, moderate runtime (5-10 minutes)
- **Comprehensive tests**: Edge cases, performance tests, extensive scenarios

### 3. Follow the Template

```yaml
- name: descriptive_test_name
  description: Clear explanation of what this test validates
  prompt: |
    Step-by-step instructions for the LLM:
    1. Setup phase (create test data)
    2. Action phase (perform operations)  
    3. Verification phase (check results)
    4. Cleanup phase (remove test data)
    
    Include specific content, parameters, and expected sequences.
  expected_result: |
    Detailed description of successful outcome:
    - Specific JSON structures expected
    - Performance characteristics
    - Error handling behavior
    - Any other measurable criteria
```

### 4. Test Your Evaluation

```bash
# Create a temporary test file
echo "model:
  provider: openai
  name: gpt-4o
evals:
  - name: your_new_test
    # ... your test definition
" > test-eval.yaml

# Run your specific evaluation
npx mcp-eval test-eval.yaml mcp-server-wrapper.ts

# Clean up
rm test-eval.yaml
```

### 5. Add Documentation

When contributing new evaluations:

1. **Update this guide**: Add your evaluation type to the appropriate section
2. **Comment your YAML**: Include inline comments for complex logic
3. **Update README**: If adding new evaluation categories
4. **Document edge cases**: Explain unusual scenarios being tested

### 6. Consider Maintainability

- **Keep prompts readable**: Use clear, maintainable language
- **Avoid hardcoded values**: Use dynamic test data where possible
- **Design for stability**: Tests should be reliable and repeatable
- **Plan for updates**: Consider how tests might need to evolve

## Advanced Topics

### Custom Model Configurations

You can customize the LLM model used for specific evaluations:

```yaml
model:
  provider: openai
  name: gpt-4o-mini  # Cost-effective for many tests
  # OR
  name: gpt-4o       # More capable for complex tests
```

### Environment-Specific Testing

```yaml
# Different configurations for different environments
- name: production_simulation
  description: Test with production-like constraints
  # Include rate limiting, larger datasets, etc.

- name: development_rapid_iteration  
  description: Fast tests for development cycle
  # Use smaller datasets, skip expensive operations
```

### Performance Benchmarking

```yaml
- name: performance_baseline
  description: Establish performance baselines
  prompt: |
    Perform standardized operations and measure response times:
    1. Create 10 notes (measure total time)
    2. Search for notes (measure query time)
    3. Update notes (measure update time)
    4. Clean up (measure deletion time)
    Report all timing information.
  expected_result: |
    Should complete within performance targets:
    - Creation: <30 seconds total
    - Search: <5 seconds per query  
    - Updates: <20 seconds total
    - Deletion: <15 seconds total
```

## Conclusion

Effective evaluations are crucial for maintaining a reliable MCP server. They provide confidence in changes, catch regressions early, and ensure the server meets user expectations.

Key principles:
- **Write realistic scenarios** that mirror actual usage
- **Be specific and measurable** in prompts and expected results
- **Include proper cleanup** to avoid test interference
- **Cover both success and failure cases** for comprehensive validation
- **Maintain tests as the codebase evolves** to prevent staleness

For questions or suggestions about evaluations, please refer to the [Contributing Guide](../contributing.md) or open an issue on the project repository.

## References

- [mcp-evals Documentation](https://github.com/modelcontextprotocol/mcp-evals)
- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Simplenote MCP Server README](../../README.md)
- [Development Setup Guide](../installation.md)
