# DOQ - Command Line Interface for Multiple LLM Providers

A powerful command-line interface for interacting with various Large Language Model (LLM) providers including Claude (Anthropic), ChatGPT (OpenAI), and DeepSeek.

## Features

- **Multiple LLM Providers**: Support for Claude, OpenAI, and DeepSeek
- **Cross-Platform Support**: Native Unicode handling on Windows and Unix-like systems
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

### Platform-Specific Commands

After installation, the following commands will be available:

**Windows**:
```powershell
doq "your query"  # PowerShell script with Unicode support
```

**Unix/Linux/macOS**:
```bash
doq "your query"  # Native script
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
   # Windows PowerShell
   $env:ANTHROPIC_API_KEY="your-claude-key"
   $env:OPENAI_API_KEY="your-openai-key"
   $env:DEEPSEEK_API_KEY="your-deepseek-key"
   
   # Unix/Linux/macOS
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
# Simple query (works with Unicode/Cyrillic on all platforms)
doq "What is the capital of France?"
doq "Что такое машинное обучение?"

# Simple queries without quotes (for single words)
doq help
doq explain
doq summarize

# Include files in query
doq "Review this code" main.py utils.py
doq analyze main.py utils.py

# Use specific provider
doq --llm=openai "Explain this function" function.py
doq --llm=openai explain function.py

# Interactive mode (confirm before sending)
doq -i "Analyze this data" data.csv
doq -i analyze data.csv

# Dry run (preview without sending)
doq --dry-run "Test query" file.txt
doq --dry-run test file.txt
```

### Advanced Features

#### Quoted Strings and Command Syntax

**When to use quotes:**
```bash
# Multi-word queries require quotes
doq "This is a single query with spaces" additional args

# Queries with special characters
doq "Say \"hello world\" in Python"
doq "What's the difference between == and === ?"
```

**When quotes are optional:**
```bash
# Single words don't need quotes
doq help
doq explain script.py
doq summarize document.txt

# Simple commands with files
doq analyze data.csv
doq review code.py
doq debug error.log
```

**Escaped quotes:**
```bash
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
# Or without quotes for simple commands
doq review main.py utils.py
```

### Data Analysis
```bash
doq "Analyze this CSV data and provide insights" data.csv
# Simplified version
doq analyze data.csv
```

### Simple Commands Without Quotes
```bash
# Basic file operations
doq explain script.py
doq summarize document.txt
doq debug error.log
doq optimize code.py
doq translate text.txt

# Quick help and information
doq help
doq version
doq status
```

### Multi-Provider Comparison
```bash
doq --llm=claude "Explain quantum computing" > claude_response.txt
doq --llm=openai "Explain quantum computing" > openai_response.txt
doq --llm=deepseek "Explain quantum computing" > deepseek_response.txt

# Or with simple commands
doq --llm=claude explain quantum.txt > claude_response.txt
doq --llm=openai explain quantum.txt > openai_response.txt
doq --llm=deepseek explain quantum.txt > deepseek_response.txt
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

## Unicode and International Support

DOQ provides native Unicode support across all platforms, allowing you to use queries in any language including Cyrillic, Chinese, Arabic, and other non-Latin scripts.

### Examples with International Text

```bash
# Russian/Cyrillic
doq "Объясни принципы машинного обучения"

# Chinese
doq "解释人工智能的基本概念"

# Arabic  
doq "اشرح مفهوم الذكاء الاصطناعي"

# Mixed languages
doq "Compare ML algorithms: что лучше - нейронные сети или деревья решений?"
```

### Platform-Specific Unicode Handling

**Windows**:
- Uses PowerShell's native Unicode support
- Automatically configures console encoding to UTF-8
- Handles Cyrillic and other non-ASCII characters correctly

**Unix/Linux/macOS**:
- Leverages system's native UTF-8 support
- No additional configuration needed
- Works seamlessly with international input methods

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
│   ├── __main__.py          # Simple module entry point
│   ├── main.py              # Simplified CLI entry point
│   ├── parser.py            # Argument parsing logic
│   └── providers/
│       ├── __init__.py      # Provider factory and base classes
│       ├── claude.py        # Claude/Anthropic provider
│       ├── openai.py        # OpenAI provider
│       └── deepseek.py      # DeepSeek provider
├── scripts/
│   ├── doq.ps1              # Windows PowerShell script with Unicode support
│   └── doq_unix             # Unix/Linux/macOS simple script
├── tests/
│   ├── __init__.py
│   ├── test_main.py         # CLI tests
│   ├── test_parser.py       # Parser tests
│   └── test_providers.py    # Provider tests
├── setup.py                 # Platform-aware package configuration
└── README.md               # This file
```

### Platform-Specific Implementation

**Windows (`scripts/doq.ps1`)**:
- PowerShell script with native Unicode/UTF-8 handling
- Proper console encoding setup for Cyrillic and other non-ASCII characters
- Seamless integration with Windows PowerShell environment

**Unix/Linux/macOS (`scripts/doq_unix`)**:
- Simple Python script without complex Unicode handling
- Relies on system's native UTF-8 support
- Lightweight implementation for Unix-like systems

**Installation Process**:
- `setup.py` automatically detects the platform during installation
- Installs the appropriate script for the target platform
- Creates unified `doq` command that works correctly on all systems
