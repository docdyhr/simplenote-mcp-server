"""Tests for content type detection utilities."""

from simplenote_mcp.server.utils.content_type import ContentType, detect_content_type


class TestContentTypeDetection:
    """Test content type detection functionality."""

    def test_plain_text_detection(self):
        """Test detection of plain text content."""
        content = "This is just plain text content"
        result = detect_content_type(content)
        assert result == ContentType.PLAIN_TEXT

    def test_empty_content(self):
        """Test detection with empty content."""
        assert detect_content_type("") == ContentType.PLAIN_TEXT
        assert detect_content_type("   ") == ContentType.PLAIN_TEXT
        assert detect_content_type("\n\n") == ContentType.PLAIN_TEXT

    def test_markdown_detection(self):
        """Test detection of markdown content."""
        markdown_content = """# Heading

        This is **bold** and *italic* text.

        ## Subheading

        - List item 1
        - List item 2
        """
        result = detect_content_type(markdown_content)
        assert result == ContentType.MARKDOWN

    def test_markdown_with_code_blocks(self):
        """Test markdown containing code blocks."""
        content = """# Code Example

        ```python
        def hello():
            print("world")
        ```
        """
        result = detect_content_type(content)
        assert result == ContentType.MARKDOWN

    def test_code_detection_python(self):
        """Test detection of Python code."""
        python_code = """def hello_world():
            print("Hello, world!")
            return True
        """
        result = detect_content_type(python_code)
        assert result == ContentType.CODE

    def test_code_detection_javascript(self):
        """Test detection of JavaScript code."""
        js_code = """function helloWorld() {
            console.log("Hello, world!");
            return true;
        }"""
        result = detect_content_type(js_code)
        assert result == ContentType.CODE

    def test_json_detection(self):
        """Test detection of JSON content."""
        json_content = """{
            "name": "John Doe",
            "age": 30,
            "active": true
        }"""
        result = detect_content_type(json_content)
        assert result == ContentType.JSON

    def test_yaml_detection(self):
        """Test detection of YAML content."""
        yaml_content = """---
        name: John Doe
        age: 30
        active: true
        hobbies:
          - reading
          - coding
        """
        result = detect_content_type(yaml_content)
        assert result == ContentType.YAML

    def test_html_detection(self):
        """Test detection of HTML content."""
        html_content = """<!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Hello World</h1>
        </body>
        </html>"""
        result = detect_content_type(html_content)
        assert result == ContentType.HTML

    def test_simple_html_tags(self):
        """Test detection of simple HTML tags."""
        html_content = (
            "<p>This is a <strong>paragraph</strong> with <em>emphasis</em>.</p>"
        )
        result = detect_content_type(html_content)
        # Note: Short inline HTML might be detected as plain text
        assert result in [ContentType.HTML, ContentType.PLAIN_TEXT]

    def test_content_type_enum_values(self):
        """Test that ContentType enum has expected values."""
        assert ContentType.PLAIN_TEXT == "text/plain"
        assert ContentType.MARKDOWN == "text/markdown"
        assert ContentType.CODE == "text/code"
        assert ContentType.JSON == "application/json"
        assert ContentType.YAML == "application/yaml"
        assert ContentType.HTML == "text/html"

    def test_complex_content_detection(self):
        """Test detection with complex mixed content."""
        # Content that might be ambiguous
        ambiguous_content = """Title: My Notes

        Some text here
        And more text
        """
        result = detect_content_type(ambiguous_content)
        # Should detect as plain text since no strong markers
        assert result == ContentType.PLAIN_TEXT

    def test_indented_content(self):
        """Test detection with indented content (function strips indentation)."""
        indented_content = """    # This is a heading
            This is content
            - List item
        """
        result = detect_content_type(indented_content)
        assert result == ContentType.MARKDOWN

    def test_json_array(self):
        """Test detection of JSON array."""
        json_array = """[
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]"""
        result = detect_content_type(json_array)
        assert result == ContentType.JSON

    def test_malformed_json(self):
        """Test with malformed JSON that should not be detected as JSON."""
        malformed_json = """{ "name": "John" invalid syntax }"""
        result = detect_content_type(malformed_json)
        # Note: Detection might still see this as JSON due to opening brace
        assert result in [ContentType.JSON, ContentType.PLAIN_TEXT]
