"""Unit tests for argument parser module."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from doq.parser import ArgumentParser, RequestStructure, FileInfo


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
        # Setup mocks - only test.txt should be treated as a file
        def mock_exists_func():
            return True

        def mock_is_file_func():
            return True

        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_stat.return_value.st_size = 100
        mock_is_binary.return_value = False

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
        assert result.files[0].include_mode == "full"
        assert "test content" in result.text_query
        assert "hello" in result.text_query

    @patch('doq.parser.ArgumentParser._is_binary_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'\x00\x01\x02\x03')
    @patch('doq.parser.Path.stat')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.exists')
    def test_binary_file_processing(self, mock_exists, mock_is_file, mock_stat, mock_open_file, mock_is_binary):
        """Test processing binary files."""
        # Setup mocks - only test.bin should be treated as a file
        def mock_exists_func(self):
            return str(self).endswith('test.bin')

        def mock_is_file_func(self):
            return str(self).endswith('test.bin')

        mock_exists.side_effect = mock_exists_func
        mock_is_file.side_effect = mock_is_file_func
        mock_stat.return_value.st_size = 100
        mock_is_binary.return_value = True

        with patch('doq.parser.ArgumentParser._ask_binary_file_mode', return_value='full'):
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
        # Setup mocks - only large_file.txt should be treated as a file
        def mock_exists_func(self):
            return str(self).endswith('large_file.txt')

        def mock_is_file_func(self):
            return str(self).endswith('large_file.txt')

        mock_exists.side_effect = mock_exists_func
        mock_is_file.side_effect = mock_is_file_func
        mock_stat.return_value.st_size = ArgumentParser.LARGE_FILE_THRESHOLD + 1

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
    def test_large_file_acceptance(self, mock_exists, mock_is_file, mock_stat, mock_input, mock_open_file, mock_is_binary):
        """Test accepting large files."""
        # Setup mocks - only large_file.txt should be treated as a file
        def mock_exists_func(self):
            return str(self).endswith('large_file.txt')

        def mock_is_file_func(self):
            return str(self).endswith('large_file.txt')

        mock_exists.side_effect = mock_exists_func
        mock_is_file.side_effect = mock_is_file_func
        mock_stat.return_value.st_size = ArgumentParser.LARGE_FILE_THRESHOLD + 1
        mock_is_binary.return_value = False

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
        # Create a mock that returns True only for test.txt
        def mock_exists(path):
            return str(path).endswith('test.txt')

        def mock_is_file(path):
            return str(path).endswith('test.txt')

        with patch('doq.parser.Path.exists', side_effect=mock_exists), \
             patch('doq.parser.Path.is_file', side_effect=mock_is_file), \
             patch('doq.parser.Path.stat') as mock_stat, \
             patch('doq.parser.ArgumentParser._is_binary_file', return_value=False):

            mock_stat.return_value.st_size = 100

            args = ["--llm=claude", "hello", "test.txt"]
            result = self.parser.parse_args(args)

            assert len(result.files) == 1
            assert result.files[0].include_mode == "as_file"
            assert "hello" in result.text_query

    def test_complex_argument_parsing(self):
        """Test complex combination of arguments."""
        # Create a mock that returns True only for test.txt
        def mock_exists(path):
            return str(path).endswith('test.txt')

        def mock_is_file(path):
            return str(path).endswith('test.txt')

        with patch('doq.parser.Path.exists', side_effect=mock_exists), \
             patch('doq.parser.Path.is_file', side_effect=mock_is_file), \
             patch('doq.parser.Path.stat') as mock_stat, \
             patch('builtins.open', new_callable=mock_open, read_data="file content"), \
             patch('doq.parser.ArgumentParser._is_binary_file', return_value=False):

            mock_stat.return_value.st_size = 100

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
        with patch('doq.parser.Path.exists', return_value=True), \
             patch('doq.parser.Path.is_file', return_value=True), \
             patch('doq.parser.Path.stat') as mock_stat, \
             patch('builtins.open', new_callable=mock_open, read_data="# Python code\nprint('Hello')"), \
             patch('doq.parser.ArgumentParser._is_binary_file', return_value=False):

            mock_stat.return_value.st_size = 100

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
        with patch('doq.parser.Path.exists', return_value=True), \
             patch('doq.parser.Path.is_file', return_value=True), \
             patch('doq.parser.Path.stat') as mock_stat, \
             patch('builtins.open', new_callable=mock_open, read_data="# Code content"), \
             patch('doq.parser.ArgumentParser._is_binary_file', return_value=False):

            mock_stat.return_value.st_size = 100

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
