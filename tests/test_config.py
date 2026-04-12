"""Tests for server configuration management."""

import os
import sys
from unittest.mock import patch

import pytest

from simplenote_mcp.server.config import Config, LogLevel, get_config


class TestLogLevel:
    """Test the LogLevel enum."""

    def test_log_level_values(self):
        """Test LogLevel enum values are correct."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"

    def test_from_string_valid_levels(self):
        """Test from_string with valid log levels."""
        assert LogLevel.from_string("DEBUG") == LogLevel.DEBUG
        assert LogLevel.from_string("debug") == LogLevel.DEBUG
        assert LogLevel.from_string("Debug") == LogLevel.DEBUG
        assert LogLevel.from_string("DEBUGGING") == LogLevel.DEBUG
        assert LogLevel.from_string("VERBOSE") == LogLevel.DEBUG

        assert LogLevel.from_string("INFO") == LogLevel.INFO
        assert LogLevel.from_string("info") == LogLevel.INFO
        assert LogLevel.from_string("INFORMATION") == LogLevel.INFO

        assert LogLevel.from_string("WARNING") == LogLevel.WARNING
        assert LogLevel.from_string("warning") == LogLevel.WARNING
        assert LogLevel.from_string("WARN") == LogLevel.WARNING

        assert LogLevel.from_string("ERROR") == LogLevel.ERROR
        assert LogLevel.from_string("error") == LogLevel.ERROR
        assert LogLevel.from_string("ERR") == LogLevel.ERROR

    def test_from_string_invalid_levels(self):
        """Test from_string with invalid log levels defaults to INFO."""
        assert LogLevel.from_string("INVALID") == LogLevel.INFO
        assert LogLevel.from_string("") == LogLevel.INFO
        assert LogLevel.from_string("123") == LogLevel.INFO
        assert LogLevel.from_string("TRACE") == LogLevel.INFO

    def test_from_string_case_insensitive(self):
        """Test from_string is case insensitive."""
        assert LogLevel.from_string("debug") == LogLevel.DEBUG
        assert LogLevel.from_string("Debug") == LogLevel.DEBUG
        assert LogLevel.from_string("DEBUG") == LogLevel.DEBUG
        assert LogLevel.from_string("dEbUg") == LogLevel.DEBUG


class TestConfig:
    """Test the Config class."""

    def test_config_creation_with_defaults(self):
        """Test creating Config with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            # Default values
            assert config.simplenote_email is None
            assert config.simplenote_password is None
            assert config.sync_interval_seconds == 120
            assert config.default_resource_limit == 100
            assert config.title_max_length == 30
            assert config.snippet_max_length == 300
            assert config.cache_max_size == 1000
            assert config.cache_initialization_timeout == 60
            assert config.metrics_collection_interval == 60
            assert config.log_level == LogLevel.INFO
            assert config.log_to_file is True
            assert config.log_format == "standard"
            assert config.debug_mode is False

    def test_config_creation_with_env_vars(self):
        """Test creating Config with environment variables."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "SYNC_INTERVAL_SECONDS": "300",
            "DEFAULT_RESOURCE_LIMIT": "200",
            "TITLE_MAX_LENGTH": "50",
            "SNIPPET_MAX_LENGTH": "150",
            "CACHE_MAX_SIZE": "2000",
            "CACHE_INITIALIZATION_TIMEOUT": "120",
            "METRICS_COLLECTION_INTERVAL": "30",
            "LOG_LEVEL": "DEBUG",
            "LOG_TO_FILE": "false",
            "LOG_FORMAT": "json",
            "MCP_DEBUG": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()

            assert config.simplenote_email == "test@example.com"
            assert config.simplenote_password == "test_password"  # noqa: S105
            assert config.sync_interval_seconds == 300
            assert config.default_resource_limit == 200
            assert config.title_max_length == 50
            assert config.snippet_max_length == 150
            assert config.cache_max_size == 2000
            assert config.cache_initialization_timeout == 120
            assert config.metrics_collection_interval == 30
            assert config.log_level == LogLevel.DEBUG
            assert config.log_to_file is False
            assert config.log_format == "json"
            assert config.debug_mode is True

    def test_config_simplenote_username_fallback(self):
        """Test that SIMPLENOTE_USERNAME falls back if SIMPLENOTE_EMAIL not set."""
        env_vars = {
            "SIMPLENOTE_USERNAME": "test_user@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.simplenote_email == "test_user@example.com"

    def test_config_email_takes_precedence(self):
        """Test that SIMPLENOTE_EMAIL takes precedence over SIMPLENOTE_USERNAME."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "email@example.com",
            "SIMPLENOTE_USERNAME": "username@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.simplenote_email == "email@example.com"

    def test_config_log_level_env_var_priority(self):
        """Test log level environment variable priority."""
        # Test LOG_LEVEL takes highest priority
        env_vars = {
            "LOG_LEVEL": "ERROR",
            "SIMPLENOTE_LOG_LEVEL": "DEBUG",
            "MCP_LOG_LEVEL": "WARNING",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.log_level == LogLevel.ERROR

        # Test SIMPLENOTE_LOG_LEVEL when LOG_LEVEL not set
        env_vars = {"SIMPLENOTE_LOG_LEVEL": "WARNING", "MCP_LOG_LEVEL": "DEBUG"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.log_level == LogLevel.WARNING

    def test_config_debug_mode_overrides_log_level(self):
        """Test that debug mode overrides log level."""
        env_vars = {
            "LOG_LEVEL": "ERROR",
            "MCP_DEBUG": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.debug_mode is True
            assert config.log_level == LogLevel.DEBUG

    def test_config_log_to_file_variations(self):
        """Test various boolean values for LOG_TO_FILE."""
        true_values = ["true", "1", "t", "yes", "True", "YES", "T"]
        false_values = ["false", "0", "f", "no", "False", "NO", "F", "invalid"]

        for value in true_values:
            with patch.dict(os.environ, {"LOG_TO_FILE": value}, clear=True):
                config = Config()
                assert config.log_to_file is True, f"Failed for value: {value}"

        for value in false_values:
            with patch.dict(os.environ, {"LOG_TO_FILE": value}, clear=True):
                config = Config()
                assert config.log_to_file is False, f"Failed for value: {value}"

    def test_config_mcp_debug_variations(self):
        """Test various boolean values for MCP_DEBUG."""
        true_values = ["true", "1", "t", "yes", "True", "YES", "T"]
        false_values = ["false", "0", "f", "no", "False", "NO", "F", "invalid"]

        for value in true_values:
            with patch.dict(os.environ, {"MCP_DEBUG": value}, clear=True):
                config = Config()
                assert config.debug_mode is True, f"Failed for value: {value}"

        for value in false_values:
            with patch.dict(os.environ, {"MCP_DEBUG": value}, clear=True):
                config = Config()
                assert config.debug_mode is False, f"Failed for value: {value}"

    def test_has_credentials_true(self):
        """Test has_credentials returns True when both email and password are set."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.has_credentials is True

    def test_has_credentials_false_no_email(self):
        """Test has_credentials returns False when email is missing."""
        env_vars = {"SIMPLENOTE_PASSWORD": "test_password"}  # noqa: S105

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.has_credentials is False

    def test_has_credentials_false_no_password(self):
        """Test has_credentials returns False when password is missing."""
        env_vars = {"SIMPLENOTE_EMAIL": "test@example.com"}

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.has_credentials is False

    def test_has_credentials_false_empty_strings(self):
        """Test has_credentials returns False with empty string credentials."""
        env_vars = {"SIMPLENOTE_EMAIL": "", "SIMPLENOTE_PASSWORD": ""}

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.has_credentials is False


class TestConfigValidation:
    """Test Config validation."""

    def test_validate_success(self):
        """Test successful validation with valid config."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            # Should not raise any exception
            config.validate()

    def test_validate_missing_credentials(self):
        """Test validation fails when credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            with pytest.raises(
                ValueError,
                match="SIMPLENOTE_EMAIL.*and SIMPLENOTE_PASSWORD.*must be set",
            ):
                config.validate()

    def test_validate_invalid_sync_interval(self):
        """Test validation fails with invalid sync interval."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "SYNC_INTERVAL_SECONDS": "5",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(
                ValueError, match="SYNC_INTERVAL_SECONDS must be at least 10 seconds"
            ):
                config.validate()

    def test_validate_invalid_resource_limit(self):
        """Test validation fails with invalid resource limit."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "DEFAULT_RESOURCE_LIMIT": "0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(
                ValueError, match="DEFAULT_RESOURCE_LIMIT must be at least 1"
            ):
                config.validate()

    def test_validate_invalid_title_max_length(self):
        """Test validation fails with invalid title max length."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "TITLE_MAX_LENGTH": "0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(ValueError, match="TITLE_MAX_LENGTH must be at least 1"):
                config.validate()

    def test_validate_invalid_snippet_max_length(self):
        """Test validation fails with invalid snippet max length."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "SNIPPET_MAX_LENGTH": "0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(
                ValueError, match="SNIPPET_MAX_LENGTH must be at least 1"
            ):
                config.validate()

    def test_validate_invalid_cache_max_size(self):
        """Test validation fails with invalid cache max size."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "CACHE_MAX_SIZE": "0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(ValueError, match="CACHE_MAX_SIZE must be at least 1"):
                config.validate()

    def test_validate_invalid_cache_timeout(self):
        """Test validation fails with invalid cache timeout."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "CACHE_INITIALIZATION_TIMEOUT": "0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(
                ValueError, match="CACHE_INITIALIZATION_TIMEOUT must be at least 1"
            ):
                config.validate()

    def test_validate_invalid_metrics_interval(self):
        """Test validation fails with invalid metrics interval."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "test@example.com",
            "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            "METRICS_COLLECTION_INTERVAL": "0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            with pytest.raises(
                ValueError, match="METRICS_COLLECTION_INTERVAL must be at least 1"
            ):
                config.validate()


class TestConfigSingleton:
    """Test the global configuration singleton."""

    def setup_method(self):
        """Reset global config before each test."""
        sys.modules["simplenote_mcp.server.config"]._config = None  # noqa: SLF001

    def teardown_method(self):
        """Reset global config after each test."""
        sys.modules["simplenote_mcp.server.config"]._config = None  # noqa: SLF001

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
        assert isinstance(config1, Config)

    def test_get_config_creates_instance(self):
        """Test that get_config creates instance on first call."""
        # Ensure global config is None
        import simplenote_mcp.server.config

        # Reset the global config for clean tests  # noqa: SLF001
        simplenote_mcp.server.config._config = None  # noqa: SLF001

        config = get_config()
        assert isinstance(config, Config)

    def test_get_config_with_env_vars(self):
        """Test get_config respects environment variables."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "singleton@example.com",
            "SIMPLENOTE_PASSWORD": "singleton_password",
            "LOG_LEVEL": "ERROR",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = get_config()
            assert config.simplenote_email == "singleton@example.com"
            assert config.log_level == LogLevel.ERROR


class TestConfigIntegration:
    """Integration tests for Config."""

    def test_config_env_var_type_conversion(self):
        """Test that environment variables are correctly converted to appropriate types."""
        env_vars = {
            "SYNC_INTERVAL_SECONDS": "300",
            "DEFAULT_RESOURCE_LIMIT": "50",
            "TITLE_MAX_LENGTH": "25",
            "SNIPPET_MAX_LENGTH": "75",
            "CACHE_MAX_SIZE": "500",
            "CACHE_INITIALIZATION_TIMEOUT": "30",
            "METRICS_COLLECTION_INTERVAL": "45",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()

            # Verify all values are integers
            assert isinstance(config.sync_interval_seconds, int)
            assert isinstance(config.default_resource_limit, int)
            assert isinstance(config.title_max_length, int)
            assert isinstance(config.snippet_max_length, int)
            assert isinstance(config.cache_max_size, int)
            assert isinstance(config.cache_initialization_timeout, int)
            assert isinstance(config.metrics_collection_interval, int)

            # Verify correct values
            assert config.sync_interval_seconds == 300
            assert config.default_resource_limit == 50
            assert config.title_max_length == 25
            assert config.snippet_max_length == 75
            assert config.cache_max_size == 500
            assert config.cache_initialization_timeout == 30
            assert config.metrics_collection_interval == 45

    def test_config_comprehensive_scenario(self):
        """Test a comprehensive configuration scenario."""
        env_vars = {
            "SIMPLENOTE_EMAIL": "comprehensive@example.com",
            "SIMPLENOTE_PASSWORD": "comprehensive_password",
            "SYNC_INTERVAL_SECONDS": "180",
            "DEFAULT_RESOURCE_LIMIT": "150",
            "TITLE_MAX_LENGTH": "40",
            "SNIPPET_MAX_LENGTH": "120",
            "CACHE_MAX_SIZE": "1500",
            "CACHE_INITIALIZATION_TIMEOUT": "90",
            "METRICS_COLLECTION_INTERVAL": "45",
            "LOG_LEVEL": "WARNING",
            "LOG_TO_FILE": "true",
            "LOG_FORMAT": "json",
            "MCP_DEBUG": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()

            # Test all values are set correctly
            assert config.simplenote_email == "comprehensive@example.com"
            assert config.simplenote_password == "comprehensive_password"  # noqa: S105
            assert config.sync_interval_seconds == 180
            assert config.default_resource_limit == 150
            assert config.title_max_length == 40
            assert config.snippet_max_length == 120
            assert config.cache_max_size == 1500
            assert config.cache_initialization_timeout == 90
            assert config.metrics_collection_interval == 45
            assert config.log_level == LogLevel.WARNING
            assert config.log_to_file is True
            assert config.log_format == "json"
            assert config.debug_mode is False

            # Test properties
            assert config.has_credentials is True

            # Test validation passes
            config.validate()

    def test_offline_mode_configuration(self):
        """Test offline mode configuration."""
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_OFFLINE_MODE": "true",
                "SIMPLENOTE_EMAIL": "",
                "SIMPLENOTE_PASSWORD": "",
            },
            clear=True,
        ):
            config = Config()

            # Test offline mode is enabled
            assert config.offline_mode is True
            assert config.has_credentials is False

            # Test validation passes without credentials in offline mode
            config.validate()

    def test_offline_mode_disabled(self):
        """Test offline mode disabled by default."""
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_OFFLINE_MODE": "false",
                "SIMPLENOTE_EMAIL": "test@example.com",
                "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            },
            clear=True,
        ):
            config = Config()

            # Test offline mode is disabled
            assert config.offline_mode is False
            assert config.has_credentials is True

            # Test validation passes with credentials
            config.validate()  # Should not raise

    @pytest.mark.parametrize(
        "env_value",
        ["true", "1", "t", "yes", "TRUE", "True", "YES", "Yes"],
    )
    def test_offline_mode_truthy_variants(self, env_value):
        """Test offline mode accepts various truthy values."""
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_OFFLINE_MODE": env_value,
                "SIMPLENOTE_EMAIL": "",
                "SIMPLENOTE_PASSWORD": "",
            },
            clear=True,
        ):
            config = Config()
            assert config.offline_mode is True, f"Expected True for '{env_value}'"

    @pytest.mark.parametrize(
        "env_value",
        ["false", "0", "f", "no", "FALSE", "False", "NO", "No", "", "invalid"],
    )
    def test_offline_mode_falsy_variants(self, env_value):
        """Test offline mode rejects various falsy/invalid values."""
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_OFFLINE_MODE": env_value,
                "SIMPLENOTE_EMAIL": "test@example.com",
                "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
            },
            clear=True,
        ):
            config = Config()
            assert config.offline_mode is False, f"Expected False for '{env_value}'"


class TestConfigAltEnvVars:
    """Tests for alternative environment variable names."""

    def test_simplenote_username_alias(self):
        """SIMPLENOTE_USERNAME is accepted as alias for SIMPLENOTE_EMAIL."""
        with patch.dict(
            os.environ,
            {"SIMPLENOTE_USERNAME": "user@example.com", "SIMPLENOTE_PASSWORD": "pw"},
            clear=True,
        ):
            config = Config()
            assert config.simplenote_email == "user@example.com"
            assert config.has_credentials is True


class TestConfigDebugMode:
    """Tests for MCP_DEBUG env var handling (line 134 in config.py)."""

    def test_debug_mode_overrides_log_level(self):
        """MCP_DEBUG=true forces log level to DEBUG even if LOG_LEVEL is INFO."""
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_EMAIL": "test@example.com",
                "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
                "MCP_DEBUG": "true",
                "LOG_LEVEL": "INFO",
            },
            clear=True,
        ):
            config = Config()
            assert config.debug_mode is True
            assert config.log_level == LogLevel.DEBUG

    def test_debug_mode_false_no_override(self):
        """MCP_DEBUG=false leaves log level unchanged."""
        with patch.dict(
            os.environ,
            {
                "SIMPLENOTE_EMAIL": "test@example.com",
                "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
                "MCP_DEBUG": "false",
                "LOG_LEVEL": "ERROR",
            },
            clear=True,
        ):
            config = Config()
            assert config.debug_mode is False
            assert config.log_level == LogLevel.ERROR


class TestConfigValidateRateLimiting:
    """Tests for validate() rate-limiting and transport sections (lines 153-250)."""

    BASE_ENV = {
        "SIMPLENOTE_EMAIL": "test@example.com",
        "SIMPLENOTE_PASSWORD": "test_password",  # noqa: S105
    }

    def test_invalid_rate_limit_requests(self):
        with patch.dict(
            os.environ, {**self.BASE_ENV, "RATE_LIMIT_REQUESTS": "0"}, clear=True
        ):
            config = Config()
            with pytest.raises(
                ValueError, match="RATE_LIMIT_REQUESTS must be at least 1"
            ):
                config.validate()

    def test_invalid_rate_limit_window(self):
        with patch.dict(
            os.environ, {**self.BASE_ENV, "RATE_LIMIT_WINDOW_SECONDS": "0"}, clear=True
        ):
            config = Config()
            with pytest.raises(
                ValueError, match="RATE_LIMIT_WINDOW_SECONDS must be at least 1"
            ):
                config.validate()

    def test_invalid_rate_limit_burst(self):
        with patch.dict(
            os.environ, {**self.BASE_ENV, "RATE_LIMIT_BURST": "0"}, clear=True
        ):
            config = Config()
            with pytest.raises(ValueError, match="RATE_LIMIT_BURST must be at least 1"):
                config.validate()

    def test_invalid_mcp_transport(self):
        with patch.dict(
            os.environ, {**self.BASE_ENV, "MCP_TRANSPORT": "grpc"}, clear=True
        ):
            config = Config()
            with pytest.raises(ValueError, match="MCP_TRANSPORT must be either"):
                config.validate()

    def test_http_transport_invalid_port(self):
        with patch.dict(
            os.environ,
            {**self.BASE_ENV, "MCP_TRANSPORT": "http", "MCP_HTTP_PORT": "80"},
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="MCP_HTTP_PORT must be between"):
                config.validate()

    def test_http_transport_empty_host(self):
        with patch.dict(
            os.environ,
            {**self.BASE_ENV, "MCP_TRANSPORT": "http", "MCP_HTTP_HOST": ""},
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="MCP_HTTP_HOST cannot be empty"):
                config.validate()

    def test_http_transport_path_missing_slash(self):
        with patch.dict(
            os.environ,
            {**self.BASE_ENV, "MCP_TRANSPORT": "http", "MCP_HTTP_PATH": "mcp"},
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="MCP_HTTP_PATH must start with"):
                config.validate()

    def test_enable_http_endpoint_invalid_port(self):
        with patch.dict(
            os.environ,
            {**self.BASE_ENV, "ENABLE_HTTP_ENDPOINT": "true", "HTTP_PORT": "80"},
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="HTTP_PORT must be between"):
                config.validate()

    def test_enable_http_endpoint_empty_host(self):
        with patch.dict(
            os.environ,
            {**self.BASE_ENV, "ENABLE_HTTP_ENDPOINT": "true", "HTTP_HOST": ""},
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="HTTP_HOST cannot be empty"):
                config.validate()

    def test_enable_http_endpoint_metrics_path_missing_slash(self):
        with patch.dict(
            os.environ,
            {
                **self.BASE_ENV,
                "ENABLE_HTTP_ENDPOINT": "true",
                "HTTP_METRICS_PATH": "metrics",
            },
            clear=True,
        ):
            config = Config()
            with pytest.raises(ValueError, match="HTTP_METRICS_PATH must start with"):
                config.validate()
