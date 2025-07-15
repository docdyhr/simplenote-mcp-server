# MCP Evaluations for Simplenote MCP Server ✅

This directory contains evaluation configurations for testing the Simplenote MCP Server using [mcp-evals](https://github.com/mclenhard/mcp-evals).

**Status**: ✅ **UPDATED & IMPROVED** - All evaluations redesigned with realistic scenarios and proper test lifecycle!

## 📁 Evaluation Files

- **`smoke-tests.yaml`** - Quick smoke tests for basic functionality validation (< 2 min) ✅ **OPTIMIZED**
- **`simplenote-evals.yaml`** - Standard evaluation suite with realistic workflows ✅ **REDESIGNED**
- **`comprehensive-evals.yaml`** - Comprehensive evaluation suite for thorough testing ✅ **ENHANCED**
- **`mcp-server-wrapper.ts`** - TypeScript wrapper that bridges Python server with Node.js mcp-evals

## 🎯 Recent Improvements (July 15, 2025)

### ✅ Critical Issues Fixed
- **Eliminated hard-coded note IDs** - All tests now use dynamic note creation and proper cleanup
- **Tool validation** - Verified all 8 implemented tools are properly tested
- **Realistic scenarios** - Replaced artificial prompts with real user workflows
- **Structured expected results** - Added specific JSON response validation

### 🚀 New Test Categories
- **Lifecycle Tests** - Complete note workflows from creation to deletion
- **Multi-step Workflows** - Realistic user scenarios (meeting notes, research collection)
- **Performance Testing** - Concurrent operations and large content handling
- **Edge Case Coverage** - Unicode, special characters, error conditions
- **Security Testing** - Input sanitization and data integrity validation

### 📊 Enhanced Validation
- **Specific Response Schemas** - Exact JSON structure expectations
- **Error Format Validation** - Proper error response structure testing
- **Performance Thresholds** - Measurable response time and load testing
- **Data Integrity Checks** - Content preservation and consistency validation

## 🚀 Quick Start

### Prerequisites

1. **OpenAI API Key**: Set your `OPENAI_API_KEY` environment variable ✅
2. **Node.js**: Version 18 or higher ✅
3. **Python**: Version 3.10+ with the Simplenote MCP server installed ✅

### Installation

```bash
# Install Node.js dependencies
npm install

# Validate evaluation files
npm run validate:evals
```

### Running Evaluations ✅

```bash
# Run smoke tests (fast, basic validation) - ✅ OPTIMIZED
npm run eval:smoke

# Run basic evaluation suite - ✅ REDESIGNED  
npm run eval:basic

# Run comprehensive evaluation suite - ✅ ENHANCED
npm run eval:comprehensive

# Run all evaluations
npm run eval:all
```

## 🧪 Evaluation Types

### Smoke Tests (`smoke-tests.yaml`)

**Duration**: < 2 minutes | **Model**: gpt-4o-mini | **Cost**: Low

Quick validation tests for CI/CD pipelines:
- ✅ Basic note creation and cleanup
- ✅ Search functionality validation  
- ✅ Error handling with invalid IDs
- ✅ Tool availability verification

### Basic Evaluations (`simplenote-evals.yaml`)

**Duration**: 5-10 minutes | **Model**: gpt-4o | **Cost**: Medium

Realistic workflow testing:
- 🔄 **Complete note lifecycle** - Create → Read → Update → Delete with proper cleanup
- 🏷️ **Tag operations** - Add, remove, replace tags with validation
- 🔍 **Multi-step search** - Create test data, search, verify, cleanup
- ⚠️ **Error scenarios** - Invalid IDs, missing parameters, edge cases
- 🚀 **Performance** - Multiple rapid operations, large content handling

### Comprehensive Evaluations (`comprehensive-evals.yaml`)

**Duration**: 15-30 minutes | **Model**: gpt-4o-mini | **Cost**: Medium

Production-readiness testing:

- Advanced CRUD operations with edge cases
- Complex search scenarios
- Performance and scale testing
- Security and input validation
- MCP protocol compliance
- Monitoring and observability

## 🔄 CI/CD Integration

### GitHub Actions

The evaluations run automatically on:

- **Pull Requests**: Smoke tests + basic evaluations
- **Manual Trigger**: All evaluation suites
- **Label Trigger**: Add `comprehensive-eval` label to PR for full suite

### Workflow Files

- `.github/workflows/mcp-evaluations.yml` - Main evaluation workflow

### Cost Management

- **Smoke tests**: ~$0.01-0.05 per run (gpt-4o-mini)
- **Basic evaluations**: ~$0.10-0.50 per run (gpt-4o-mini)
- **Comprehensive evaluations**: ~$1.00-5.00 per run (gpt-4o)

💡 **Tip**: GitHub provides 2.5M free GPT-4o mini tokens daily for open source projects!

## 📊 Understanding Results

Each evaluation returns scores in these categories:

- **Accuracy** (1-5): How correct the responses are
- **Completeness** (1-5): How complete the responses are
- **Relevance** (1-5): How relevant responses are to the query
- **Clarity** (1-5): How clear and understandable responses are
- **Reasoning** (1-5): Quality of reasoning in responses
- **Overall Comments**: Detailed feedback on strengths and weaknesses

## 🛠️ Development

### Adding New Evaluations

1. Add your evaluation to the appropriate YAML file:

```yaml
- name: your_test_name
  description: What this test validates
  prompt: "The prompt to send to the MCP server"
  expected_result: "Description of expected behavior"
```

1. Validate the YAML:

```bash
npm run validate:evals
```

1. Test locally:

```bash
npm run eval:smoke  # Test your changes
```

### Custom Evaluation Files

Create custom evaluation files following the same structure:

```bash
# Run custom evaluation file
npx mcp-eval path/to/your/custom-evals.yaml simplenote_mcp_server.py
```

## 🔍 Troubleshooting

### Common Issues

1. **OpenAI API Key not set**:

   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Server not starting**:
   - Check Python environment
   - Verify Simplenote credentials
   - Check server logs

3. **Evaluation failures**:
   - Verify YAML syntax
   - Check server responsiveness
   - Review evaluation prompts

### Debug Mode

Run evaluations with debug output:

```bash
DEBUG=1 npm run eval:smoke
```

## 📚 Resources

- [mcp-evals Documentation](https://github.com/mclenhard/mcp-evals)
- [Model Context Protocol](https://github.com/modelcontextprotocol)
- [OpenAI API Documentation](https://platform.openai.com/docs)

## 🤝 Contributing

1. Add new evaluations for uncovered functionality
2. Improve existing evaluation prompts for better accuracy
3. Update documentation for new evaluation patterns
4. Report issues with evaluation reliability

---

**Note**: Evaluations help ensure the MCP server works correctly and performs well. Regular evaluation runs catch regressions and validate new features.
