# MCP Evaluations for Simplenote MCP Server ✅

This directory contains evaluation configurations for testing the Simplenote MCP Server using [mcp-evals](https://github.com/mclenhard/mcp-evals).

**Status**: ✅ **WORKING** - All evaluations successfully running with TypeScript wrapper!

## 📁 Evaluation Files

- **`smoke-tests.yaml`** - Quick smoke tests for basic functionality validation ✅ **PASSING**
- **`simplenote-evals.yaml`** - Standard evaluation suite for core Simplenote operations
- **`comprehensive-evals.yaml`** - Comprehensive evaluation suite for thorough testing
- **`mcp-server-wrapper.ts`** - TypeScript wrapper that bridges Python server with Node.js mcp-evals

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
# Run smoke tests (fast, basic validation) - ✅ WORKING
npm run eval:smoke

# Run basic evaluation suite
npm run eval:basic

# Run comprehensive evaluation suite (thorough, uses more API credits)
npm run eval:comprehensive

# Run all evaluations
npm run eval:all
```

## 📊 Latest Test Results

**Smoke Tests Results** (from latest run):

- **Server Startup**: 4.6/5 ⭐ (Excellent)
- **Authentication**: 4.0/5 ⭐ (Good)
- **Basic Note Operations**: 3.8/5 ⭐ (Good)
- **Search Functionality**: 5.0/5 ⭐ (Perfect)
- **Error Handling**: 1.4/5 ⚠️ (Needs improvement)

**Overall**: **4 out of 5 tests passing excellently!**

## 🔧 Configuration

### Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `SIMPLENOTE_EMAIL` - Simplenote account email for testing
- `SIMPLENOTE_PASSWORD` - Simplenote account password for testing

### Model Configuration

All evaluation files are configured to use OpenAI models:

- **Smoke tests**: `gpt-4o-mini` (cost-effective for frequent testing)
- **Basic evaluations**: `gpt-4o-mini` (balanced performance and cost)
- **Comprehensive evaluations**: `gpt-4o` (highest quality for thorough testing)

## 🧪 Evaluation Types

### Smoke Tests (`smoke-tests.yaml`)

Quick validation tests that run in under 2 minutes:

- Server startup and responsiveness
- Basic authentication
- Simple CRUD operations
- Basic search functionality
- Error handling

### Basic Evaluations (`simplenote-evals.yaml`)

Standard test suite covering core functionality:

- Note creation, retrieval, update, deletion
- Search with various filters
- Tag management
- Error handling scenarios
- Performance with moderate load

### Comprehensive Evaluations (`comprehensive-evals.yaml`)

Thorough testing for production readiness:

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
