"""Base classes and interfaces for DOQ LLM providers."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterator

import yaml

from ..parser import RequestStructure


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_credentials()

    @abstractmethod
    def _validate_credentials(self) -> None:
        """Validate that required credentials are available."""
        pass

    @abstractmethod
    def send_request(self, request: RequestStructure) -> Iterator[str]:
        """Send request to LLM and yield response chunks."""
        pass

    @property
    @abstractmethod
    def supports_files(self) -> bool:
        """Whether this provider supports direct file uploads."""
        pass


class ConfigManager:
    """Manages configuration for LLM providers."""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "default_provider": "claude",
        "providers": {
            "claude": {
                "api_key": None,
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 4096
            },
            "openai": {
                "api_key": None,
                "model": "gpt-4",
                "max_tokens": 4096
            },
            "deepseek": {
                "api_key": None,
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "max_tokens": 4096
            }
        }
    }

    def __init__(self):
        self.config_path = Path.home() / ".doq-config.yaml"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                return self._merge_with_defaults(config)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")

        # Create default config
        self._create_default_config()
        return self.DEFAULT_CONFIG.copy()

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with defaults."""
        merged: Dict[str, Any] = self.DEFAULT_CONFIG.copy()

        if "default_provider" in config:
            merged["default_provider"] = config["default_provider"]

        if "providers" in config:
            providers_dict = merged["providers"]
            assert isinstance(providers_dict, dict), "providers should be a dictionary"
            for provider, settings in config["providers"].items():
                if provider in providers_dict:
                    providers_dict[provider].update(settings)
                else:
                    providers_dict[provider] = settings

        return merged

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False)
            print(f"Created default config at {self.config_path}")
            print("Please edit the config file to add your API keys.")
        except Exception as e:
            print(f"Could not create config file: {e}")

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        provider_config = self.config["providers"].get(provider_name, {}).copy()

        # Check environment variables for API keys
        env_key_map = {
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }

        if provider_name in env_key_map:
            env_key = os.getenv(env_key_map[provider_name])
            if env_key:
                provider_config["api_key"] = env_key

        return provider_config


class ProviderFactory:
    """Factory for creating LLM provider instances."""

    def __init__(self):
        self.config_manager = ConfigManager()

    def create_provider(self, provider_name: str) -> LLMProvider:
        """Create a provider instance."""
        config = self.config_manager.get_provider_config(provider_name)

        if provider_name == "claude":
            from .claude import ClaudeProvider
            return ClaudeProvider(config)
        elif provider_name == "openai":
            from .openai import OpenAIProvider
            return OpenAIProvider(config)
        elif provider_name == "deepseek":
            from .deepseek import DeepSeekProvider
            return DeepSeekProvider(config)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
