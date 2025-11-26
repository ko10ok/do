# DoQue - Command Line Interface for Multiple LLM Providers

A powerful command-line interface for interacting with various Large Language Model (LLM) providers including Claude (Anthropic), ChatGPT (OpenAI), and DeepSeek.

## What is DoQue?

DoQue is a universal CLI tool that allows you to send queries to different AI providers while automatically including files, directories, and web content for context. It handles the complexity of file processing, validation, and formatting so you can focus on getting answers from AI about your code, documents, or any other content.

### Key Capabilities

- **Multi-Provider Support**: Switch between Claude, OpenAI, and DeepSeek with a simple flag
- **Smart File Processing**: Automatically analyze single files, multiple files, or entire directory structures
- **Web Content Analysis**: Fetch and analyze content from URLs, GitHub repositories, APIs, and code snippets
- **Intelligent Validation**: Built-in limits and warnings to prevent excessive token usage and costs
- **Cross-Platform**: Native Unicode support on Windows, macOS, and Linux

## Installation

```bash
pip install doque
```

## Quick Setup

Set your API key for at least one provider:

```bash
# Choose one or more
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

## Basic Usage

### Simple Questions
```bash
# No quotes needed for simple concepts
doq What is machine learning?
doq Explain recursion
doq Define polymorphism
```

### File Analysis
```bash
# Single files
doq Review this code script.py
doq Explain this function utils.py
doq Debug this file error.log

# Multiple files
doq Compare these implementations old.py new.py
doq Analyze these modules auth.py user.py
```

### Directory Analysis
```bash
# Current directory overview
doq Review project structure .

# Specific directory
doq Analyze data files ./data
doq Review source code ./src/*

# Recursive analysis with patterns
doq "Check all Python code" ./**/*.py
```

### Choose Your AI Provider
```bash
# Claude (default) - Great for code analysis
doq Explain this algorithm algorithm.py

# OpenAI - Excellent for explanations
doq --llm=openai Debug this code buggy.py

# DeepSeek - Good for optimization
doq --llm=deepseek Optimize this function slow_function.py
```

## Core Features

### Request Validation

DoQue includes intelligent validation to prevent excessive costs:

**Default Limits:**
- Maximum 10 files per request
- Maximum 10,000 lines per text file
- Maximum 10KB per binary file
- Maximum 1MB total request size
- Maximum 8 directory levels

**Smart-kind Features:**
- Approximate token estimation with cost warnings (estimates may vary from actual usage)
- Automatic detection of test files and redundant content
- Interactive confirmation for large requests
- Dry-run mode to preview before sending

### Command Options

```bash
doq [OPTIONS] <query> [files...]
```

**Available Options:**
- `-h, --help`: Show detailed help
- `-i`: Interactive mode (confirm before sending)
- `--llm=PROVIDER`: Choose provider (claude, openai, deepseek)
- `--dry-run`: Preview request without sending
- `--doq-default-config`: Generate configuration file

### Essential Examples

```bash
# Get help
doq --help

# Preview large requests
doq --dry-run Review all code ./**

# Interactive mode for safety
doq -i Comprehensive analysis ./**

# Combine options
doq -i --llm=openai --dry-run Analyze project .
```

## Configuration

Create `~/.doq-config.yaml` to customize behavior:

```yaml
# Default provider
default_provider: claude

# Validation limits
validation:
  max_files: 10
  max_text_lines: 10000
  max_binary_size_kb: 10
  max_total_size_mb: 1
  max_directory_depth: 8
  ignore_patterns:
    - "__pycache__"
    - ".git"
    - "node_modules"
    - "*.pyc"
    - "*.log"

# Cost control
cost_control:
  warn_token_threshold: 20000
  block_token_threshold: 50000
  show_cost_estimates: true
```

Generate default config:
```bash
doq --doq-default-config > ~/.doq-config.yaml
```

## Best Practices

1. **Start Small**: Begin with specific files before analyzing entire directories
2. **Use Dry Run**: Preview large requests with `--dry-run`
3. **Be Specific**: Ask focused questions rather than broad "analyze everything"
4. **Monitor Tokens**: Pay attention to validation warnings
5. **Configure Limits**: Adjust settings based on your usage patterns

## Troubleshooting

**Common Issues:**
- **Unicode on Windows**: Use PowerShell instead of Command Prompt
- **Large token usage**: Use `--dry-run` to preview and reduce scope
- **Too many files**: Use more specific patterns or increase limits
- **API errors**: Verify environment variables are set correctly

**Debug Information:**
Use `--dry-run` to see files included, validation results, and token estimates.

## Advanced Usage

### Advanced File Processing

```bash
# Single file deep analysis
doq Find potential bugs in this code security.py

# Multiple files with context
doq Compare these implementations v1/processor.py v2/processor.py

# Mixed files and directories
doq Analyze the entire authentication system auth/ user.py session.py
```

### URL and Web Content Analysis

```bash
# Web pages
doq Summarize this article https://example.com/article.html

# GitHub files
doq Explain this implementation https://raw.githubusercontent.com/user/repo/main/file.py

# API endpoints
doq Analyze this API response https://api.github.com/users/octocat

# Code snippets
doq What does this script do https://gist.githubusercontent.com/user/id/raw/script.js
```

### Directory Processing Patterns

DoQue supports flexible directory patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| `.` | Current directory (non-recursive) | `doq Review structure .` |
| `./**` | Current directory recursive | `doq Deep scan ./**` |
| `./src` | Specific subdirectory | `doq Review source ./src` |
| `./src/**` | Subdirectory recursive | `doq Deep source scan ./src/**` |
| `src/**` | Named directory recursive | `doq Analyze source src/**` |

```bash
# Current directory (non-recursive)
doq Review project architecture .

# Recursive scanning
doq Deep analysis of all code ./**

# Specific patterns
doq Review all Python files recursively ./**/*.py

# Named directory recursive
doq Deep scan of source directory ./src/**

# Multi-directory analysis
doq Review entire backend ./src/** ./api/** ./models/**
```

### Provider-Specific Usage

```bash
# Claude for architecture analysis
doq --llm=claude Analyze the architecture of this system ./src/**

# OpenAI for documentation
doq --llm=openai Generate documentation for this API api.py

# DeepSeek for optimization
doq --llm=deepseek Find performance bottlenecks ./src/**
```

### Interactive and Validation Modes

```bash
# Interactive mode
doq -i Comprehensive code review ./**

# Dry run preview
doq --dry-run Check what files will be included ./src/**

# Combined modes for safety
doq -i --dry-run --llm=claude Large project analysis ./**
```

### International and Unicode Support

```bash
# Unicode queries (quotes required for special characters)
doq "Что такое машинное обучение?"              # Russian
doq "解释人工智能的基本概念"                     # Chinese
doq "اشرح مفهوم الذكاء الاصطناعي"               # Arabic

# Mixed language analysis
doq Analyze this multilingual codebase international_app/
```

### Token Optimization Strategies

For large projects:

1. **Start Specific**: Begin with individual files rather than entire directories
2. **Use Patterns**: Target specific file types with `./**/*.py` instead of `./**`
3. **Preview First**: Always use `--dry-run` for large requests
4. **Exclude Irrelevant**: Configure ignore patterns for tests, logs, build files
5. **Interactive Mode**: Use `-i` for requests with validation warnings
6. **Focus Queries**: Ask specific questions rather than broad analysis requests

## Environment Variables

```bash
# API Keys
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Development

DoQue supports Python 3.10+ (tested on 3.10-3.14).

**Setup:**
```bash
# Create virtual environment
python3.14 -m venv venv314
source venv314/bin/activate  # Windows: venv314\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run tests (137 should pass)
pytest tests/ -v

# Install in editable mode
pip install -e .
```

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: https://github.com/ko10ok/do/issues
- Documentation: https://github.com/ko10ok/do
