# Search Engine

This document provides technical documentation for the Simplenote MCP Server's advanced search functionality.

## Overview

The search engine provides powerful search capabilities for finding notes in your Simplenote account. It supports boolean operators, phrase matching, tag filtering, and various search modes to help you find exactly what you're looking for.

## Search Class

::: simplenote_mcp.server.search
    options:
      show_source: true
      heading_level: 3

## Search Features

### Boolean Operators

The search engine supports standard boolean operators for complex queries:

#### AND Operator
Find notes containing all specified terms.

```python
# Search for notes containing both "python" and "tutorial"
results = await search_engine.search("python AND tutorial")

# Implicit AND (space-separated terms)
results = await search_engine.search("python tutorial")
```

#### OR Operator
Find notes containing any of the specified terms.

```python
# Search for notes containing either "python" or "javascript"
results = await search_engine.search("python OR javascript")
```

#### NOT Operator
Exclude notes containing specified terms.

```python
# Search for notes about "programming" but not "python"
results = await search_engine.search("programming NOT python")

# Alternative syntax with minus sign
results = await search_engine.search("programming -python")
```

#### Complex Boolean Expressions
Combine multiple operators with parentheses for complex queries.

```python
# Search for notes about web development but exclude backend topics
results = await search_engine.search("(javascript OR typescript) AND web NOT backend")

# Search for programming tutorials in any language except Java
results = await search_engine.search("(programming OR coding) AND tutorial NOT java")
```

### Phrase Matching

Use quotes to search for exact phrases.

```python
# Search for the exact phrase "machine learning"
results = await search_engine.search('"machine learning"')

# Combine phrases with boolean operators
results = await search_engine.search('"data science" OR "machine learning"')

# Search for phrases with AND operator
results = await search_engine.search('"project management" AND "agile methodology"')
```

### Wildcard Search

Use asterisks (*) for partial matching.

```python
# Search for words starting with "prog"
results = await search_engine.search("prog*")

# Search for words ending with "ing"
results = await search_engine.search("*ing")

# Search for words containing "dev"
results = await search_engine.search("*dev*")
```

### Tag-Based Search

Filter searches by specific tags or search within tagged notes.

```python
# Search within notes tagged with "work"
results = await search_engine.search("meeting", tags=["work"])

# Search within multiple tags
results = await search_engine.search("deadline", tags=["work", "urgent"])

# Boolean search within tagged notes
results = await search_engine.search("project AND status", tags=["work"])
```

## Search Configuration

### Search Engine Configuration

```python
from simplenote_mcp.server.search import AdvancedSearchEngine

search_engine = AdvancedSearchEngine(
    case_sensitive=False,  # Case-insensitive search by default
    stemming=True,  # Enable word stemming
    stop_words=True,  # Filter common stop words
    max_results=100,  # Maximum results per search
    search_timeout=30,  # Search timeout in seconds
    cache_results=True,  # Cache search results
    fuzzy_matching=False,  # Disable fuzzy matching by default
    min_score=0.1,  # Minimum relevance score
)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_CASE_SENSITIVE` | `false` | Enable case-sensitive search |
| `SEARCH_STEMMING` | `true` | Enable word stemming |
| `SEARCH_STOP_WORDS` | `true` | Filter common stop words |
| `SEARCH_MAX_RESULTS` | `100` | Maximum search results |
| `SEARCH_TIMEOUT` | `30` | Search timeout in seconds |
| `SEARCH_CACHE_TTL` | `300` | Search cache TTL in seconds |
| `SEARCH_FUZZY_THRESHOLD` | `0.8` | Fuzzy matching threshold |

## Search Methods

### Basic Search

```python
# Simple text search
results = await search_engine.search("python programming")

# Search with options
results = await search_engine.search(
    query="machine learning", limit=50, include_deleted=False, sort_by="relevance"
)
```

### Advanced Search

```python
# Advanced search with multiple filters
results = await search_engine.advanced_search(
    query="web development",
    tags=["work", "tutorial"],
    date_from="2024-01-01",
    date_to="2024-12-31",
    min_length=100,
    max_length=5000,
    sort_by="modified_date",
    sort_order="desc",
)
```

### Tag Search

```python
# Search by tags only
results = await search_engine.search_by_tags(
    tags=["work", "meeting"],
    operator="AND",  # or "OR"
)

# Get all available tags
tags = await search_engine.get_all_tags()

# Get notes by specific tag
notes = await search_engine.get_notes_by_tag("work", limit=20)
```

### Content Search

```python
# Search in note content only
results = await search_engine.search_content(
    query="algorithm implementation", case_sensitive=False, whole_words=True
)

# Search in note titles only
results = await search_engine.search_titles(query="weekly report", fuzzy=True)
```

## Search Result Format

### Search Result Structure

```python
{
    "results": [
        {
            "note_id": "abc123def456",
            "title": "Python Tutorial Notes",
            "content_preview": "This is a comprehensive guide to Python programming...",
            "tags": ["programming", "python", "tutorial"],
            "created_date": "2024-01-15T10:30:00Z",
            "modified_date": "2024-01-20T14:22:00Z",
            "score": 0.95,
            "highlights": [
                {
                    "field": "content",
                    "fragment": "...comprehensive guide to <mark>Python</mark> <mark>programming</mark>...",
                }
            ],
        }
    ],
    "total_results": 15,
    "search_time_ms": 45,
    "query_info": {
        "original_query": "python programming",
        "parsed_query": "python AND programming",
        "filters_applied": ["active_notes_only"],
    },
}
```

### Result Ranking

Results are ranked based on multiple factors:

1. **Text Relevance**: TF-IDF scoring for content matching
2. **Tag Relevance**: Exact tag matches get higher scores
3. **Recency**: More recently modified notes get slight boost
4. **Length**: Optimal note length gets preference
5. **Title Matches**: Title matches get higher scores

### Highlighting

Search results include highlighted snippets showing where matches were found:

```python
# Highlighting configuration
search_engine.configure_highlighting(
    highlight_tag="<mark>",  # HTML tag for highlights
    close_tag="</mark>",  # Closing tag
    fragment_size=150,  # Characters per fragment
    max_fragments=3,  # Maximum fragments per note
    fragment_separator="...",  # Separator between fragments
)
```

## Search Performance

### Indexing

The search engine maintains an internal index for fast searching:

```python
# Force index rebuild
await search_engine.rebuild_index()

# Check index status
index_info = await search_engine.get_index_info()
print(f"Indexed notes: {index_info['note_count']}")
print(f"Index size: {index_info['size_mb']:.2f} MB")
print(f"Last updated: {index_info['last_updated']}")
```

### Search Optimization

```python
# Configure search performance
search_engine.configure_performance(
    index_update_interval=300,  # Update index every 5 minutes
    background_indexing=True,  # Index updates in background
    parallel_search=True,  # Enable parallel search
    max_concurrent_searches=5,  # Limit concurrent searches
)
```

### Caching

Search results are automatically cached for improved performance:

```python
# Configure search caching
search_engine.configure_cache(
    cache_size=1000,  # Cache up to 1000 search results
    cache_ttl=300,  # Cache for 5 minutes
    cache_similar_queries=True,  # Cache similar queries
)

# Clear search cache
await search_engine.clear_cache()
```

## Search Analytics

### Search Statistics

```python
# Get search statistics
stats = await search_engine.get_search_stats()

print(f"Total searches: {stats['total_searches']}")
print(f"Average response time: {stats['avg_response_time_ms']:.2f} ms")
print(f"Cache hit ratio: {stats['cache_hit_ratio']:.2%}")
print(f"Most common queries: {stats['top_queries']}")
```

### Query Analysis

```python
# Analyze query patterns
analysis = await search_engine.analyze_queries(
    start_date="2024-01-01", end_date="2024-12-31"
)

print(f"Most searched terms: {analysis['top_terms']}")
print(f"Search frequency by hour: {analysis['hourly_distribution']}")
print(f"Failed searches: {analysis['failed_searches']}")
```

## Error Handling

### Search Exceptions

```python
from simplenote_mcp.server.errors import (
    SearchError,
    QueryParseError,
    SearchTimeoutError,
    IndexError,
)

try:
    results = await search_engine.search("complex query")
except QueryParseError as e:
    print(f"Invalid query syntax: {e}")
except SearchTimeoutError as e:
    print(f"Search timed out: {e}")
except IndexCorruptionError as e:
    print(f"Search index corrupted: {e}")
    await search_engine.rebuild_index()
except SearchError as e:
    print(f"General search error: {e}")
```

### Error Recovery

```python
# Configure error handling
search_engine.configure_error_handling(
    auto_retry=True,  # Automatically retry failed searches
    max_retries=3,  # Maximum retry attempts
    retry_delay=1.0,  # Delay between retries
    fallback_to_simple=True,  # Fall back to simple search on complex query failure
)
```

## Advanced Features

### Fuzzy Search

Enable fuzzy matching for typo tolerance:

```python
# Enable fuzzy search
search_engine.enable_fuzzy_search(
    threshold=0.8,  # Similarity threshold (0.0-1.0)
    max_distance=2,  # Maximum edit distance
    prefix_length=1,  # Minimum prefix match length
)

# Fuzzy search example
results = await search_engine.fuzzy_search(
    "pythno programing"
)  # Finds "python programming"
```

### Semantic Search

Enable semantic search for concept-based matching:

```python
# Enable semantic search (requires additional setup)
search_engine.enable_semantic_search(
    model="sentence-transformers/all-MiniLM-L6-v2", similarity_threshold=0.7
)

# Semantic search example
results = await search_engine.semantic_search("machine learning concepts")
# Finds notes about AI, neural networks, algorithms, etc.
```

### Custom Scoring

Define custom scoring functions for search results:

```python
def custom_scorer(note, query_terms):
    """Custom scoring function."""
    score = 0.0

    # Boost recent notes
    days_old = (datetime.now() - note["modified_date"]).days
    recency_boost = max(0, 1.0 - days_old / 365)
    score += recency_boost * 0.2

    # Boost notes with many tags
    tag_boost = min(len(note["tags"]) * 0.1, 0.3)
    score += tag_boost

    # Boost shorter notes (easier to read)
    length_penalty = min(len(note["content"]) / 10000, 0.2)
    score -= length_penalty

    return score


# Register custom scorer
search_engine.register_scorer("custom", custom_scorer)

# Use custom scoring
results = await search_engine.search("python", scorer="custom")
```

### Search Filters

Define reusable search filters:

```python
# Define custom filters
@search_engine.filter("recent")
def recent_notes_filter(note):
    """Filter for notes modified in the last 30 days."""
    cutoff = datetime.now() - timedelta(days=30)
    return note["modified_date"] > cutoff


@search_engine.filter("long")
def long_notes_filter(note):
    """Filter for notes longer than 1000 characters."""
    return len(note["content"]) > 1000


# Use filters in search
results = await search_engine.search("machine learning", filters=["recent", "long"])
```

## Integration Examples

### MCP Tool Integration

```python
from simplenote_mcp.server import SimplenoteServer


class SimplenoteServer:
    def __init__(self):
        self.search_engine = AdvancedSearchEngine()

    @tool("search_notes")
    async def search_notes(self, query: str, tags: list = None, limit: int = 20):
        """Search notes with advanced features."""
        results = await self.search_engine.search(query=query, tags=tags, limit=limit)

        return {
            "results": results["results"],
            "total": results["total_results"],
            "search_time": results["search_time_ms"],
        }
```

### Claude Desktop Integration

The search functionality is automatically available in Claude Desktop through the MCP server:

```
# Natural language search commands in Claude Desktop:
"Find my notes about Python programming"
"Search for meeting notes from last week"
"Show me all notes tagged with 'work' that mention 'deadline'"
"Find notes containing the exact phrase 'quarterly review'"
```

## Performance Benchmarks

### Search Performance

Typical performance metrics for different search operations:

| Operation | Time (ms) | Notes Searched | Results |
|-----------|-----------|----------------|---------|
| Simple text search | 10-50 | 1,000 | 20 |
| Boolean search | 20-100 | 1,000 | 15 |
| Phrase search | 15-75 | 1,000 | 8 |
| Tag search | 5-25 | 1,000 | 30 |
| Fuzzy search | 50-200 | 1,000 | 12 |
| Semantic search | 100-500 | 1,000 | 18 |

### Optimization Tips

1. **Use specific terms**: More specific queries are faster
2. **Limit results**: Use the `limit` parameter to reduce processing
3. **Cache frequently used searches**: Enable search result caching
4. **Use tag filters**: Tag filtering is very fast
5. **Avoid overly complex boolean expressions**: Keep queries simple when possible

## Testing

### Search Testing Utilities

```python
from simplenote_mcp.search.testing import SearchTestUtils

# Create test search engine
search_engine = SearchTestUtils.create_test_engine()

# Populate with test data
await SearchTestUtils.populate_test_data(search_engine, num_notes=1000)

# Run search tests
test_results = await SearchTestUtils.run_search_tests(search_engine)
print(f"Test pass rate: {test_results['pass_rate']:.2%}")
```

### Performance Testing

```python
async def benchmark_search():
    """Benchmark search performance."""
    search_engine = AdvancedSearchEngine()

    # Test different query types
    queries = [
        "simple search",
        "boolean AND search",
        '"exact phrase"',
        "wildcard search*",
        "complex (query OR search) AND test",
    ]

    for query in queries:
        start_time = time.time()
        results = await search_engine.search(query)
        search_time = time.time() - start_time

        print(f"Query: {query}")
        print(f"Time: {search_time * 1000:.2f} ms")
        print(f"Results: {len(results['results'])}")
        print("---")
```

## Best Practices

### Query Design

1. **Use specific terms**: "python tutorial" vs "programming"
2. **Combine operators**: Use AND/OR for precise results
3. **Use tags effectively**: Filter by tags for faster searches
4. **Avoid overly broad queries**: Limit scope for better performance

### Performance Optimization

1. **Enable caching**: Cache frequently used searches
2. **Use appropriate limits**: Don't request more results than needed
3. **Update index regularly**: Keep search index current
4. **Monitor performance**: Track search times and optimize slow queries

### Error Handling

1. **Handle parse errors**: Provide fallback for invalid queries
2. **Implement timeouts**: Set reasonable search timeouts
3. **Graceful degradation**: Fall back to simple search if advanced features fail
4. **User feedback**: Provide helpful error messages

## Troubleshooting

### Common Issues

1. **Slow searches**: Check query complexity, enable caching, update index
2. **No results found**: Verify query syntax, check for typos, try simpler terms
3. **Inconsistent results**: Rebuild search index, check for data corruption
4. **Memory usage**: Adjust cache size, limit concurrent searches

### Debug Mode

```python
# Enable search debugging
search_engine = AdvancedSearchEngine(debug=True)

# This will log detailed search information
results = await search_engine.search("debug query")
```

### Index Maintenance

```python
# Check index health
health = await search_engine.check_index_health()
if not health["healthy"]:
    print(f"Index issues: {health['issues']}")
    await search_engine.rebuild_index()

# Optimize index performance
await search_engine.optimize_index()
```

## API Reference

For complete API documentation, see the source code documentation and type hints in the `simplenote_mcp.server.search` module.

## Related Documentation

- [Server API](server.md) - Main server implementation
- [Cache System](cache.md) - Caching system that works with search
- [Configuration](../configuration.md) - Search configuration options
- [Usage Guide](../usage.md) - Practical search examples
