"""Unit tests for LLM providers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from doq.providers import ConfigManager, ProviderFactory, LLMProvider
from doq.parser import RequestStructure, FileInfo


class TestConfigManager:
    """Test cases for ConfigManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()

    @patch('doq.providers.Path.home')
    @patch('doq.providers.Path.exists')
    def test_config_file_not_exists(self, mock_exists, mock_home):
        """Test behavior when config file doesn't exist."""
        mock_home.return_value = "/fake/home"
        mock_exists.return_value = False

        with patch.object(self.config_manager, '_create_default_config'):
            config = self.config_manager._load_config()

        assert config["default_provider"] == "claude"
        assert "claude" in config["providers"]
        assert "openai" in config["providers"]
        assert "deepseek" in config["providers"]

    @patch('doq.providers.Path.home')
    @patch('doq.providers.Path.exists')
    @patch('builtins.open')
    @patch('doq.providers.yaml.safe_load')
    def test_config_file_loading(self, mock_yaml_load, mock_open, mock_exists, mock_home):
        """Test loading existing config file."""
        mock_home.return_value = "/fake/home"
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "default_provider": "openai",
            "providers": {
                "openai": {"api_key": "test-key"}
            }
        }

        config = self.config_manager._load_config()

        assert config["default_provider"] == "openai"
        assert config["providers"]["openai"]["api_key"] == "test-key"

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-claude-key'})
    def test_env_variable_override(self):
        """Test that environment variables override config file."""
        config = self.config_manager.get_provider_config("claude")

        assert config["api_key"] == "env-claude-key"

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'env-openai-key'})
    def test_openai_env_variable(self):
        """Test OpenAI environment variable."""
        config = self.config_manager.get_provider_config("openai")

        assert config["api_key"] == "env-openai-key"

    @patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'env-deepseek-key'})
    def test_deepseek_env_variable(self):
        """Test DeepSeek environment variable."""
        config = self.config_manager.get_provider_config("deepseek")

        assert config["api_key"] == "env-deepseek-key"


class TestProviderFactory:
    """Test cases for ProviderFactory class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = ProviderFactory()

    @patch('doq.providers.claude.ClaudeProvider')
    def test_create_claude_provider(self, mock_claude):
        """Test creating Claude provider."""
        mock_instance = Mock()
        mock_claude.return_value = mock_instance

        with patch.object(self.factory.config_manager, 'get_provider_config',
                         return_value={"api_key": "test-key"}):
            provider = self.factory.create_provider("claude")

        mock_claude.assert_called_once_with({"api_key": "test-key"})

    @patch('doq.providers.openai.OpenAIProvider')
    def test_create_openai_provider(self, mock_openai):
        """Test creating OpenAI provider."""
        mock_instance = Mock()
        mock_openai.return_value = mock_instance

        with patch.object(self.factory.config_manager, 'get_provider_config',
                         return_value={"api_key": "test-key"}):
            provider = self.factory.create_provider("openai")

        mock_openai.assert_called_once_with({"api_key": "test-key"})

    @patch('doq.providers.deepseek.DeepSeekProvider')
    def test_create_deepseek_provider(self, mock_deepseek):
        """Test creating DeepSeek provider."""
        mock_instance = Mock()
        mock_deepseek.return_value = mock_instance

        with patch.object(self.factory.config_manager, 'get_provider_config',
                         return_value={"api_key": "test-key"}):
            provider = self.factory.create_provider("deepseek")

        mock_deepseek.assert_called_once_with({"api_key": "test-key"})

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            self.factory.create_provider("unknown")


class MockProvider(LLMProvider):
    """Mock provider for testing base class."""

    def __init__(self, config):
        self.config = config
        self.supports_files_value = True
        # Call parent's __init__ which will call _validate_credentials
        super().__init__(config)

    def _validate_credentials(self):
        if not self.config.get("api_key"):
            raise ValueError("API key required")

    def send_request(self, request):
        yield "Mock response"

    @property
    def supports_files(self):
        return self.supports_files_value


class TestLLMProvider:
    """Test cases for LLMProvider base class."""

    def test_provider_with_valid_credentials(self):
        """Test provider initialization with valid credentials."""
        config = {"api_key": "test-key"}
        provider = MockProvider(config)

        assert provider.config == config

    def test_provider_without_credentials(self):
        """Test provider initialization without credentials."""
        config = {}

        with pytest.raises(ValueError, match="API key required"):
            MockProvider(config)

    def test_send_request(self):
        """Test sending request through provider."""
        config = {"api_key": "test-key"}
        provider = MockProvider(config)
        request = RequestStructure("test query")

        response = list(provider.send_request(request))

        assert response == ["Mock response"]

    def test_supports_files_property(self):
        """Test supports_files property."""
        config = {"api_key": "test-key"}
        provider = MockProvider(config)

        assert provider.supports_files is True

        provider.supports_files_value = False
        assert provider.supports_files is False


@patch('doq.providers.claude.anthropic')
class TestClaudeProvider:
    """Test cases for Claude provider."""

    def test_claude_initialization(self, mock_anthropic):
        """Test Claude provider initialization."""
        from doq.providers.claude import ClaudeProvider

        config = {"api_key": "test-key", "model": "claude-3-sonnet-20240229"}
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        provider = ClaudeProvider(config)

        assert provider.client == mock_client
        assert provider.model == "claude-3-sonnet-20240229"
        mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")

    def test_claude_supports_files(self, mock_anthropic):
        """Test that Claude supports files."""
        from doq.providers.claude import ClaudeProvider

        config = {"api_key": "test-key"}
        provider = ClaudeProvider(config)

        assert provider.supports_files is True

    def test_claude_send_request(self, mock_anthropic):
        """Test sending request to Claude."""
        from doq.providers.claude import ClaudeProvider

        config = {"api_key": "test-key"}
        mock_client = Mock()
        mock_stream = Mock()
        mock_stream.text_stream = ["Hello", " world", "!"]

        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_stream)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_client.messages.stream.return_value = mock_context_manager

        mock_anthropic.Anthropic.return_value = mock_client

        provider = ClaudeProvider(config)
        request = RequestStructure("test query")

        response = list(provider.send_request(request))

        assert response == ["Hello", " world", "!"]


@patch('doq.providers.openai.openai')
class TestOpenAIProvider:
    """Test cases for OpenAI provider."""

    def test_openai_initialization(self, mock_openai):
        """Test OpenAI provider initialization."""
        from doq.providers.openai import OpenAIProvider

        config = {"api_key": "test-key", "model": "gpt-4"}
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        provider = OpenAIProvider(config)

        assert provider.client == mock_client
        assert provider.model == "gpt-4"
        mock_openai.OpenAI.assert_called_once_with(api_key="test-key")

    def test_openai_no_file_support(self, mock_openai):
        """Test that OpenAI doesn't support files."""
        from doq.providers.openai import OpenAIProvider

        config = {"api_key": "test-key"}
        provider = OpenAIProvider(config)

        assert provider.supports_files is False


@patch('doq.providers.deepseek.openai')
class TestDeepSeekProvider:
    """Test cases for DeepSeek provider."""

    def test_deepseek_initialization(self, mock_openai):
        """Test DeepSeek provider initialization."""
        from doq.providers.deepseek import DeepSeekProvider

        config = {"api_key": "test-key", "base_url": "https://api.deepseek.com/v1"}
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        provider = DeepSeekProvider(config)

        assert provider.client == mock_client
        mock_openai.OpenAI.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1"
        )

    def test_deepseek_no_file_support(self, mock_openai):
        """Test that DeepSeek doesn't support files."""
        from doq.providers.deepseek import DeepSeekProvider

        config = {"api_key": "test-key"}
        provider = DeepSeekProvider(config)

        assert provider.supports_files is False


if __name__ == "__main__":
    pytest.main([__file__])
