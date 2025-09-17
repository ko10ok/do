"""Main CLI module for DOQ."""

import sys
from typing import List
from .parser import ArgumentParser
from .providers import ProviderFactory

def print_help():
    """Print comprehensive help information with examples."""
    print("DOQ - Command Line Interface for Multiple LLM Providers")
    print("=" * 60)
    print()
    print("USAGE:")
    print("  doq [options] <query> [files...]")
    print()
    print("OPTIONS:")
    print("  -h, --help         Show this help message and exit")
    print("  -i                 Interactive mode (confirm before sending)")
    print("  --llm=PROVIDER     Choose LLM provider (claude, openai, deepseek)")
    print("  --dry-run          Show request details without sending")
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
    print("PROVIDER SELECTION:")
    print('  doq --llm=claude "Explain quantum computing"')
    print('  doq --llm=openai "What does this code do?" script.py')
    print('  doq --llm=deepseek "Analyze this data" data.json')
    print()
    print("INTERACTIVE MODE:")
    print('  doq -i "Review my code" *.py      # Confirm before sending')
    print("  doq -i analyze project/")
    print()
    print("DRY RUN (PREVIEW):")
    print('  doq --dry-run "Test query" file.txt')
    print("  doq --dry-run explain script.py")
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
    print('  doq "解释人工智能的基本概念"        # Chinese')
    print('  doq "اشرح مفهوم الذكاء الاصطناعي"    # Arabic')
    print('  doq "Объясни принципы ML"           # Russian')
    print()
    print("CONFIGURATION:")
    print("  Set API keys via environment variables:")
    print("    ANTHROPIC_API_KEY=your-key")
    print("    OPENAI_API_KEY=your-key")
    print("    DEEPSEEK_API_KEY=your-key")
    print()
    print("  Or use config file: ~/.doq-config.yaml")
    print()
    print("For more information, visit: https://github.com/ko10ok/do")

def print_dry_run_info(request_structure):
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

    print("Raw arguments:")
    print(" ".join(f'"{arg}"' if " " in arg else arg for arg in request_structure.raw_args))
    print()

    print("Final query text:")
    print("-" * 40)
    print(request_structure.text_query)
    print("-" * 40)


def main(args: List[str] = None):
    """Main entry point for DOQ CLI."""
    # Use provided args or get from sys.argv
    if args is None:
        args = sys.argv[1:]

    # Check for help flags first
    if not args or "-h" in args or "--help" in args:
        if "-h" in args or "--help" in args:
            print_help()
            return 0

        # Show brief usage if no args
        print("Usage: doq [options] <query> [files...]")
        print()
        print("Options:")
        print("  -h, --help         Show help message with examples")
        print("  -i                 Interactive mode (confirm before sending)")
        print("  --llm=PROVIDER     Choose LLM provider (claude, openai, deepseek)")
        print("  --dry-run          Show request details without sending")
        print()
        print("Examples:")
        print('  doq "Explain this code" script.py')
        print('  doq --llm=openai "What does this do?" file.txt')
        print('  doq -i "Review my code" *.py')
        print('  doq --dry-run "Test query" data.json')
        print()
        print("Use 'doq --help' for more detailed examples and information.")
        return 1

    try:
        # Parse arguments
        parser = ArgumentParser()
        request_structure = parser.parse_args(args)

        # Handle dry-run mode
        if request_structure.dry_run:
            print_dry_run_info(request_structure)
            return 0

        # Handle interactive mode
        if request_structure.interactive:
            print("=" * 60)
            print("INTERACTIVE MODE - Request Preview")
            print("=" * 60)
            print(f"Provider: {request_structure.provider}")
            print(f"Query: {request_structure.text_query[:200]}{'...' if len(request_structure.text_query) > 200 else ''}")
            if request_structure.files:
                print(f"Files: {len(request_structure.files)} file(s)")
            print()

            response = input("Send this request? (y/N): ")
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
