"""Request validation and limits checking module."""

import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class ValidationLimits:
    """Configuration for request validation limits."""
    max_files: int = 5
    max_text_lines: int = 1000
    max_binary_size_kb: int = 5
    max_total_size_mb: int = 10
    max_directory_depth: int = 5
    warn_large_directories: bool = True
    auto_skip_common_ignores: bool = True

    # Common files/directories to ignore
    ignore_patterns: List[str] = None

    def __post_init__(self):
        if self.ignore_patterns is None:
            self.ignore_patterns = [
                "__pycache__", ".git", ".svn", ".hg", "node_modules",
                ".venv", "venv", ".env", "*.pyc", "*.pyo", "*.pyd",
                ".DS_Store", "Thumbs.db", "*.log", "*.tmp", "*.temp",
                ".pytest_cache", ".coverage", "*.egg-info"
            ]


@dataclass
class ValidationResult:
    """Result of request validation."""
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    file_count: int
    total_size_bytes: int
    binary_files: int
    text_files: int
    skipped_files: List[str]


class RequestValidator:
    """Validates and checks request limits before sending to LLM."""

    def __init__(self, limits: Optional[ValidationLimits] = None):
        self.limits = limits or ValidationLimits()

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> 'RequestValidator':
        """Create validator from configuration file."""
        if config_path is None:
            config_path = os.path.expanduser("~/.doq-config.yaml")

        limits = ValidationLimits()

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}

                validation_config = config.get('validation', {})
                if validation_config:
                    # Update limits from config
                    for key, value in validation_config.items():
                        if hasattr(limits, key):
                            setattr(limits, key, value)
            except Exception as e:
                print(f"Warning: Could not load config from {config_path}: {e}", file=sys.stderr)

        return cls(limits)

    def validate_request(self, files: List, text_query: str) -> ValidationResult:
        """Validate complete request before sending to LLM."""
        warnings = []
        errors = []
        skipped_files = []

        # Count files and sizes
        file_count = len(files)
        total_size = 0
        binary_files = 0
        text_files = 0

        for file_info in files:
            total_size += file_info.size
            if file_info.is_binary:
                binary_files += 1
            else:
                text_files += 1

        # Check file count limit
        if file_count > self.limits.max_files:
            warnings.append(f"Large number of files: {file_count} files (limit: {self.limits.max_files})")

        # Check total size limit
        total_size_mb = total_size / (1024 * 1024)
        if total_size_mb > self.limits.max_total_size_mb:
            warnings.append(f"Large total size: {total_size_mb:.1f}MB (limit: {self.limits.max_total_size_mb}MB)")

        # Check individual file limits
        for file_info in files:
            if file_info.is_binary:
                size_kb = file_info.size / 1024
                if size_kb > self.limits.max_binary_size_kb:
                    warnings.append(f"Large binary file: {file_info.path} ({size_kb:.1f}KB)")
            else:
                # Count lines for text files
                if file_info.content:
                    lines = file_info.content.count('\n')
                    if lines > self.limits.max_text_lines:
                        warnings.append(f"Large text file: {file_info.path} ({lines} lines)")

        # Check text query size
        query_lines = text_query.count('\n') + 1
        if query_lines > 100:  # Reasonable limit for query itself
            warnings.append(f"Large query text: {query_lines} lines")

        # Additional token consumption checks
        estimated_tokens = self._estimate_tokens(text_query, files)
        if estimated_tokens > 50000:  # ~50k tokens warning
            warnings.append(f"High estimated token count: ~{estimated_tokens:,} tokens")
        elif estimated_tokens > 100000:  # ~100k tokens error
            errors.append(f"Extremely high token count: ~{estimated_tokens:,} tokens - consider reducing request size")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            errors=errors,
            file_count=file_count,
            total_size_bytes=total_size,
            binary_files=binary_files,
            text_files=text_files,
            skipped_files=skipped_files
        )

    def _estimate_tokens(self, text_query: str, files: List) -> int:
        """Estimate total token count for the request."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        # Binary files count more due to hex encoding

        total_chars = len(text_query)

        for file_info in files:
            if file_info.content:
                if file_info.is_binary:
                    # Binary files as hex take more space
                    total_chars += len(file_info.content) * 1.2
                else:
                    total_chars += len(file_info.content)

        # Conservative estimation
        estimated_tokens = int(total_chars / 3.5)  # Slightly more conservative than 4
        return estimated_tokens

    def confirm_proceed(self, result: ValidationResult) -> bool:
        """Ask user confirmation if there are warnings."""
        if not result.warnings and result.is_valid:
            return True

        if not result.is_valid:
            print("❌ Request validation failed:")
            for error in result.errors:
                print(f"  • {error}")
            return False

        print("⚠️  Request validation warnings:")
        for warning in result.warnings:
            print(f"  • {warning}")

        print(f"\n📊 Request summary:")
        print(f"  • Files: {result.file_count} ({result.text_files} text, {result.binary_files} binary)")
        print(f"  • Total size: {result.total_size_bytes / (1024*1024):.1f}MB")

        response = input("\nDo you want to proceed? (y/N): ")
        return response.lower().startswith('y')


def suggest_optimization_tips():
    """Suggest ways to reduce token consumption."""
    tips = [
        "💡 Token Optimization Tips:",
        "",
        "1. 📁 File Selection:",
        "   • Use specific file patterns instead of whole directories",
        "   • Focus on main source files, skip tests/docs unless needed",
        "   • Exclude generated files (build artifacts, logs, etc.)",
        "",
        "2. 📝 Content Filtering:",
        "   • Use .gitignore-style patterns to exclude irrelevant files",
        "   • Summarize large config files instead of including full content",
        "   • Consider splitting large requests into smaller focused ones",
        "",
        "3. 🎯 Query Optimization:",
        "   • Be specific about what you want to know",
        "   • Use focused questions rather than broad requests",
        "   • Consider breaking complex tasks into smaller requests",
        "",
        "4. 🚀 Performance Tips:",
        "   • Use --dry-run to preview requests before sending",
        "   • Configure limits in ~/.doq-config.yaml",
        "   • Monitor token usage to optimize future requests",
        "",
        "5. 📋 Directory Patterns:",
        "   • Use ./ for current directory (non-recursive)",
        "   • Use ./** for recursive scanning",
        "   • Use ./src/* for specific subdirectories",
        "   • Combine with file extensions: ./src/*.py",
    ]

    for tip in tips:
        print(tip)


class EnhancedRequestValidator(RequestValidator):
    """Enhanced validator with additional checks and configurable limits."""

    def __init__(self, limits: Optional[ValidationLimits] = None):
        super().__init__(limits)

    def validate_request_enhanced(self, files: List, text_query: str,
                                 interactive: bool = False) -> ValidationResult:
        """Enhanced validation with additional checks and user interaction."""
        warnings = []
        errors = []
        skipped_files = []

        # Run basic validation first
        basic_result = self.validate_request(files, text_query)
        warnings.extend(basic_result.warnings)
        errors.extend(basic_result.errors)

        # Enhanced checks
        self._check_file_diversity(files, warnings)
        self._check_redundant_files(files, warnings)
        self._check_query_complexity(text_query, warnings)
        self._check_directory_structure(files, warnings)

        # Interactive validation if enabled
        if interactive and (warnings or errors):
            if not self._interactive_validation(basic_result, warnings, errors):
                errors.append("User cancelled request")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings + basic_result.warnings,
            errors=errors,
            file_count=basic_result.file_count,
            total_size_bytes=basic_result.total_size_bytes,
            binary_files=basic_result.binary_files,
            text_files=basic_result.text_files,
            skipped_files=skipped_files
        )

    def _check_file_diversity(self, files: List, warnings: List[str]):
        """Check for too many similar files that might be redundant."""
        if len(files) < 3:
            return

        # Group files by extension
        extensions = {}
        for file_info in files:
            ext = Path(file_info.path).suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

        # Warn about too many files of same type
        for ext, count in extensions.items():
            if count > 10:
                warnings.append(f"Many {ext or 'no-extension'} files ({count}). Consider filtering specific files.")

    def _check_redundant_files(self, files: List, warnings: List[str]):
        """Check for potentially redundant files."""
        redundant_patterns = [
            ('test', 'Many test files detected. Consider excluding unless analyzing tests specifically.'),
            ('spec', 'Many spec files detected. Consider excluding unless analyzing tests specifically.'),
            ('doc', 'Many documentation files detected. Consider excluding unless analyzing docs.'),
            ('example', 'Many example files detected. Consider excluding unless analyzing examples.'),
            ('sample', 'Many sample files detected. Consider excluding unless analyzing samples.'),
        ]

        for pattern, message in redundant_patterns:
            matching_files = [f for f in files if pattern in f.path.lower()]
            if len(matching_files) > 5:
                warnings.append(f"{message} ({len(matching_files)} files)")

    def _check_query_complexity(self, text_query: str, warnings: List[str]):
        """Check query complexity and suggest improvements."""
        if len(text_query) < 5:
            warnings.append("Very short query. Consider providing more context for better results.")

        if len(text_query) > 1000:
            warnings.append("Very long query. Consider breaking into smaller, focused questions.")

        # Check for vague terms
        vague_terms = ['analyze', 'review', 'check', 'look at', 'help with']
        query_lower = text_query.lower()
        found_vague = [term for term in vague_terms if term in query_lower]

        if len(found_vague) > 2:
            warnings.append("Query contains vague terms. Be more specific about what you want to know.")

    def _check_directory_structure(self, files: List, warnings: List[str]):
        """Check directory structure for potential issues."""
        if len(files) == 0:
            return

        # Check for deep nested structures
        max_depth = max(len(Path(f.path).parts) for f in files)
        if max_depth > 8:
            warnings.append(f"Deep directory nesting detected (depth: {max_depth}). Consider focusing on specific areas.")

        # Check for scattered files across many directories
        directories = set(str(Path(f.path).parent) for f in files)
        if len(directories) > 15:
            warnings.append(f"Files scattered across many directories ({len(directories)}). Consider organizing by area of interest.")

    def _interactive_validation(self, result: ValidationResult, warnings: List[str],
                               errors: List[str]) -> bool:
        """Interactive validation with user confirmation."""
        print("\n" + "="*60)
        print("🔍 REQUEST VALIDATION RESULTS")
        print("="*60)

        if errors:
            print("❌ ERRORS (Request cannot proceed):")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            print()
            return False

        if warnings:
            print("⚠️  WARNINGS:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
            print()

        # Show summary
        print("📊 REQUEST SUMMARY:")
        print(f"  • Files: {result.file_count} ({result.text_files} text, {result.binary_files} binary)")
        print(f"  • Total size: {result.total_size_bytes / (1024*1024):.1f}MB")

        # Estimate cost/tokens
        estimated_tokens = self._estimate_tokens("", [])  # Will be calculated properly
        if estimated_tokens > 10000:
            print(f"  • Estimated tokens: ~{estimated_tokens:,}")
            print(f"  • Estimated cost: $0.{estimated_tokens//1000:02d} - $0.{estimated_tokens//500:02d} (rough estimate)")

        print()
        print("OPTIONS:")
        print("  y) Proceed with request")
        print("  n) Cancel request")
        print("  t) Show optimization tips")
        print("  f) Show file list")

        while True:
            choice = input("Your choice (y/n/t/f): ").lower().strip()

            if choice == 'y' or choice == 'yes':
                return True
            elif choice == 'n' or choice == 'no':
                return False
            elif choice == 't' or choice == 'tips':
                suggest_optimization_tips()
                print()
            elif choice == 'f' or choice == 'files':
                self._show_file_list(result)
                print()
            else:
                print("Please choose y, n, t, or f")


    def _show_file_list(self, result: ValidationResult):
        """Show detailed file list for user review."""
        print("📁 FILES TO BE INCLUDED:")
        print("-" * 40)

        # Group files by directory for better readability
        files_by_dir = {}
        for file_info in result.files if hasattr(result, 'files') else []:
            dir_path = str(Path(file_info.path).parent)
            if dir_path not in files_by_dir:
                files_by_dir[dir_path] = []
            files_by_dir[dir_path].append(file_info)

        for directory, files in sorted(files_by_dir.items()):
            print(f"\n📂 {directory}:")
            for file_info in sorted(files, key=lambda x: x.path):
                size_str = f"{file_info.size/1024:.1f}KB" if file_info.size > 1024 else f"{file_info.size}B"
                file_type = "📄" if not file_info.is_binary else "📦"
                filename = Path(file_info.path).name
                print(f"  {file_type} {filename} ({size_str})")


def create_validator_from_config(config_path: Optional[str] = None) -> EnhancedRequestValidator:
    """Create enhanced validator from configuration file."""
    if config_path is None:
        config_path = os.path.expanduser("~/.doq-config.yaml")

    limits = ValidationLimits()

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            validation_config = config.get('validation', {})
            if validation_config:
                # Update limits from config
                for key, value in validation_config.items():
                    if hasattr(limits, key):
                        setattr(limits, key, value)

        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}", file=sys.stderr)

    return EnhancedRequestValidator(limits)

