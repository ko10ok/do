"""Unit tests for argument parser module."""

import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from doq.parser import ArgumentParser, FileInfo, RequestStructure


class TestArgumentParser:
    """Test cases for ArgumentParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ArgumentParser()

    def test_simple_text_parsing(self):
        """Test parsing simple text arguments."""
        args = ["hello", "world", "test"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test"
        assert result.provider == "claude"
        assert not result.interactive
        assert not result.dry_run
        assert len(result.files) == 0

    def test_quoted_string_parsing(self):
        """Test parsing quoted strings."""
        args = ['"hello world"', "test"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test"

    def test_quoted_string_with_spaces(self):
        """Test parsing quoted strings that span multiple arguments."""
        args = ['"hello', 'world', 'test"', "after"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test after"

    def test_escaped_quotes(self):
        """Test parsing strings with escaped quotes."""
        args = ['"hello \\"world\\" test"']
        result = self.parser.parse_args(args)

        assert result.text_query == 'hello "world" test'

    def test_single_quotes(self):
        """Test parsing single-quoted strings."""
        args = ["'hello world'", "test"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test"

    def test_provider_parameter(self):
        """Test parsing provider parameter."""
        args = ["--llm=openai", "hello", "world"]
        result = self.parser.parse_args(args)

        assert result.provider == "openai"
        assert result.text_query == "hello world"

    def test_interactive_flag(self):
        """Test parsing interactive flag."""
        args = ["-i", "hello", "world"]
        result = self.parser.parse_args(args)

        assert result.interactive is True
        assert result.text_query == "hello world"

    def test_dry_run_flag(self):
        """Test parsing dry-run flag."""
        args = ["--dry-run", "hello", "world"]
        result = self.parser.parse_args(args)

        assert result.dry_run is True
        assert result.text_query == "hello world"

    def test_combined_flags(self):
        """Test parsing multiple flags together."""
        args = ["-i", "--llm=deepseek", "--dry-run", "hello"]
        result = self.parser.parse_args(args)

        assert result.interactive is True
        assert result.dry_run is True
        assert result.provider == "deepseek"
        assert result.text_query == "hello"

    @patch('doq.parser.ArgumentParser._is_binary_file')
    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    @patch('doq.parser.Path.stat')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.exists')
    def test_text_file_processing(self, mock_exists, mock_is_file, mock_stat, mock_open_file, mock_is_binary):
        """Test processing text files."""
        # Create a proper mock stat object with st_mode for is_dir() calls
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()
        mock_stat.return_value = mock_stat_obj

        # Setup mocks - only test.txt should be treated as a file
        def mock_exists_func():
            return True

        def mock_is_file_func():
            return True

        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_binary.return_value = False

        # Mock directory pattern detection to return False for test.txt
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            # Only test.txt exists
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "test.txt"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["hello", "test.txt"]
                result = self.parser.parse_args(args)

        assert len(result.files) == 1
        assert result.files[0].path.endswith("test.txt")
        assert not result.files[0].is_binary
        assert result.files[0].include_mode == "as_file"  # Claude provider uses as_file mode
        assert "hello" in result.text_query

    @patch('doq.parser.ArgumentParser._is_binary_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'\x00\x01\x02\x03')
    @patch('doq.parser.Path.stat')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.exists')
    def test_binary_file_processing(self, mock_exists, mock_is_file, mock_stat, mock_open_file, mock_is_binary):
        """Test processing binary files."""
        # Create a proper mock stat object with st_mode for is_dir() calls
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()
        mock_stat.return_value = mock_stat_obj

        # Setup mocks - only test.bin should be treated as a file
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_binary.return_value = True

        # Mock directory pattern detection to return False for test.bin
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            with patch('doq.parser.ArgumentParser._ask_binary_file_mode', return_value='full'):
                with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                    def is_file_path_side_effect(arg):
                        return arg == "test.bin"

                    mock_is_file_path.side_effect = is_file_path_side_effect

                    args = ["hello", "test.bin"]
                    result = self.parser.parse_args(args)

        assert len(result.files) == 1
        assert result.files[0].is_binary is True
        assert "hello" in result.text_query

    @patch('doq.parser.Path.exists')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.stat')
    @patch('builtins.input', return_value='n')
    def test_large_file_rejection(self, mock_input, mock_stat, mock_is_file, mock_exists):
        """Test rejecting large files."""
        # Create a proper mock stat object with st_mode for is_dir() calls
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': ArgumentParser.LARGE_FILE_THRESHOLD + 1,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()
        mock_stat.return_value = mock_stat_obj

        # Setup mocks using return values instead of side effects to avoid parameter issues
        mock_exists.return_value = True
        mock_is_file.return_value = True

        # Mock directory pattern detection to return False for large_file.txt
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "large_file.txt"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["hello", "large_file.txt"]
                result = self.parser.parse_args(args)

        assert len(result.files) == 0
        assert "hello large_file.txt" in result.text_query
        mock_input.assert_called_once()

    @patch('doq.parser.ArgumentParser._is_binary_file')
    @patch('builtins.open', new_callable=mock_open, read_data="large file content")
    @patch('builtins.input', return_value='y')
    @patch('doq.parser.Path.stat')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.exists')
    def test_large_file_acceptance(self, mock_exists, mock_is_file, mock_stat, mock_input, mock_open_file,
                                   mock_is_binary):
        """Test accepting large files."""
        # Create a proper mock stat object with st_mode for is_dir() calls
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': ArgumentParser.LARGE_FILE_THRESHOLD + 1,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()
        mock_stat.return_value = mock_stat_obj

        # Setup mocks using return values instead of side effects to avoid parameter issues
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_binary.return_value = False

        # Mock directory pattern detection to return False for large_file.txt
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "large_file.txt"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["hello", "large_file.txt"]
                result = self.parser.parse_args(args)

        assert len(result.files) == 1
        assert "hello" in result.text_query
        mock_input.assert_called_once()

    def test_file_path_vs_regular_arg(self):
        """Test distinguishing file paths from regular arguments."""
        # Non-existent file should be treated as regular argument
        args = ["hello", "nonexistent.txt"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello nonexistent.txt"
        assert len(result.files) == 0

    def test_claude_provider_file_mode(self):
        """Test that Claude provider uses file mode for supported files."""
        # Create a proper mock stat object with st_mode
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()

        with patch('doq.parser.Path.exists', return_value=True), \
                patch('doq.parser.Path.is_file', return_value=True), \
                patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                patch('doq.parser.ArgumentParser._is_binary_file', return_value=False), \
                patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "test.txt"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["--llm=claude", "hello", "test.txt"]
                result = self.parser.parse_args(args)

                assert len(result.files) == 1
                assert result.files[0].include_mode == "as_file"
                assert "hello" in result.text_query

    def test_complex_argument_parsing(self):
        """Test complex combination of arguments."""
        # Create a proper mock stat object with st_mode
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()

        with patch('doq.parser.Path.exists', return_value=True), \
                patch('doq.parser.Path.is_file', return_value=True), \
                patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                patch('builtins.open', new_callable=mock_open, read_data="file content"), \
                patch('doq.parser.ArgumentParser._is_binary_file', return_value=False), \
                patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "test.txt"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ['-i', '--llm=openai', '"quoted text"', 'regular', 'test.txt', '--dry-run']
                result = self.parser.parse_args(args)

                assert result.interactive is True
                assert result.dry_run is True
                assert result.provider == "openai"
                assert "quoted text" in result.text_query
                assert "regular" in result.text_query
                assert len(result.files) == 1

    def test_unquoted_russian_command(self):
        """Test parsing unquoted Russian command."""
        args = ["проверь", "содержимое", "файла", "script.py"]
        result = self.parser.parse_args(args)

        assert result.text_query == "проверь содержимое файла script.py"
        assert result.provider == "claude"
        assert not result.interactive
        assert not result.dry_run
        # script.py is treated as regular text since it doesn't exist
        assert len(result.files) == 0

    def test_unquoted_russian_with_real_file(self):
        """Test parsing unquoted Russian command with a real file."""
        # Create a proper mock stat object
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Regular file mode - this must be an integer
        })()

        with patch('doq.parser.Path.exists') as mock_exists, \
                patch('doq.parser.Path.is_file') as mock_is_file, \
                patch('doq.parser.Path.is_dir') as mock_is_dir, \
                patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                patch('builtins.open', new_callable=mock_open, read_data="# Python code\nprint('Hello')"), \
                patch('doq.parser.ArgumentParser._is_binary_file', return_value=False):

            # Setup proper side effects for path checking
            def exists_side_effect(path_obj=None):
                if path_obj is None:
                    # Called as method on Path object
                    path_str = str(path_obj) if path_obj else ""
                else:
                    path_str = str(path_obj)
                return "./file.py" in path_str

            def is_file_side_effect(path_obj=None):
                if path_obj is None:
                    path_str = str(path_obj) if path_obj else ""
                else:
                    path_str = str(path_obj)
                return "./file.py" in path_str

            def is_dir_side_effect(path_obj=None):
                return False  # ./file.py is not a directory

            mock_exists.side_effect = lambda: "./file.py" in str(mock_exists.return_value)
            mock_is_file.side_effect = lambda: "./file.py" in str(mock_is_file.return_value)
            mock_is_dir.side_effect = lambda: False

            # Mock _is_file_path to return True only for ./file.py
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "./file.py"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["проверь", "содержимое", "файла", "./file.py", "и", "сформулируй", "содержимое"]
                result = self.parser.parse_args(args)

                assert "проверь содержимое файла" in result.text_query
                assert "и сформулируй содержимое" in result.text_query
                assert len(result.files) == 1
                assert result.files[0].path.endswith("file.py")
                # For Claude provider, file is sent as attachment (as_file mode)
                assert result.files[0].include_mode == "as_file"
                # Content is not included in text_query for Claude
                assert "# Python code" not in result.text_query

    def test_unquoted_mixed_language_command(self):
        """Test parsing unquoted command with mixed Russian and English."""
        args = ["analyze", "код", "в", "файле", "main.py", "and", "объясни", "логику"]
        result = self.parser.parse_args(args)

        assert result.text_query == "analyze код в файле main.py and объясни логику"
        assert result.provider == "claude"
        assert len(result.files) == 0

    def test_unquoted_command_with_path_separators(self):
        """Test parsing unquoted command with file paths containing separators."""
        # Mock directory pattern detection to prevent unwanted directory tree generation
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            args = ["проанализируй", "файл", "./src/utils.py", "и", "покажи", "функции"]
            result = self.parser.parse_args(args)

            assert result.text_query == "проанализируй файл ./src/utils.py и покажи функции"
            assert "./src/utils.py" in result.text_query
            assert len(result.files) == 0  # File doesn't exist, treated as text

    def test_unquoted_command_with_provider_flag(self):
        """Test parsing unquoted Russian command with provider flag."""
        args = ["--llm=openai", "переведи", "текст", "на", "английский"]
        result = self.parser.parse_args(args)

        assert result.provider == "openai"
        assert result.text_query == "переведи текст на английский"
        assert len(result.files) == 0

    def test_unquoted_command_with_interactive_flag(self):
        """Test parsing unquoted command with interactive flag."""
        args = ["-i", "создай", "документацию", "для", "проекта"]
        result = self.parser.parse_args(args)

        assert result.interactive is True
        assert result.text_query == "создай документацию для проекта"
        assert len(result.files) == 0

    def test_unquoted_long_russian_command(self):
        """Test parsing long unquoted Russian command."""
        args = [
            "проанализируй", "данный", "код", "Python", "и", "предложи",
            "улучшения", "для", "повышения", "производительности", "и",
            "читаемости", "кода"
        ]
        result = self.parser.parse_args(args)

        expected_text = ("проанализируй данный код Python и предложи улучшения "
                         "для повышения производительности и читаемости кода")
        assert result.text_query == expected_text
        assert len(result.files) == 0

    def test_unquoted_command_with_multiple_files(self):
        """Test parsing unquoted command with multiple file references."""
        # Create a proper mock stat object with st_mode for is_dir() calls
        import stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Regular file mode
        })()

        with patch('doq.parser.Path.exists', return_value=True), \
                patch('doq.parser.Path.is_file', return_value=True), \
                patch('doq.parser.Path.is_dir', return_value=False), \
                patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                patch('builtins.open', new_callable=mock_open, read_data="# Code content"), \
                patch('doq.parser.ArgumentParser._is_binary_file', return_value=False), \
                patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            # Mock _is_file_path to return True only for .py and .js files
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg.endswith(('.py', '.js'))

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["сравни", "main.py", "и", "utils.js", "найди", "различия"]
                result = self.parser.parse_args(args)

                assert "сравни" in result.text_query
                assert "найди различия" in result.text_query
                assert len(result.files) == 2
                # Files should be included in text content since default provider is claude (as_file mode)

    def test_unquoted_command_with_special_characters(self):
        """Test parsing unquoted command with special characters and punctuation."""
        args = ["что", "делает", "функция", "test()", "в", "коде?"]
        result = self.parser.parse_args(args)

        assert result.text_query == "что делает функция test() в коде?"
        assert len(result.files) == 0

    def test_unquoted_command_with_numbers(self):
        """Test parsing unquoted command with numbers."""
        args = ["найди", "ошибки", "в", "строках", "1-10", "и", "25-30"]
        result = self.parser.parse_args(args)

        assert result.text_query == "найди ошибки в строках 1-10 и 25-30"
        assert len(result.files) == 0

    def test_unquoted_empty_command(self):
        """Test parsing empty unquoted command."""
        args = []
        result = self.parser.parse_args(args)

        assert result.text_query == ""
        assert len(result.files) == 0

    def test_unquoted_single_word_command(self):
        """Test parsing single word unquoted command."""
        args = ["помощь"]
        result = self.parser.parse_args(args)

        assert result.text_query == "помощь"
        assert len(result.files) == 0

    def test_directory_pattern_without_wildcard_no_files_included(self):
        """Test that directory patterns without wildcards don't include files in request."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files and directories
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "file2.txt").write_text("some content")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file3.py").write_text("def test(): pass")

            # Mock the current working directory to be our temp directory
            with patch('doq.parser.Path.cwd', return_value=temp_path):
                with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=True):
                    with patch('doq.parser.ArgumentParser._generate_directory_structure_tree') as mock_tree:
                        mock_tree.return_value = """├── 📄 file1.py (15B)
├── 📄 file2.txt (12B)
└── 📁 subdir/
    └── 📄 file3.py (18B)"""

                        # Test with "." pattern (no wildcard)
                        args = ["analyze", "."]
                        result = self.parser.parse_args(args)

                        # Should have directory tree but no files included
                        assert len(result.files) == 0
                        assert "analyze" in result.text_query
                        assert "####" in result.text_query  # Directory tree header
                        assert "📁" in result.text_query or "📄" in result.text_query  # Tree content

    def test_directory_pattern_with_wildcard_includes_files(self):
        """Test that directory patterns with wildcards include files in request."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "file2.txt").write_text("some content")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                # Mock _scan_directory to return test files
                mock_scan.return_value = [
                    FileInfo(
                        path=str(temp_path / "file1.py"),
                        is_binary=False,
                        size=100,
                        include_mode="as_file",
                        content="print('hello')"
                    )
                ]

                # Test with "./*" pattern (with wildcard)
                args = ["analyze", "./*"]
                result = parser.parse_args(args)

                # Should include files
                assert len(result.files) == 1
                assert result.files[0].path.endswith("file1.py")

    def test_directory_pattern_recursive_wildcard(self):
        """Test recursive directory pattern with wildcard (./**)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested structure
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file2.py").write_text("def test(): pass")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                # Mock recursive scan
                mock_scan.return_value = [
                    FileInfo(
                        path=str(temp_path / "file1.py"),
                        is_binary=False,
                        size=100,
                        include_mode="as_file"
                    ),
                    FileInfo(
                        path=str(temp_path / "subdir" / "file2.py"),
                        is_binary=False,
                        size=150,
                        include_mode="as_file"
                    )
                ]

                # Test with "./**" pattern (recursive wildcard)
                args = ["analyze", "./**"]
                result = parser.parse_args(args)

                # Should include files from all levels
                assert len(result.files) == 2

    def test_specific_directory_without_wildcard(self):
        """Test specific directory pattern without wildcard (./src)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create src directory with files
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")
            (src_dir / "utils.py").write_text("def helper(): pass")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            # Test with "./src" pattern (no wildcard)
            args = ["analyze", "./src"]
            result = parser.parse_args(args)

            # Should show directory structure but not include files
            assert len(result.files) == 0
            assert "analyze" in result.text_query
            assert "####" in result.text_query  # Directory tree header

    def test_specific_directory_with_wildcard(self):
        """Test specific directory pattern with wildcard (./src/*)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create src directory with files
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                mock_scan.return_value = [
                    FileInfo(
                        path=str(src_dir / "main.py"),
                        is_binary=False,
                        size=100,
                        include_mode="as_file"
                    )
                ]

                # Test with "./src/*" pattern (with wildcard)
                args = ["analyze", "./src/*"]
                result = parser.parse_args(args)

                # Should include files from src directory
                assert len(result.files) == 1
                assert "main.py" in result.files[0].path

    def test_directory_tree_generation_in_query(self):
        """Test that directory tree is included in final query text."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test structure
            (temp_path / "README.md").write_text("# Project")
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.py").write_text("def main(): pass")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._build_recursive_directory_tree') as mock_tree:
                mock_tree.return_value = """├── 📄 README.md (10B)
└── 📁 src/
    └── 📄 main.py (20B)"""

                args = ["show structure", "."]
                result = parser.parse_args(args)

                # Check that query contains the directory tree
                assert "show structure" in result.text_query
                assert "####" in result.text_query
                assert "📄 README.md" in result.text_query
                assert "📁 src/" in result.text_query

    def test_wildcard_detection_in_process_directory_pattern(self):
        """Test that wildcard detection works correctly in _process_directory_pattern."""
        # Test patterns without wildcards
        assert "*" not in "."
        assert "*" not in "./"
        assert "*" not in "./src"
        assert "*" not in "src/"

        # Test patterns with wildcards
        assert "*" in "./*"
        assert "*" in "./**"
        assert "*" in "./src/*"
        assert "*" in "./src/**"
        assert "*" in "src/*"
        assert "*" in "src/**"

    def test_has_directory_patterns_in_args(self):
        """Test detection of directory patterns in arguments."""
        # Test with various directory patterns
        test_cases = [
            (["analyze", "."], True),
            (["analyze", "./"], True),
            (["analyze", "./*"], True),
            (["analyze", "./**"], True),
            (["analyze", "./src"], True),
            (["analyze", "src/"], True),
            (["analyze", "file.py"], False),
            (["--dry-run", "analyze"], False),
            (["analyze", "--llm=claude"], False),
        ]

        for args, expected in test_cases:
            with patch('doq.parser.ArgumentParser._is_directory_pattern') as mock_is_dir:
                def mock_is_dir_func(arg):
                    return arg in [".", "./", "./*", "./**", "./src", "src/"]

                mock_is_dir.side_effect = mock_is_dir_func

                parser = ArgumentParser()
                parser.raw_args = args
                result = parser._has_directory_patterns_in_args()
                assert result == expected, f"Failed for args: {args}"

    def test_find_directory_base_from_args(self):
        """Test finding base directory from arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            src_dir = temp_path / "src"
            src_dir.mkdir()

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            # Test current directory patterns
            parser.raw_args = ["analyze", "."]
            base_dir = parser._find_directory_base_from_args()
            assert str(temp_path) in base_dir

            # Test specific directory patterns
            parser.raw_args = ["analyze", "./src"]
            base_dir = parser._find_directory_base_from_args()
            assert "src" in base_dir

    def test_directory_structure_tree_generation(self):
        """Test recursive directory structure tree generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test structure
            (temp_path / "file1.txt").write_text("content1")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file2.py").write_text("def test(): pass")
            (temp_path / "subdir" / "nested").mkdir()
            (temp_path / "subdir" / "nested" / "file3.js").write_text("console.log('hello');")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)
            parser.raw_args = ["analyze", "."]

            tree_output = parser._generate_directory_structure_tree()

            # Should contain all files and directories
            assert "file1.txt" in tree_output
            assert "subdir" in tree_output
            assert "file2.py" in tree_output
            assert "nested" in tree_output
            assert "file3.js" in tree_output

            # Should have proper tree structure
            assert "├──" in tree_output or "└──" in tree_output
            assert "📁" in tree_output  # Directory emoji
            assert "📄" in tree_output  # File emoji

    def test_mixed_files_and_directory_patterns(self):
        """Test combining individual files with directory patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "standalone.py").write_text("# standalone file")
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.py").write_text("def main(): pass")

            # Use the new constructor to inject the working directory
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file:
                with patch('doq.parser.ArgumentParser._is_directory_pattern') as mock_is_dir:
                    with patch('doq.parser.ArgumentParser._process_file') as mock_process_file:
                        with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                            # Setup mocks
                            def is_file_side_effect(arg):
                                return arg == "standalone.py"

                            def is_dir_side_effect(arg):
                                return arg == "./src/*"

                            mock_is_file.side_effect = is_file_side_effect
                            mock_is_dir.side_effect = is_dir_side_effect

                            mock_process_file.return_value = FileInfo(
                                path=str(temp_path / "standalone.py"),
                                is_binary=False,
                                size=50,
                                include_mode="as_file"
                            )

                            mock_scan.return_value = [
                                FileInfo(
                                    path=str(temp_path / "src" / "main.py"),
                                    is_binary=False,
                                    size=100,
                                    include_mode="as_file"
                                )
                            ]

                            # Test mixed arguments
                            args = ["analyze", "standalone.py", "./src/*"]
                            result = parser.parse_args(args)

                            # Should include both individual file and directory files
                            assert len(result.files) == 2


class TestFileInfo:
    """Test cases for FileInfo dataclass."""

    def test_file_info_creation(self):
        """Test FileInfo object creation."""
        file_info = FileInfo(
            path="/test/path.txt",
            is_binary=False,
            size=1024,
            include_mode="full",
            content="test content"
        )

        assert file_info.path == "/test/path.txt"
        assert file_info.is_binary is False
        assert file_info.size == 1024
        assert file_info.include_mode == "full"
        assert file_info.content == "test content"


class TestRequestStructure:
    """Test cases for RequestStructure dataclass."""

    def test_request_structure_creation(self):
        """Test RequestStructure object creation."""
        files = [FileInfo("/test.txt", False, 100, "full")]
        request = RequestStructure(
            text_query="test query",
            provider="openai",
            interactive=True,
            dry_run=False,
            files=files,
            raw_args=["test", "args"]
        )

        assert request.text_query == "test query"
        assert request.provider == "openai"
        assert request.interactive is True
        assert request.dry_run is False
        assert len(request.files) == 1
        assert request.raw_args == ["test", "args"]

    def test_request_structure_defaults(self):
        """Test RequestStructure default values."""
        request = RequestStructure(text_query="test")

        assert request.provider == "claude"
        assert request.interactive is False
        assert request.dry_run is False
        assert len(request.files) == 0
        assert len(request.raw_args) == 0


if __name__ == "__main__":
    pytest.main([__file__])
