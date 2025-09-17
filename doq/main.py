"""Main CLI module for DOQ."""

import sys
from typing import List

from .parser import ArgumentParser
from .providers import ProviderFactory
from .validator import (ValidationLimits, create_validator_from_config,
                        suggest_optimization_tips)


def print_default_config():
    """Print default configuration in YAML format from example file."""
    try:
        # Get the path to the config example file
        import os
        from pathlib import Path

        # Get the package directory
        package_dir = Path(__file__).parent.parent
        config_file = package_dir / "doq-config-example.yaml"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(content)
        else:
            # Fallback to minimal config if file not found
            print("""# DOQ Default Configuration
# Save this as ~/.doq-config.yaml

# Default LLM provider
default_provider: claude

# Enhanced request validation limits
validation:
  max_files: 5
  max_text_lines: 1000
  max_binary_size_kb: 5
  max_total_size_mb: 10
  max_directory_depth: 5

# Set your API keys as environment variables:
# export ANTHROPIC_API_KEY="your-key"
# export OPENAI_API_KEY="your-key"
# export DEEPSEEK_API_KEY="your-key"
""")
    except Exception as e:
        # Fallback in case of any error
        print(f"# Error reading config file: {e}")
        print("""# DOQ Default Configuration
# Save this as ~/.doq-config.yaml

validation:
  max_files: 5
  max_text_lines: 1000
  max_binary_size_kb: 5
  max_total_size_mb: 10
""")

def print_help():
    """Print comprehensive help information with examples."""
    print("DOQ - Command Line Interface for Multiple LLM Providers")
    print("=" * 60)
    print()
    print("USAGE:")
    print("  doq [options] <query> [files...]")
    print()
    print("OPTIONS:")
    print("  -h, --help             Show this help message and exit")
    print("  -i                     Interactive mode (confirm before sending)")
    print("  --llm=PROVIDER         Choose LLM provider (claude, openai, deepseek)")
    print("  --dry-run              Show request details without sending")
    print("  --doq-default-config   Print default configuration and exit")
    print()
    print("BASIC EXAMPLES:")
    print('  doq "What is machine learning?"')
    print('  doq "Что такое машинное обучение?"  # Unicode/Cyrillic support')
    print("  doq explain script.py             # Simple command without quotes")
    print("  doq help                          # Single word commands")
    print()
    print("FILE PROCESSING:")
    print('  doq "Review this code" main.py utils.py')
    print("  doq analyze data.csv")
    print('  doq "Explain this function" function.py')
    print("  doq debug error.log")
    print()
    print("DIRECTORY PROCESSING:")
    print('  doq "Review project structure" .           # Current directory')
    print('  doq "Analyze all Python files" ./**        # Recursive')
    print('  doq "Check specific directory" ./src       # Specific directory')
    print('  doq "Review source files" ./src/*          # Directory contents')
    print('  doq "Python files only" ./src/**/*.py      # With file patterns')
    print()
    print("DIRECTORY PATTERNS:")
    print("  .              # Current directory (non-recursive)")
    print("  ./             # Current directory (non-recursive)")
    print("  ./*            # Current directory files")
    print("  ./**           # Current directory recursive")
    print("  ./src          # Specific subdirectory")
    print("  ./src/*        # Files in subdirectory")
    print("  ./src/**       # Subdirectory recursive")
    print("  src/           # Directory by name")
    print("  src/*          # Files in named directory")
    print("  src/**         # Named directory recursive")
    print()
    print("PROVIDER SELECTION:")
    print('  doq --llm=claude "Explain quantum computing"')
    print('  doq --llm=openai "What does this code do?" script.py')
    print('  doq --llm=deepseek "Analyze this data" data.json')
    print()
    print("INTERACTIVE MODE:")
    print('  doq -i "Review my code" *.py      # Confirm before sending')
    print("  doq -i analyze project/          # Interactive directory analysis")
    print()
    print("DRY RUN (PREVIEW):")
    print('  doq --dry-run "Test query" file.txt')
    print("  doq --dry-run explain script.py")
    print('  doq --dry-run "Analyze project" ./**')
    print()
    print("QUOTED VS UNQUOTED:")
    print("  # Use quotes for multi-word queries:")
    print('  doq "This is a complex query with spaces"')
    print("  # No quotes needed for single words:")
    print("  doq help")
    print("  doq explain file.py")
    print("  doq summarize document.txt")
    print()
    print("INTERNATIONAL SUPPORT:")
    try:
        print('  doq "解释人工智能的基本概念"        # Chinese')
        print('  doq "اشرح مفهوم الذكاء الاصطناعي"    # Arabic')
        print('  doq "Объясни принципы ML"           # Russian')
    except UnicodeEncodeError:
        # Fallback for Windows console with limited encoding
        print('  doq "International text support"     # Unicode/UTF-8 support')
        print('  doq "текст на русском"               # Cyrillic example')
        print('  doq "中文示例"                        # Chinese example')
    print()
    print("VALIDATION & LIMITS:")
    print("  DOQ validates requests before sending to prevent large token usage:")
    print("  • File count limits (default: 5 files)")
    print("  • File size limits (text: 1000 lines, binary: 5KB)")
    print("  • Total request size limits (default: 10MB)")
    print("  • Directory depth limits (default: 5 levels)")
    print("  • Token estimation with cost warnings")
    print()
    print("CONFIGURATION:")
    print("  Set API keys via environment variables:")
    print("    ANTHROPIC_API_KEY=your-key")
    print("    OPENAI_API_KEY=your-key")
    print("    DEEPSEEK_API_KEY=your-key")
    print()
    print("  Configure limits in ~/.doq-config.yaml:")
    print("    validation:")
    print("      max_files: 10")
    print("      max_text_lines: 2000")
    print("      max_binary_size_kb: 10")
    print("      max_total_size_mb: 20")
    print("      max_directory_depth: 8")
    print()
    print("  Generate default config:")
    print("    doq --doq-default-config > ~/.doq-config.yaml")
    print()
    print("OPTIMIZATION TIPS:")
    print("  • Use --dry-run to preview requests before sending")
    print("  • Start with specific files rather than whole directories")
    print("  • Use interactive mode (-i) for large requests")
    print("  • Focus queries on specific aspects rather than general reviews")
    print("  • Exclude test files and documentation unless needed")
    print()
    print("For more information, visit: https://github.com/ko10ok/do")

def print_dry_run_info(request_structure, validation_result=None):
    """Print detailed information about the request in dry-run mode."""
    print("=" * 60)
    print("DRY RUN - Request Information")
    print("=" * 60)
    print(f"Provider: {request_structure.provider}")
    print(f"Interactive mode: {request_structure.interactive}")
    print(f"Text query length: {len(request_structure.text_query)} characters")
    print()

    if request_structure.files:
        print("Files to be included:")
        for file_info in request_structure.files:
            print(f"  - {file_info.path}")
            print(f"    Size: {file_info.size} bytes")
            print(f"    Binary: {file_info.is_binary}")
            print(f"    Include mode: {file_info.include_mode}")
        print()

    # Show validation results if available
    if validation_result:
        print("VALIDATION RESULTS:")
        if validation_result.warnings:
            print("⚠️  Warnings:")
            for warning in validation_result.warnings:
                print(f"  • {warning}")

        if validation_result.errors:
            print("❌ Errors:")
            for error in validation_result.errors:
                print(f"  • {error}")

        print(f"\n📊 Summary:")
        print(f"  • Files: {validation_result.file_count} ({validation_result.text_files} text, {validation_result.binary_files} binary)")
        print(f"  • Total size: {validation_result.total_size_bytes / (1024*1024):.1f}MB")
        print()

    print("Raw arguments:")
    print(" ".join(f'"{arg}"' if " " in arg else arg for arg in request_structure.raw_args))
    print()

    print("Final query text:")
    print("-" * 40)
    print(request_structure.text_query)
    print("-" * 40)


def _has_directory_patterns(raw_args):
    """Check if any of the raw arguments represent directory patterns."""
    directory_patterns = [
        ".", "./", "./*", "./**"
    ]

    for arg in raw_args:
        # Skip option flags
        if arg.startswith("-"):
            continue

        # Check for direct directory patterns
        if arg in directory_patterns:
            return True

        # Check for patterns like ./src, ./src/*, ./src/**, src/, src/*, src/**
        if (arg.startswith("./") or
            arg.endswith("/") or
            arg.endswith("/*") or
            arg.endswith("/**")):
            return True

        # Check if it's a plain directory path
        try:
            from pathlib import Path
            path = Path(arg)
            if path.exists() and path.is_dir():
                return True
        except (OSError, ValueError):
            pass

    return False


def _generate_directory_tree(files):
    """Generate a visual directory tree from the list of files."""
    import os
    from pathlib import Path

    if not files:
        return "No files found."

    # Build a tree structure
    tree = {}

    for file_info in files:
        path = Path(file_info.path)
        parts = path.parts

        current = tree
        for part in parts[:-1]:  # All parts except the filename
            if part not in current:
                current[part] = {}
            current = current[part]

        # Add the file
        filename = parts[-1]
        current[filename] = {
            'size': file_info.size,
            'is_binary': file_info.is_binary,
            'is_file': True
        }

    # Generate the tree visualization
    def format_tree(node, prefix="", is_last=True):
        lines = []
        items = list(node.items())

        for i, (name, content) in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "

            if content.get('is_file', False):
                # It's a file
                size_str = _format_file_size(content['size'])
                file_type = "📦" if content['is_binary'] else "📄"
                lines.append(f"{prefix}{current_prefix}{file_type} {name} ({size_str})")
            else:
                # It's a directory
                lines.append(f"{prefix}{current_prefix}📁 {name}/")

                # Add subdirectory contents
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                sublines = format_tree(content, next_prefix, is_last_item)
                lines.extend(sublines)

        return lines

    tree_lines = format_tree(tree)
    return "\n".join(tree_lines)


def _format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def main(args: List[str] = None):
    """Main entry point for DOQ CLI."""
    # Use provided args or get from sys.argv
    if args is None:
        args = sys.argv[1:]

    # Check for default config flag first (before parsing)
    if "--doq-default-config" in args:
        print_default_config()
        return 0

    # Check for help flags first
    if not args or "-h" in args or "--help" in args:
        if "-h" in args or "--help" in args:
            print_help()
            return 0

        # Show brief usage if no args
        print("Usage: doq [options] <query> [files...]")
        print()
        print("Options:")
        print("  -h, --help             Show help message with examples")
        print("  -i                     Interactive mode (confirm before sending)")
        print("  --llm=PROVIDER         Choose LLM provider (claude, openai, deepseek)")
        print("  --dry-run              Show request details without sending")
        print("  --doq-default-config   Print default configuration and exit")
        print()
        print("Examples:")
        print('  doq "Explain this code" script.py')
        print('  doq --llm=openai "What does this do?" file.txt')
        print('  doq -i "Review my code" *.py')
        print('  doq --dry-run "Test query" data.json')
        print("  doq analyze .                    # Current directory")
        print("  doq review ./**                  # Recursive directory")
        print()
        print("Configuration:")
        print("  doq --doq-default-config > ~/.doq-config.yaml")
        print()
        print("Use 'doq --help' for more detailed examples and information.")
        return 1

    try:
        # Parse arguments
        parser = ArgumentParser()
        request_structure = parser.parse_args(args)

        # Create validator from config
        validator = create_validator_from_config()

        # Validate request
        validation_result = validator.validate_request_enhanced(
            request_structure.files,
            request_structure.text_query,
            interactive=request_structure.interactive
        )

        # Handle dry-run mode
        if request_structure.dry_run:
            print_dry_run_info(request_structure, validation_result)

            if validation_result.warnings or validation_result.errors:
                print("\nOPTIMIZATION SUGGESTIONS:")
                suggest_optimization_tips()

            return 0

        # Check validation results
        if not validation_result.is_valid:
            print("❌ Request validation failed:")
            for error in validation_result.errors:
                print(f"  • {error}")
            print("\nRequest cannot be processed. Please address the errors above.")
            return 1

        # Handle interactive mode or show warnings
        if request_structure.interactive:
            # Show validation summary for interactive mode
            if validation_result.warnings:
                print("⚠️  Request validation warnings:")
                for warning in validation_result.warnings:
                    print(f"  • {warning}")

            print(f"\n📊 Request summary:")
            print(f"  • Files: {validation_result.file_count} ({validation_result.text_files} text, {validation_result.binary_files} binary)")
            print(f"  • Total size: {validation_result.total_size_bytes / (1024*1024):.1f}MB")

            response = input("\nDo you want to proceed? (y/N): ")
            if not response.lower().startswith('y'):
                print("Request cancelled.")
                return 0
        elif validation_result.warnings and len(validation_result.warnings) > 1:
            # Only show warnings prompt for multiple warnings in non-interactive mode
            print("⚠️  Request validation warnings:")
            for warning in validation_result.warnings:
                print(f"  • {warning}")

            print(f"\n📊 Request summary:")
            print(f"  • Files: {validation_result.file_count} ({validation_result.text_files} text, {validation_result.binary_files} binary)")
            print(f"  • Total size: {validation_result.total_size_bytes / (1024*1024):.1f}MB")

            response = input("\nDo you want to proceed? (y/N): ")
            if not response.lower().startswith('y'):
                print("Request cancelled.")
                return 0

        # Create provider and send request
        factory = ProviderFactory()
        provider = factory.create_provider(request_structure.provider)

        # Stream response
        try:
            for chunk in provider.send_request(request_structure):
                print(chunk, end='', flush=True)
            print()  # Final newline

        except KeyboardInterrupt:
            print("\nRequest interrupted by user.")
            return 130

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
