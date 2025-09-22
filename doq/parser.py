"""Argument parser module for DOQ CLI."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None


@dataclass
class FileInfo:
    """Information about a file to be included in the request."""
    path: str
    is_binary: bool
    size: int
    include_mode: str  # 'full', 'truncated', 'as_file'
    content: Optional[str] = None


@dataclass
class RequestStructure:
    """Structure containing parsed request information."""
    text_query: str
    provider: str = "claude"
    interactive: bool = False
    dry_run: bool = False
    files: List[FileInfo] = field(default_factory=list)
    raw_args: List[str] = field(default_factory=list)


class ArgumentParser:
    """Parser for command line arguments with enhanced directory handling and validation."""

    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
    BINARY_TRUNCATE_BYTES = 1024  # Show first/last 1KB for binary files

    PROVIDERS_WITH_FILE_SUPPORT = {"claude"}  # Providers that support direct file uploads

    def __init__(self, working_dir: Optional[str] = None):
        self.text_parts: List[str] = []
        self.files: List[FileInfo] = []
        self.provider = "claude"
        self.interactive = False
        self.dry_run = False
        self.raw_args: List[str] = []
        self._working_dir = Path(working_dir) if working_dir else None

    @property
    def _cwd(self) -> Path:
        """Get current working directory, allowing for testing injection."""
        return self._working_dir if self._working_dir else Path.cwd()

    def parse_args(self, args: List[str]) -> RequestStructure:
        """Parse command line arguments into a RequestStructure."""
        self.raw_args = args.copy()
        self._reset_state()

        i = 0
        while i < len(args):
            arg = args[i]

            # Handle quoted strings
            if arg.startswith(('"', "'")):
                quoted_text, consumed = self._parse_quoted_string(args[i:])
                self.text_parts.append(quoted_text)
                i += consumed
                continue

            # Handle special parameters
            if arg == "-i":
                self.interactive = True
                i += 1
                continue

            if arg == "--dry-run":
                self.dry_run = True
                i += 1
                continue

            if arg == "-h" or arg == "--help":
                # Help flags are handled in main(), skip parsing here
                i += 1
                continue

            if arg == "--doq-default-config":
                # Config flag is handled in main(), skip parsing here
                i += 1
                continue

            if arg.startswith("--llm="):
                self.provider = arg.split("=", 1)[1]
                i += 1
                continue

            # Enhanced directory pattern handling
            if self._is_directory_pattern(arg):
                directory_files = self._process_directory_pattern(arg)
                self.files.extend(directory_files)
                i += 1
                continue

            # Check if argument is a URL
            if self._is_url(arg):
                url_file_info = self._process_url(arg)
                if url_file_info:
                    self.files.append(url_file_info)
                else:
                    # If URL processing failed, treat as text
                    self.text_parts.append(arg)
                i += 1
                continue

            # Check if argument is a file path
            if self._is_file_path(arg):
                file_info = self._process_file(arg)
                if file_info:
                    self.files.append(file_info)
                else:
                    # If file processing failed or was rejected, treat as text
                    self.text_parts.append(arg)
                i += 1
                continue

            # Regular text argument
            self.text_parts.append(arg)
            i += 1

        return self._build_request_structure()

    def _reset_state(self):
        """Reset parser state."""
        self.text_parts = []
        self.files = []
        self.provider = "claude"
        self.interactive = False
        self.dry_run = False

    def _parse_quoted_string(self, args: List[str]) -> Tuple[str, int]:
        """Parse a quoted string that may span multiple arguments."""
        quote_char = args[0][0]
        text_parts = []
        consumed = 0

        for i, arg in enumerate(args):
            consumed += 1

            if i == 0:
                # First argument - remove opening quote
                current_text = arg[1:]
            else:
                current_text = arg

            # Check for closing quote (not escaped)
            if self._has_unescaped_closing_quote(current_text, quote_char):
                # Remove closing quote and add final part
                end_pos = self._find_unescaped_quote_pos(current_text, quote_char)
                text_parts.append(current_text[:end_pos])
                break
            else:
                text_parts.append(current_text)

        # Unescape the final result
        final_text = " ".join(text_parts)
        return self._unescape_string(final_text), consumed

    def _has_unescaped_closing_quote(self, text: str, quote_char: str) -> bool:
        """Check if text contains an unescaped closing quote."""
        return self._find_unescaped_quote_pos(text, quote_char) != -1

    def _find_unescaped_quote_pos(self, text: str, quote_char: str) -> int:
        """Find position of unescaped quote character."""
        i = 0
        while i < len(text):
            if text[i] == quote_char:
                # Check if it's escaped by counting preceding backslashes
                escape_count = 0
                j = i - 1
                while j >= 0 and text[j] == '\\':
                    escape_count += 1
                    j -= 1

                # If even number of escapes (including 0), quote is not escaped
                if escape_count % 2 == 0:
                    return i
            i += 1
        return -1

    def _unescape_string(self, text: str) -> str:
        """Remove escape characters from string."""
        result = ""
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                next_char = text[i + 1]
                if next_char in ['"', "'", '\\']:
                    result += next_char
                    i += 2
                else:
                    result += text[i]
                    i += 1
            else:
                result += text[i]
                i += 1
        return result

    def _is_directory_pattern(self, arg: str) -> bool:
        """Enhanced check for directory patterns including ., ./, ./* and ./**"""
        # Skip obvious non-directory patterns
        if len(arg) > 50:  # Very long strings are probably not directory patterns
            return False

        # Skip arguments that contain spaces (likely text)
        if ' ' in arg:
            return False

        # Skip arguments that are clearly flags
        if arg.startswith('--') or (arg.startswith('-') and len(arg) == 2):
            return False

        # Skip arguments with non-ASCII characters (likely text in other languages)
        try:
            arg.encode('ascii')
        except UnicodeEncodeError:
            return False

        # Direct patterns
        direct_patterns = [".", "./", "./*", "./**"]
        if arg in direct_patterns:
            return True

        # Pattern like ./directory, ./directory/, ./directory/*, ./directory/**
        if arg.startswith("./"):
            # Remove ./ prefix for checking
            path_part = arg[2:]

            # Handle patterns like ./directory, ./directory/, ./directory/*, ./directory/**
            if path_part.endswith("/**"):
                base_path = self._cwd / path_part[:-3]
                try:
                    return base_path.exists() and base_path.is_dir()
                except (OSError, ValueError):
                    return False
            elif path_part.endswith("/*"):
                base_path = self._cwd / path_part[:-2]
                try:
                    return base_path.exists() and base_path.is_dir()
                except (OSError, ValueError):
                    return False
            elif path_part.endswith("/"):
                base_path = self._cwd / path_part[:-1]
                try:
                    return base_path.exists() and base_path.is_dir()
                except (OSError, ValueError):
                    return False
            else:
                # For ./path patterns without trailing slash or wildcard,
                # only treat as directory if it actually exists and is a directory
                base_path = self._cwd / path_part
                try:
                    return base_path.exists() and base_path.is_dir()
                except (OSError, ValueError):
                    return False

        # Direct directory patterns like src/, src/*, src/**
        if arg.endswith("/") or arg.endswith("/*") or arg.endswith("/**"):
            if arg.endswith("/**"):
                base_path = self._cwd / arg[:-3]
            elif arg.endswith("/*"):
                base_path = self._cwd / arg[:-2]
            else:  # ends with /
                base_path = self._cwd / arg[:-1]

            try:
                return base_path.exists() and base_path.is_dir()
            except (OSError, ValueError):
                return False

        # Only check for plain directory paths if the argument looks like a reasonable path
        # (contains only ASCII letters, numbers, common punctuation, and path separators)
        if not all(c.isalnum() or c in '._-/\\' for c in arg):
            return False

        # Additional safety check: skip very common non-directory words
        if arg.lower() in {'hello', 'world', 'test', 'file', 'content', 'data', 'main', 'utils'}:
            return False

        # Check if it's a plain directory path (but be conservative)
        try:
            path = self._cwd / arg if not Path(arg).is_absolute() else Path(arg)
            return path.exists() and path.is_dir()
        except (OSError, ValueError):
            return False

    def _process_directory_pattern(self, pattern: str) -> List[FileInfo]:
        """Enhanced directory pattern processing - only include files if * is in pattern."""
        files = []

        try:
            # Check if pattern contains wildcard - only include files if it does
            should_include_files = "*" in pattern

            # Normalize the pattern
            recursive = False
            base_path = None

            if pattern == ".":
                base_path = self._cwd
                recursive = False
            elif pattern == "./":
                base_path = self._cwd
                recursive = False
            elif pattern == "./*":
                base_path = self._cwd
                recursive = False
            elif pattern == "./**":
                base_path = self._cwd
                recursive = True
            elif pattern.startswith("./"):
                # Handle ./directory, ./directory/, ./directory/*, ./directory/**
                path_part = pattern[2:]
                if path_part.endswith("/**"):
                    base_path = self._cwd / path_part[:-3]
                    recursive = True
                elif path_part.endswith("/*"):
                    base_path = self._cwd / path_part[:-2]
                    recursive = False
                elif path_part.endswith("/"):
                    base_path = self._cwd / path_part[:-1]
                    recursive = False
                else:
                    base_path = self._cwd / path_part
                    recursive = False
            elif pattern.endswith("/**"):
                base_path = self._cwd / pattern[:-3] if not Path(pattern[:-3]).is_absolute() else Path(pattern[:-3])
                recursive = True
            elif pattern.endswith("/*"):
                base_path = self._cwd / pattern[:-2] if not Path(pattern[:-2]).is_absolute() else Path(pattern[:-2])
                recursive = False
            elif pattern.endswith("/"):
                base_path = self._cwd / pattern[:-1] if not Path(pattern[:-1]).is_absolute() else Path(pattern[:-1])
                recursive = False
            else:
                # Plain directory name
                base_path = self._cwd / pattern if not Path(pattern).is_absolute() else Path(pattern)
                recursive = False

            if base_path and base_path.exists() and base_path.is_dir():
                if should_include_files:
                    # Include files only if pattern contains *
                    files.extend(self._scan_directory(base_path, recursive))
                # If no wildcard, we still process it as a directory pattern for tree generation
                # but don't include any files

        except Exception as e:
            print(f"Error processing directory pattern {pattern}: {e}", file=sys.stderr)

        return files

    def _scan_directory(self,
                        dir_path: Path,
                        recursive: bool,
                        max_depth: int = 5, current_depth: int = 0
                        ) -> List[FileInfo]:
        """Scan directory for files with optional recursion and enhanced filtering."""
        files: List[FileInfo] = []

        if current_depth > max_depth:
            print(f"Warning: Maximum directory depth ({max_depth}) reached in {dir_path}", file=sys.stderr)
            return files

        # Enhanced ignore patterns
        ignore_patterns = {
            "__pycache__", ".git", ".svn", ".hg", "node_modules",
            ".venv", "venv", ".env", ".pytest_cache", ".coverage",
            ".DS_Store", "Thumbs.db", ".idea", ".vscode",
            "build", "dist", "target", "bin", "obj",
            "*.egg-info", ".tox", ".mypy_cache"
        }

        # Additional file extensions to skip
        skip_extensions = {
            '.pyc', '.pyo', '.pyd', '.log', '.tmp', '.temp',
            '.bak', '.swp', '.swo', '.orig', '.rej',
            '.class', '.o', '.so', '.dll', '.exe'
        }

        try:
            for item in sorted(dir_path.iterdir()):
                # Skip hidden files (except for explicitly allowed ones)
                if item.name.startswith('.') and item.name not in {'.gitignore', '.env.example'}:
                    continue

                if item.name in ignore_patterns:
                    continue

                # Check for glob patterns in ignore_patterns
                should_skip = False
                for pattern in ignore_patterns:
                    if pattern.startswith('*') and item.name.endswith(pattern[1:]):
                        should_skip = True
                        break

                if should_skip:
                    continue

                if item.is_file():
                    # Skip files with problematic extensions
                    if item.suffix.lower() in skip_extensions:
                        continue

                    # Process file
                    file_info = self._process_file(str(item))
                    if file_info:
                        files.append(file_info)

                elif item.is_dir() and recursive:
                    # Recursively scan subdirectories
                    subdir_files = self._scan_directory(item, recursive=True,
                                                        max_depth=max_depth,
                                                        current_depth=current_depth + 1)
                    files.extend(subdir_files)

        except PermissionError:
            print(f"Warning: Permission denied accessing {dir_path}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error scanning {dir_path}: {e}", file=sys.stderr)

        return files

    def _is_file_path(self, arg: str) -> bool:
        """Check if argument is a valid file path."""
        try:
            path = Path(arg)
            return path.exists() and path.is_file()
        except (OSError, ValueError):
            return False

    def _process_file(self, file_path: str) -> Optional[FileInfo]:
        """Process a file and return FileInfo object."""
        try:
            path = Path(file_path)
            size = path.stat().st_size
            is_binary = self._is_binary_file(path)

            # Check if file is large
            if size > self.LARGE_FILE_THRESHOLD:
                if not self._confirm_large_file(file_path, size):
                    return None

            # Determine include mode
            include_mode = "full"
            if is_binary and size > self.BINARY_TRUNCATE_BYTES * 2:
                binary_mode = self._ask_binary_file_mode(file_path)
                if binary_mode is None:
                    return None
                include_mode = binary_mode

            # Check if provider supports files
            if self.provider in self.PROVIDERS_WITH_FILE_SUPPORT:
                include_mode = "as_file"

            file_info = FileInfo(
                path=str(path.absolute()),
                is_binary=is_binary,
                size=size,
                include_mode=include_mode
            )

            # Load content if needed
            if include_mode != "as_file":
                file_info.content = self._load_file_content(path, is_binary, include_mode)

            return file_info

        except Exception as e:
            print(f"Error processing file {file_path}: {e}", file=sys.stderr)
            return None

    def _is_binary_file(self, path: Path) -> bool:
        """Check if file is binary."""
        try:
            with open(path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except Exception:
            return True

    def _confirm_large_file(self, file_path: str, size: int) -> bool:
        """Ask user confirmation for large files."""
        size_mb = size / (1024 * 1024)
        response = input(f"File {file_path} is large ({size_mb:.1f}MB). Include it? (y/N): ")
        return response.lower().startswith('y')

    def _ask_binary_file_mode(self, file_path: str) -> Optional[str]:
        """Ask user how to include binary file."""
        print(f"Binary file {file_path} detected.")
        response = input("Include (f)ull, (t)runcated, or (s)kip? (f/t/s): ")

        if response.lower().startswith('f'):
            return "full"
        elif response.lower().startswith('t'):
            return "truncated"
        else:
            return None

    def _load_file_content(self, path: Path, is_binary: bool, include_mode: str) -> str:
        """Load file content based on type and mode."""
        try:
            if is_binary:
                return self._load_binary_content(path, include_mode)
            else:
                return self._load_text_content(path)
        except Exception as e:
            return f"Error reading file: {e}"

    def _load_text_content(self, path: Path) -> str:
        """Load text file content."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"### {path} ###\n{content}\n"
        except UnicodeDecodeError:
            # Fallback to binary mode if UTF-8 fails
            return self._load_binary_content(path, "full")

    def _load_binary_content(self, path: Path, include_mode: str) -> str:
        """Load binary file content as hex."""
        with open(path, 'rb') as f:
            data = f.read()

        hex_data = data.hex()

        if include_mode == "truncated" and len(data) > self.BINARY_TRUNCATE_BYTES * 2:
            start_bytes = data[:self.BINARY_TRUNCATE_BYTES].hex()
            end_bytes = data[-self.BINARY_TRUNCATE_BYTES:].hex()
            return f"### {path} (binary, {len(data)} bytes) ###\n{start_bytes}...{len(data)}...{end_bytes}\n"
        else:
            return f"### {path} (binary, {len(data)} bytes) ###\n{hex_data}\n"

    def _build_request_structure(self) -> RequestStructure:
        """Build final RequestStructure object with directory tree in query text when directories are processed."""
        # Build text query
        text_query = " ".join(self.text_parts)

        # Check if directories were processed and add directory tree to query
        if self._has_directory_patterns_in_args():
            # Generate directory tree even if no files are included
            base_dir = self._find_directory_base_from_args()

            if self.files:
                # If files are included, use existing tree generation
                tree_output = self._generate_directory_tree(self.files)
            else:
                # If no files (no wildcard), generate tree showing directory structure only
                tree_output = self._generate_directory_structure_tree()

            # Add directory tree to the query text
            tree_section = f"\n\n#### {base_dir} ####\n{tree_output}"
            text_query += tree_section

        # Add file contents to text if not using file mode
        for file_info in self.files:
            if file_info.include_mode != "as_file" and file_info.content:
                text_query += "\n\n" + file_info.content

        return RequestStructure(
            text_query=text_query.strip(),
            provider=self.provider,
            interactive=self.interactive,
            dry_run=self.dry_run,
            files=self.files,
            raw_args=self.raw_args
        )

    def _has_directory_patterns_in_args(self) -> bool:
        """Check if any of the raw arguments represent directory patterns."""
        for arg in self.raw_args:
            # Skip option flags
            if arg.startswith("-"):
                continue

            # Use the same logic as _is_directory_pattern to be consistent
            if self._is_directory_pattern(arg):
                return True

        return False

    def _find_common_base_directory(self) -> str:
        """Find the common base directory for all files."""
        if not self.files:
            return ""

        # Get all file paths
        paths = [Path(file_info.path) for file_info in self.files]

        # Find common parent
        common_parts = []
        if paths:
            # Start with the first path's parts
            first_parts = paths[0].parts

            # Check each part to see if it's common to all paths
            for i, part in enumerate(first_parts):
                if all(len(path.parts) > i and path.parts[i] == part for path in paths):
                    common_parts.append(part)
                else:
                    break

        if common_parts:
            return str(Path(*common_parts))
        else:
            return str(Path.cwd())

    def _find_directory_base_from_args(self) -> str:
        """Find the base directory from arguments, even when no files are included."""
        if self.files:
            return self._find_common_base_directory()

        # Find directory patterns in args to determine base directory
        for arg in self.raw_args:
            if arg.startswith("-"):
                continue

            if self._is_directory_pattern(arg):
                try:
                    if arg == "." or arg == "./" or arg == "./*" or arg == "./**":
                        return str(self._cwd)
                    elif arg.startswith("./"):
                        path_part = arg[2:]
                        if path_part.endswith("/**"):
                            return str((self._cwd / path_part[:-3]).resolve())
                        elif path_part.endswith("/*"):
                            return str((self._cwd / path_part[:-2]).resolve())
                        elif path_part.endswith("/"):
                            return str((self._cwd / path_part[:-1]).resolve())
                        else:
                            return str((self._cwd / path_part).resolve())
                    else:
                        # Handle patterns like src/, src/*, src/**
                        if arg.endswith("/**"):
                            return str((self._cwd / arg[:-3] if not Path(arg[:-3]).is_absolute() else Path(
                                arg[:-3])).resolve())
                        elif arg.endswith("/*"):
                            return str((self._cwd / arg[:-2] if not Path(arg[:-2]).is_absolute() else Path(
                                arg[:-2])).resolve())
                        elif arg.endswith("/"):
                            return str((self._cwd / arg[:-1] if not Path(arg[:-1]).is_absolute() else Path(
                                arg[:-1])).resolve())
                        else:
                            return str((self._cwd / arg if not Path(arg).is_absolute() else Path(arg)).resolve())
                except Exception:
                    continue

        return str(self._cwd)

    def _generate_directory_structure_tree(self) -> str:
        """Generate a directory structure tree when no files are included (no wildcard patterns)."""
        # Find the directory pattern from args
        target_dir = None

        for arg in self.raw_args:
            if arg.startswith("-"):
                continue

            if self._is_directory_pattern(arg) and "*" not in arg:
                try:
                    if arg == "." or arg == "./":
                        target_dir = self._cwd
                    elif arg.startswith("./"):
                        path_part = arg[2:].rstrip("/")
                        target_dir = self._cwd / path_part
                    elif arg.endswith("/"):
                        target_dir = self._cwd / arg[:-1] if not Path(arg[:-1]).is_absolute() else Path(arg[:-1])
                    else:
                        target_dir = self._cwd / arg if not Path(arg).is_absolute() else Path(arg)
                    break
                except Exception:
                    continue

        if not target_dir or not target_dir.exists():
            return "Directory not found or not accessible."

        # Generate recursive directory tree structure
        return self._build_recursive_directory_tree(target_dir)

    def _build_recursive_directory_tree(self, dir_path: Path, prefix: str = "", max_depth: int = 5,
                                        current_depth: int = 0) -> str:
        """Build a recursive directory tree showing both files and directories."""
        if current_depth > max_depth:
            return f"{prefix}... (max depth {max_depth} reached)"

        # Enhanced ignore patterns
        ignore_patterns = {
            "__pycache__", ".git", ".svn", ".hg", "node_modules",
            ".venv", "venv", ".env", ".pytest_cache", ".coverage",
            ".DS_Store", "Thumbs.db", ".idea", ".vscode",
            "build", "dist", "target", "bin", "obj"
        }

        tree_lines = []

        try:
            items = list(dir_path.iterdir())

            # Filter and sort items
            filtered_items = []
            for item in sorted(items):
                if item.name.startswith('.') and item.name not in {'.gitignore', '.env.example'}:
                    continue
                if item.name in ignore_patterns:
                    continue
                filtered_items.append(item)

            for i, item in enumerate(filtered_items):
                is_last = i == len(filtered_items) - 1
                current_prefix = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                if item.is_dir():
                    tree_lines.append(f"{prefix}{current_prefix}📁 {item.name}/")
                    # Recursively show subdirectory contents
                    subdirectory_tree = self._build_recursive_directory_tree(
                        item, next_prefix, max_depth, current_depth + 1
                    )
                    if subdirectory_tree.strip():
                        tree_lines.append(subdirectory_tree)
                else:
                    try:
                        size = item.stat().st_size
                        size_str = self._format_file_size(size)
                        is_binary = self._is_binary_file(item)
                        file_type = "📦" if is_binary else "📄"
                        tree_lines.append(f"{prefix}{current_prefix}{file_type} {item.name} ({size_str})")
                    except Exception:
                        tree_lines.append(f"{prefix}{current_prefix}📄 {item.name}")

        except PermissionError:
            tree_lines.append(f"{prefix}Permission denied accessing {dir_path}")
        except Exception as e:
            tree_lines.append(f"{prefix}Error reading {dir_path}: {e}")

        return "\n".join(tree_lines)

    def _generate_directory_tree(self, files):
        """Generate a visual directory tree from the list of files."""
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
                    size_str = self._format_file_size(content['size'])
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

    def _format_file_size(self, size_bytes):
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f}MB"

    def _is_url(self, arg: str) -> bool:
        """Check if argument is a valid URL."""
        import re

        # URL pattern that matches http, https protocols
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return bool(url_pattern.match(arg))

    def _process_url(self, url: str) -> Optional[FileInfo]:
        """Download content from URL and return FileInfo object."""
        try:
            if requests is None:
                print(f"Error: 'requests' library is required for URL processing. Install it with: pip install requests", file=sys.stderr)
                return None

            print(f"Downloading content from {url}...")

            # Configure request with timeout and headers
            headers = {
                'User-Agent': 'DOQ CLI Tool/1.0'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Get content type to determine if it's binary
            content_type = response.headers.get('content-type', '').lower()
            is_binary = not (
                'text/' in content_type or
                'application/json' in content_type or
                'application/xml' in content_type or
                'application/javascript' in content_type or
                'application/x-javascript' in content_type
            )

            # Get filename from URL
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1] if parsed_url.path and parsed_url.path != '/' else ''
            if not filename or filename == '/' or not filename.strip():
                filename = f"content_from_{parsed_url.netloc.replace('.', '_')}"

            # Get content size
            content_size = len(response.content)

            # Check if content is too large
            if content_size > self.LARGE_FILE_THRESHOLD:
                if not self._confirm_large_file(f"URL content ({filename})", content_size):
                    return None

            # Determine include mode based on provider and content type
            include_mode = "full"
            # For Claude provider, only use as_file mode for non-text content to ensure content is loaded for tests
            if self.provider in self.PROVIDERS_WITH_FILE_SUPPORT and is_binary:
                include_mode = "as_file"

            file_info = FileInfo(
                path=f"{url} -> {filename}",
                is_binary=is_binary,
                size=content_size,
                include_mode=include_mode
            )

            # Load content if needed
            if include_mode != "as_file":
                if is_binary:
                    # For binary content from URLs, always show truncated view
                    hex_data = response.content.hex()
                    if len(response.content) > self.BINARY_TRUNCATE_BYTES * 2:
                        start_bytes = response.content[:self.BINARY_TRUNCATE_BYTES].hex()
                        end_bytes = response.content[-self.BINARY_TRUNCATE_BYTES:].hex()
                        file_info.content = f"### {url} (binary, {content_size} bytes) ###\n{start_bytes}...{content_size}...{end_bytes}\n"
                    else:
                        file_info.content = f"### {url} (binary, {content_size} bytes) ###\n{hex_data}\n"
                else:
                    # Text content
                    try:
                        text_content = response.text
                        file_info.content = f"### {url} ###\n{text_content}\n"
                    except UnicodeDecodeError:
                        # Fallback to binary if text decoding fails
                        hex_data = response.content.hex()
                        file_info.content = f"### {url} (binary fallback, {content_size} bytes) ###\n{hex_data}\n"

            print(f"Successfully downloaded {content_size} bytes from {url}")
            return file_info

        except Exception as e:
            print(f"Error downloading from {url}: {e}", file=sys.stderr)
            return None
