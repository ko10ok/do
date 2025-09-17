# API Reference

## Core Classes

### ArgumentParser

Main class for parsing command line arguments and processing files.

#### Methods

- `parse_args(args: List[str]) -> RequestStructure`: Parse command line arguments
- `_parse_quoted_string(args: List[str]) -> Tuple[str, int]`: Parse quoted strings
- `_is_file_path(arg: str) -> bool`: Check if argument is a file path
- `_process_file(file_path: str) -> Optional[FileInfo]`: Process file and return info
- `_is_binary_file(path: Path) -> bool`: Check if file is binary

#### Configuration

- `LARGE_FILE_THRESHOLD = 10 * 1024 * 1024`: Size threshold for large files (10MB)
- `BINARY_TRUNCATE_BYTES = 1024`: Bytes to show at start/end for truncated binary files
- `PROVIDERS_WITH_FILE_SUPPORT = {"claude"}`: Providers supporting direct file uploads

### RequestStructure

Data class containing parsed request information.

#### Fields

- `text_query: str`: The processed text query
- `provider: str = "claude"`: LLM provider to use
- `interactive: bool = False`: Whether to use interactive mode
- `dry_run: bool = False`: Whether this is a dry run
- `files: List[FileInfo] = []`: List of files to include
- `raw_args: List[str] = []`: Original command line arguments

### FileInfo

Data class containing file information.

#### Fields

- `path: str`: Absolute path to the file
- `is_binary: bool`: Whether the file is binary
- `size: int`: File size in bytes
- `include_mode: str`: How to include the file ('full', 'truncated', 'as_file')
- `content: Optional[str] = None`: File content (if loaded)

## Provider Classes

### LLMProvider (Abstract Base Class)

Base class for all LLM providers.

#### Abstract Methods

- `_validate_credentials() -> None`: Validate required credentials
- `send_request(request: RequestStructure) -> Iterator[str]`: Send request and yield response
- `supports_files -> bool`: Property indicating file support

### ClaudeProvider

Implementation for Anthropic's Claude.

#### Configuration

- `api_key`: Anthropic API key (required)
- `model`: Claude model name (default: "claude-3-sonnet-20240229")
- `max_tokens`: Maximum tokens in response (default: 4096)

#### Features

- Direct file upload support
- Streaming responses
- Automatic content formatting

### OpenAIProvider

Implementation for OpenAI's ChatGPT.

#### Configuration

- `api_key`: OpenAI API key (required)
- `model`: OpenAI model name (default: "gpt-4")
- `max_tokens`: Maximum tokens in response (default: 4096)

#### Features

- Streaming responses
- File content embedded in text

### DeepSeekProvider

Implementation for DeepSeek's API.

#### Configuration

- `api_key`: DeepSeek API key (required)
- `base_url`: API base URL (default: "https://api.deepseek.com/v1")
- `model`: DeepSeek model name (default: "deepseek-chat")
- `max_tokens`: Maximum tokens in response (default: 4096)

#### Features

- OpenAI-compatible API
- Streaming responses
- File content embedded in text

## Configuration Classes

### ConfigManager

Manages configuration loading and merging.

#### Methods

- `get_provider_config(provider_name: str) -> Dict[str, Any]`: Get provider configuration
- `_load_config() -> Dict[str, Any]`: Load configuration from file
- `_create_default_config() -> None`: Create default configuration file

### ProviderFactory

Factory for creating provider instances.

#### Methods

- `create_provider(provider_name: str) -> LLMProvider`: Create provider instance

## CLI Functions

### main(args: List[str] = None) -> int

Main entry point for the CLI application.

#### Parameters

- `args`: Command line arguments (defaults to sys.argv[1:])

#### Returns

- `0`: Success
- `1`: General error
- `130`: Keyboard interrupt

### print_dry_run_info(request_structure: RequestStructure) -> None

Print detailed information about a request in dry-run mode.

## Error Handling

### Common Exceptions

- `ValueError`: Invalid provider name, missing credentials
- `ImportError`: Missing required packages (anthropic, openai)
- `OSError`: File access errors
- `KeyboardInterrupt`: User cancellation

### Error Messages

All error messages are designed to be user-friendly and provide actionable information:

- Missing API keys include setup instructions
- File errors specify the problematic file
- Network errors suggest retry or connection check
- Invalid arguments show usage examples

## Usage Patterns

### Basic Query

```python
from llm_cli.parser import ArgumentParser
from llm_cli.providers import ProviderFactory

parser = ArgumentParser()
request = parser.parse_args(["Hello", "world"])

factory = ProviderFactory()
provider = factory.create_provider(request.provider)

for chunk in provider.send_request(request):
    print(chunk, end='')
```

### File Processing

```python
# Files are automatically detected and processed
request = parser.parse_args(["Explain", "script.py"])

# Check what files were found
for file_info in request.files:
    print(f"File: {file_info.path}")
    print(f"Binary: {file_info.is_binary}")
    print(f"Mode: {file_info.include_mode}")
```

### Custom Provider Configuration

```python
from llm_cli.providers import ConfigManager

config_manager = ConfigManager()
claude_config = config_manager.get_provider_config("claude")
claude_config["model"] = "claude-3-opus-20240229"

# Create provider with custom config
from llm_cli.providers.claude import ClaudeProvider
provider = ClaudeProvider(claude_config)
```

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_parser.py

# With coverage
pytest --cov=llm_cli --cov-report=html

# Verbose output
pytest -v
```

### Test Structure

- `test_parser.py`: Tests for argument parsing and file handling
- `test_providers.py`: Tests for LLM provider implementations
- `test_main.py`: Tests for CLI functionality and integration

### Mocking External Dependencies

Tests use extensive mocking to avoid actual API calls:

```python
@patch('llm_cli.providers.claude.anthropic')
def test_claude_provider(mock_anthropic):
    # Test without real API calls
    pass
```

## Extension Points

### Adding New Providers

1. Create new provider class inheriting from `LLMProvider`
2. Implement required abstract methods
3. Add provider to `ProviderFactory.create_provider()`
4. Add configuration to `ConfigManager.DEFAULT_CONFIG`
5. Add environment variable mapping

### Custom File Processing

Override `ArgumentParser._process_file()` for custom file handling:

```python
class CustomArgumentParser(ArgumentParser):
    def _process_file(self, file_path: str) -> Optional[FileInfo]:
        # Custom file processing logic
        return super()._process_file(file_path)
```

### Custom Response Processing

Override provider's `send_request()` method for custom response handling:

```python
class CustomClaudeProvider(ClaudeProvider):
    def send_request(self, request: RequestStructure) -> Iterator[str]:
        for chunk in super().send_request(request):
            # Custom processing
            yield process_chunk(chunk)
```
