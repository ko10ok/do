# DoQue - Command Line Interface for Multiple LLM Providers

A powerful command-line interface for interacting with various Large Language Model (LLM) providers including Claude (Anthropic), ChatGPT (OpenAI), and DeepSeek.

## Features

- **Multiple LLM Providers**: Support for Claude, OpenAI, and DeepSeek
- **Cross-Platform Support**: Native Unicode handling on Windows and Unix-like systems
- **Enhanced Directory Processing**: Smart directory scanning with configurable patterns
- **Advanced File Processing**: Automatically detect and include text/binary files with validation
- **Request Validation**: Intelligent limits and warnings to prevent large token usage
- **Smart Argument Parsing**: Handle quoted strings, file paths, and special parameters
- **Interactive Mode**: Confirm requests before sending with detailed validation
- **Dry Run Mode**: Preview requests with validation results
- **Streaming Responses**: Real-time response display
- **Configurable**: Comprehensive configuration via YAML file or environment variables

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

2. **Set your API key**:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   # or
   export OPENAI_API_KEY="your-api-key"
   # or
   export DEEPSEEK_API_KEY="your-api-key"
   ```

3. **Basic usage**:
   ```bash
   doq "What is machine learning?"
   doq explain script.py
   doq "Review this code" main.py utils.py
   ```

## Usage Examples

### Basic Queries

```bash
# Simple queries (no quotes needed for single words)
doq help
doq explain file.py
doq summarize document.txt

# Multi-word queries (use quotes)
doq "What is artificial intelligence?"
doq "Explain how this algorithm works" algorithm.py
```

### Directory Processing

```bash
# Current directory (non-recursive)
doq "Review project structure" .
doq analyze ./

# Recursive directory scanning
doq "Analyze all Python files" ./**
doq "Review entire project" ./**

# Specific directories
doq "Check source code" ./src
doq "Review source files" ./src/*
doq "Deep analysis of src" ./src/**

# Named directories
doq "Analyze data processing" data/
doq "Review all data files" data/*
doq "Deep scan of data directory" data/**
```

### File Processing

```bash
# Single files
doq "Explain this function" main.py
doq "What does this script do?" script.py

# Multiple files
doq "Review these modules" main.py utils.py config.py
doq "Compare implementations" old_version.py new_version.py

# Mixed files and directories
doq "Analyze project" main.py ./src/* ./tests/
```

### Provider Selection

```bash
# Choose specific LLM provider
doq --llm=claude "Explain quantum computing"
doq --llm=openai "What does this code do?" script.py
doq --llm=deepseek "Analyze this data" data.json
```

### Interactive Mode

```bash
# Confirm before sending (especially useful for large requests)
doq -i "Review my entire codebase" ./**
doq -i "Analyze all Python files" ./src/**
```

### Dry Run Mode

```bash
# Preview request without sending
doq --dry-run "Test query" file.txt
doq --dry-run "Analyze project" ./**
doq --dry-run explain script.py
```

### International Support

```bash
# Unicode and international text fully supported
doq "Что такое машинное обучение?"      # Russian
doq "解释人工智能的基本概念"              # Chinese
doq "اشرح مفهوم الذكاء الاصطناعي"        # Arabic
```

## Directory Patterns

DOQ supports flexible directory patterns for scanning files:

| Pattern | Description | Example |
|---------|-------------|---------|
| `.` | Current directory (non-recursive) | `doq analyze .` |
| `./` | Current directory (non-recursive) | `doq review ./` |
| `./*` | Current directory files | `doq check ./*` |
| `./**` | Current directory recursive | `doq scan ./**` |
| `./src` | Specific subdirectory | `doq analyze ./src` |
| `./src/*` | Files in subdirectory | `doq review ./src/*` |
| `./src/**` | Subdirectory recursive | `doq scan ./src/**` |
| `src/` | Directory by name | `doq analyze src/` |
| `src/*` | Files in named directory | `doq review src/*` |
| `src/**` | Named directory recursive | `doq scan src/**` |

## Request Validation

DOQ includes intelligent validation to prevent excessive token usage and costs:

### Default Limits
- **Files**: Maximum 5 files (configurable)
- **Text files**: Maximum 1,000 lines per file
- **Binary files**: Maximum 5KB per file
- **Total size**: Maximum 10MB per request
- **Directory depth**: Maximum 5 levels of recursion

### Validation Features
- **Token estimation**: Approximate token count and cost estimation
- **File type analysis**: Smart detection of redundant or test files
- **Directory structure analysis**: Warnings for scattered or deep structures
- **Query optimization**: Suggestions for vague or overly broad queries
- **Interactive confirmation**: Detailed validation results in interactive mode

### Configuration

Create `~/.doq-config.yaml` to customize limits:

```yaml
validation:
  max_files: 10
  max_text_lines: 2000
  max_binary_size_kb: 10
  max_total_size_mb: 20
  max_directory_depth: 8
  
cost_control:
  warn_token_threshold: 50000
  block_token_threshold: 150000
  show_cost_estimates: true
```

## Command Line Options

```bash
doq [OPTIONS] <query> [files...]
```

### Options

- `-h, --help`: Show detailed help with examples
- `-i`: Interactive mode (confirm before sending)
- `--llm=PROVIDER`: Choose LLM provider (claude, openai, deepseek)
- `--dry-run`: Show request details without sending

### Examples with Options

```bash
# Get help
doq --help

# Interactive mode with validation
doq -i "Review all my code" ./**

# Dry run to preview request
doq --dry-run "Analyze project structure" .

# Specific provider
doq --llm=openai "Explain this algorithm" algorithm.py

# Combined options
doq -i --llm=claude --dry-run "Large analysis" ./**
```

## Configuration

### Environment Variables

Set your API keys:

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
```

### Configuration File

Create `~/.doq-config.yaml`:

```yaml
# Default provider
default_provider: claude

# Provider settings
providers:
  claude:
    model: "claude-3-sonnet-20240229"
    max_tokens: 4096
  openai:
    model: "gpt-4"
    max_tokens: 4096
  deepseek:
    model: "deepseek-chat"
    max_tokens: 4096

# Validation limits
validation:
  max_files: 10
  max_text_lines: 2000
  max_binary_size_kb: 10
  max_total_size_mb: 20
  max_directory_depth: 8

# Patterns to ignore during directory scanning
  ignore_patterns:
    - "__pycache__"
    - ".git"
    - "node_modules"
    - ".venv"
    - "*.pyc"
    - "*.log"
    - "build"
    - "dist"
```

## Advanced Usage

### Token Optimization

For large projects, use these strategies to reduce token usage:

1. **Start specific**: Begin with specific files rather than entire directories
2. **Use dry-run**: Preview requests with `--dry-run` to see what will be included
3. **Focus queries**: Ask specific questions rather than broad "analyze" requests
4. **Exclude irrelevant files**: Configure ignore patterns to skip tests, docs, logs
5. **Use interactive mode**: Review validation results before sending

### Best Practices

1. **Directory scanning**: Start with `.` (current directory) before using `./**` (recursive)
2. **File selection**: Use specific file patterns when possible
3. **Query focus**: Be specific about what you want to know
4. **Validation**: Pay attention to warnings about file count and token usage
5. **Configuration**: Customize limits based on your typical usage patterns

### Performance Tips

- Use `--dry-run` to preview large requests
- Configure appropriate limits in `~/.doq-config.yaml`
- Use interactive mode (`-i`) for requests with many files
- Monitor token estimates to optimize future requests
- Exclude unnecessary files with ignore patterns

## Troubleshooting

### Common Issues

1. **Unicode issues on Windows**: Use PowerShell instead of Command Prompt
2. **Large token usage**: Use `--dry-run` to preview and reduce file count
3. **Too many files**: Configure higher limits or use more specific patterns
4. **Permission errors**: Ensure you have read access to directories
5. **API key errors**: Verify environment variables are set correctly

### Debug Information

Use `--dry-run` to see:
- Files that will be included
- Validation warnings and errors
- Token estimates
- Request structure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

[Add license information]

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/docs
