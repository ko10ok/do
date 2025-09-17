"""Argument parser module for DOQ CLI."""

import os
import sys
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


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
    """Parser for command line arguments with file handling and quote processing."""

    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
    BINARY_TRUNCATE_BYTES = 1024  # Show first/last 1KB for binary files

    PROVIDERS_WITH_FILE_SUPPORT = {"claude"}  # Providers that support direct file uploads

    def __init__(self):
        self.text_parts = []
        self.files = []
        self.provider = "claude"
        self.interactive = False
        self.dry_run = False
        self.raw_args = []

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

            if arg.startswith("--llm="):
                self.provider = arg.split("=", 1)[1]
                i += 1
                continue

            # Check if argument is a file path
            if self._is_file_path(arg):
                file_info = self._process_file(arg)
                if file_info:
                    self.files.append(file_info)
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
                include_mode = self._ask_binary_file_mode(file_path)
                if include_mode is None:
                    return None

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
        """Build final RequestStructure object."""
        # Build text query
        text_query = " ".join(self.text_parts)

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
