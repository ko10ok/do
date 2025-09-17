# DOQ - Command Line Interface for Multiple LLM Providers

A powerful command-line interface for interacting with various Large Language Model (LLM) providers including Claude (Anthropic), ChatGPT (OpenAI), and DeepSeek.

## Features

- **Multiple LLM Providers**: Support for Claude, OpenAI, and DeepSeek
- **File Processing**: Automatically detect and include text/binary files in queries
- **Smart Argument Parsing**: Handle quoted strings, file paths, and special parameters
- **Interactive Mode**: Confirm requests before sending
- **Dry Run Mode**: Preview requests without sending them
- **Streaming Responses**: Real-time response display
- **Configurable**: Easy configuration via config file or environment variables

## Installation

### From Source

```bash
git clone <repository-url>
cd doq
pip install -e .
```

### From PyPI (when published)

```bash
pip install doq
```

## Quick Start

1. **Install the package**:
   ```bash
   pip install -e .
   ```

2. **Set up API keys** (choose one method):
   
   **Environment Variables**:
   ```bash
   export ANTHROPIC_API_KEY="your-claude-key"
   export OPENAI_API_KEY="your-openai-key"
   export DEEPSEEK_API_KEY="your-deepseek-key"
   ```
   
   **Config File**: Edit `~/.doq-config.yaml`:
   ```yaml
   default_provider: claude
   providers:
     claude:
       api_key: "your-claude-key"
       model: "claude-3-sonnet-20240229"
     openai:
       api_key: "your-openai-key"
       model: "gpt-4"
     deepseek:
       api_key: "your-deepseek-key"
       model: "deepseek-chat"
   ```

3. **Start using**:
   ```bash
   doq "Explain what this code does" script.py
   ```

## Usage

### Basic Usage

```bash
# Simple query
doq "What is the capital of France?"

# Include files in query
doq "Review this code" main.py utils.py

# Use specific provider
doq --llm=openai "Explain this function" function.py

# Interactive mode (confirm before sending)
doq -i "Analyze this data" data.csv

# Dry run (preview without sending)
doq --dry-run "Test query" file.txt
```

### Advanced Features

#### Quoted Strings
```bash
# Multi-word queries
doq "This is a single query with spaces" additional args

# Escaped quotes
doq "Say \"hello world\" in Python"
```

#### File Handling
```bash
# Text files are automatically included with headers
doq "Explain this code" script.py
# Adds: ### ./script.py ###\n<file content>

# Binary files in hex format
doq "Analyze this binary" data.bin

# Large files prompt for confirmation
doq "Process this" large_file.txt
# Prompts: File large_file.txt is large (15.2MB). Include it? (y/N):
```

#### Provider-Specific Features

**Claude (supports file uploads)**:
```bash
doq --llm=claude "Review these files" *.py
# Files are sent as attachments when possible
```

**OpenAI & DeepSeek**:
```bash
doq --llm=openai "Analyze this" file.txt
# File content is embedded in the text query
```

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `-i` | Interactive mode - confirm before sending | `doq -i "query"` |
| `--llm=PROVIDER` | Choose provider (claude/openai/deepseek) | `doq --llm=openai "query"` |
| `--dry-run` | Show request details without sending | `doq --dry-run "query"` |

## Configuration

### Config File Location
- **Linux/Mac**: `~/.doq-config.yaml`
- **Windows**: `C:\Users\{username}\.doq-config.yaml`

### Default Configuration
```yaml
default_provider: claude
providers:
  claude:
    api_key: null
    model: "claude-3-sonnet-20240229"
    max_tokens: 4096
  openai:
    api_key: null
    model: "gpt-4"
    max_tokens: 4096
  deepseek:
    api_key: null
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    max_tokens: 4096
```

### Environment Variables
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key  
- `DEEPSEEK_API_KEY` - DeepSeek API key

Environment variables take precedence over config file values.

## Examples

### Code Review
```bash
doq "Please review this Python code for best practices" main.py utils.py
```

### Data Analysis
```bash
doq "Analyze this CSV data and provide insights" data.csv
```

### Multi-Provider Comparison
```bash
doq --llm=claude "Explain quantum computing" > claude_response.txt
doq --llm=openai "Explain quantum computing" > openai_response.txt
doq --llm=deepseek "Explain quantum computing" > deepseek_response.txt
```

### Interactive Workflow
```bash
doq -i "Help me debug this error" error.log traceback.txt
# Shows preview, asks for confirmation
# Streams response in real-time
```

### Binary File Analysis
```bash
doq "What type of file is this?" unknown_file.bin
# Automatically detects binary, converts to hex
# For large files, offers truncation options
```

## File Processing Details

### Text Files
- Automatically detected and included with headers
- Format: `### ./filename.ext ###\n<content>`
- Large files (>10MB) prompt for confirmation

### Binary Files
- Converted to hexadecimal representation
- Format: `### ./filename.bin (binary, 1024 bytes) ###\n<hex_data>`
- Large binary files offer truncation option
- Truncated format: `<first_1KB_hex>...{total_bytes}...{last_1KB_hex}`

### Provider File Support
- **Claude**: Supports direct file uploads (when available)
- **OpenAI/DeepSeek**: Files embedded in text query

## Error Handling

The CLI handles various error scenarios gracefully:

- **Missing API keys**: Clear error message with setup instructions
- **Network errors**: Informative error messages
- **File access errors**: Skip problematic files with warnings
- **Keyboard interrupts**: Clean exit with status code 130
- **Invalid providers**: List of available providers

## Development

### Setting Up Development Environment

```bash
git clone <repository-url>
cd doq
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=doq

# Run specific test file
pytest tests/test_parser.py
```

### Project Structure

```
doq/
├── doq/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── parser.py            # Argument parsing logic
│   └── providers/
│       ├── __init__.py      # Provider factory and base classes
│       ├── claude.py        # Claude/Anthropic provider
│       ├── openai.py        # OpenAI provider
│       └── deepseek.py      # DeepSeek provider
├── tests/
│   ├── __init__.py
│   ├── test_main.py         # CLI tests
│   ├── test_parser.py       # Parser tests
│   └── test_providers.py    # Provider tests
├── setup.py                 # Package configuration
└── README.md               # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please visit the project repository on GitHub.
