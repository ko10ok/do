"""Claude provider implementation."""

from typing import Any, Dict, Iterator

from ..parser import RequestStructure
from ..providers import LLMProvider

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore


class ClaudeProvider(LLMProvider):
    """Claude/Anthropic provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if anthropic is None:
            raise ImportError("anthropic package is required for Claude provider. Install with: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=self.config["api_key"])
        self.model = self.config.get("model", "claude-3-sonnet-20240229")
        self.max_tokens = self.config.get("max_tokens", 4096)

    def _validate_credentials(self) -> None:
        """Validate that required credentials are available."""
        if not self.config.get("api_key"):
            raise ValueError(
                "Claude API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or add api_key to ~/.llm-cli-config.yaml under providers.claude"
            )

    @property
    def supports_files(self) -> bool:
        """Claude supports direct file uploads."""
        return True

    def send_request(self, request: RequestStructure) -> Iterator[str]:
        """Send request to Claude and yield response chunks."""
        try:
            messages = self._build_messages(request)

            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            yield f"\nError communicating with Claude: {e}\n"

    def _build_messages(self, request: RequestStructure) -> list:
        """Build messages for Claude API."""
        content = []

        # Add text content
        if request.text_query:
            content.append({
                "type": "text",
                "text": request.text_query
            })

        # Add files if supported
        for file_info in request.files:
            if file_info.include_mode == "as_file" and not file_info.is_binary:
                try:
                    with open(file_info.path, 'r', encoding='utf-8') as f:
                        file_content = f.read()

                    content.append({
                        "type": "text",
                        "text": f"\n\n### {file_info.path} ###\n{file_content}\n"
                    })
                except Exception as e:
                    content.append({
                        "type": "text",
                        "text": f"\n\nError reading {file_info.path}: {e}\n"
                    })

        return [{"role": "user", "content": content}]
