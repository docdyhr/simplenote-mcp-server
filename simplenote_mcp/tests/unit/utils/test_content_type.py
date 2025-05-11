"""
Unit tests for content type detection utilities.
"""

import pytest

from simplenote_mcp.server.utils.content_type import (
    ContentType,
    detect_content_type,
    get_content_type_hint,
    _is_likely_markdown,
    _is_likely_code,
    _is_likely_json,
    _is_likely_yaml,
    _is_likely_html,
)


class TestContentTypeDetection:
    """Test cases for content type detection functions."""

    def test_empty_content(self):
        """Test that empty content is detected as plain text."""
        assert detect_content_type("") == ContentType.PLAIN_TEXT
        assert detect_content_type(" \n ") == ContentType.PLAIN_TEXT

    def test_plain_text_detection(self):
        """Test plain text detection."""
        content = """
        This is a simple note with plain text.
        It has multiple lines but no special formatting.
        """
        assert detect_content_type(content) == ContentType.PLAIN_TEXT

    def test_markdown_detection(self):
        """Test Markdown detection."""
        content = """
        # Heading 1
        
        This is a paragraph with **bold** and *italic* text.
        
        - List item 1
        - List item 2
        
        [Link text](https://example.com)
        
        > Blockquote text
        """
        assert detect_content_type(content) == ContentType.MARKDOWN
        assert _is_likely_markdown(content) is True

    def test_code_detection(self):
        """Test code detection."""
        content = """
        def calculate_sum(a, b):
            \"\"\"Calculate sum of two numbers.\"\"\"
            return a + b
            
        # Call the function
        result = calculate_sum(5, 10)
        print(f"The sum is {result}")
        """
        assert detect_content_type(content) == ContentType.CODE
        assert _is_likely_code(content) is True

    def test_code_block_in_markdown(self):
        """Test code block within Markdown."""
        content = """
        # Code Example
        
        Here's a Python code snippet:
        
        ```python
        def hello_world():
            print("Hello, world!")
        ```
        """
        assert detect_content_type(content) == ContentType.MARKDOWN
        assert _is_likely_markdown(content) is True

    def test_json_detection(self):
        """Test JSON detection."""
        content = """
        {
            "name": "John Doe",
            "age": 30,
            "isActive": true,
            "address": {
                "street": "123 Main St",
                "city": "Anytown"
            },
            "hobbies": ["reading", "cycling", "swimming"]
        }
        """
        assert detect_content_type(content) == ContentType.JSON
        assert _is_likely_json(content) is True

    def test_yaml_detection(self):
        """Test YAML detection."""
        content = """
        ---
        name: John Doe
        age: 30
        isActive: true
        address:
          street: 123 Main St
          city: Anytown
        hobbies:
          - reading
          - cycling
          - swimming
        """
        assert detect_content_type(content) == ContentType.YAML
        assert _is_likely_yaml(content) is True

    def test_html_detection(self):
        """Test HTML detection."""
        content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sample Page</title>
        </head>
        <body>
            <h1>Hello World</h1>
            <p>This is a paragraph.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
        </html>
        """
        assert detect_content_type(content) == ContentType.HTML
        assert _is_likely_html(content) is True

    def test_content_type_hint(self):
        """Test getting content type hint dictionary."""
        markdown_content = "# Heading\n\n- List item"
        hint = get_content_type_hint(markdown_content)
        
        assert isinstance(hint, dict)
        assert "content_type" in hint
        assert hint["content_type"] == ContentType.MARKDOWN
        assert "format" in hint
        assert hint["format"] == "text/markdown"


class TestEdgeCases:
    """Test edge cases for content type detection."""

    def test_short_markdown(self):
        """Test detection of short Markdown content."""
        assert _is_likely_markdown("# Just a heading") is True
        assert _is_likely_markdown("[link](https://example.com)") is True

    def test_ambiguous_content(self):
        """Test content that could be interpreted multiple ways."""
        # JSON-like but not valid JSON
        content = """
        {
            name: John Doe,
            age: 30,
        }
        """
        assert detect_content_type(content) == ContentType.PLAIN_TEXT

    def test_detection_priority(self):
        """Test that detection follows the correct priority order."""
        # This could be JSON or code, but JSON should be detected first
        content = """
        {
            "function": "def example():",
            "description": "# This looks like a heading"
        }
        """
        assert detect_content_type(content) == ContentType.JSON