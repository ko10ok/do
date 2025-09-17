"""OpenAI provider implementation."""

import sys
from typing import Any, Dict, Iterator

from ..parser import RequestStructure
from ..providers import LLMProvider

try:
    import openai
except ImportError:
    openai = None


class OpenAIProvider(LLMProvider):
    """OpenAI/ChatGPT provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if openai is None:
            raise ImportError("openai package is required for OpenAI provider. Install with: pip install openai")

        self.client = openai.OpenAI(api_key=self.config["api_key"])
        self.model = self.config.get("model", "gpt-4")
        self.max_tokens = self.config.get("max_tokens", 4096)

    def _validate_credentials(self) -> None:
        """Validate that required credentials are available."""
        if not self.config.get("api_key"):
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or add api_key to ~/.llm-cli-config.yaml under providers.openai"
            )

    @property
    def supports_files(self) -> bool:
        """OpenAI does not support direct file uploads in chat completions."""
        return False

    def send_request(self, request: RequestStructure) -> Iterator[str]:
        """Send request to OpenAI and yield response chunks."""
        try:
            messages = self._build_messages(request)

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\nError communicating with OpenAI: {e}\n"

    def _build_messages(self, request: RequestStructure) -> list:
        """Build messages for OpenAI API."""
        # For OpenAI, all content (including files) should already be in text_query
        # since it doesn't support direct file uploads
        return [{
            "role": "user",
            "content": request.text_query
        }]
