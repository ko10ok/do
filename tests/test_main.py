"""Unit tests for main CLI module."""

from io import StringIO
from unittest.mock import Mock, patch

import pytest

from doq.main import main, print_dry_run_info
from doq.parser import FileInfo, RequestStructure


class TestMainFunction:
    """Test cases for main CLI function."""

    @patch('doq.main.ArgumentParser')
    @patch('doq.main.ProviderFactory')
    def test_main_basic_usage(self, mock_factory, mock_parser_class):
        """Test basic usage of main function."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        request = RequestStructure(
            text_query="test query",
            provider="claude",
            interactive=False,
            dry_run=False
        )
        mock_parser.parse_args.return_value = request

        mock_provider = Mock()
        mock_provider.send_request.return_value = iter(["Hello", " world"])
        mock_factory_instance = Mock()
        mock_factory_instance.create_provider.return_value = mock_provider
        mock_factory.return_value = mock_factory_instance

        # Test
        with patch('sys.stdout', new=StringIO()):
            result = main(["test", "query"])

        assert result == 0
        mock_parser.parse_args.assert_called_once_with(["test", "query"])
        mock_factory_instance.create_provider.assert_called_once_with("claude")
        mock_provider.send_request.assert_called_once_with(request)

    def test_main_no_args(self):
        """Test main function with no arguments shows help."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = main([])

        assert result == 1
        output = mock_stdout.getvalue()
        assert "Usage:" in output
        assert "Options:" in output
        assert "Examples:" in output

    @patch('doq.main.ArgumentParser')
    def test_main_dry_run_mode(self, mock_parser_class):
        """Test main function in dry-run mode."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        request = RequestStructure(
            text_query="test query",
            provider="claude",
            dry_run=True
        )
        mock_parser.parse_args.return_value = request

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = main(["--dry-run", "test"])

        assert result == 0
        output = mock_stdout.getvalue()
        assert "DRY RUN" in output
        assert "test query" in output

    @patch('doq.main.ArgumentParser')
    @patch('builtins.input', return_value='n')
    def test_main_interactive_cancelled(self, mock_input, mock_parser_class):
        """Test main function with interactive mode cancelled."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        request = RequestStructure(
            text_query="test query",
            interactive=True
        )
        mock_parser.parse_args.return_value = request

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = main(["-i", "test"])

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Request cancelled" in output
        mock_input.assert_called_once()

    @patch('doq.main.ArgumentParser')
    @patch('doq.main.ProviderFactory')
    @patch('builtins.input', return_value='y')
    def test_main_interactive_confirmed(self, mock_input, mock_factory, mock_parser_class):
        """Test main function with interactive mode confirmed."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        request = RequestStructure(
            text_query="test query",
            interactive=True
        )
        mock_parser.parse_args.return_value = request

        mock_provider = Mock()
        mock_provider.send_request.return_value = iter(["Response"])
        mock_factory_instance = Mock()
        mock_factory_instance.create_provider.return_value = mock_provider
        mock_factory.return_value = mock_factory_instance

        with patch('sys.stdout', new=StringIO()):
            result = main(["-i", "test"])

        assert result == 0
        mock_input.assert_called_once()
        mock_provider.send_request.assert_called_once()

    @patch('doq.main.ArgumentParser')
    def test_main_parser_error(self, mock_parser_class):
        """Test main function handles parser errors."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse_args.side_effect = ValueError("Test error")

        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            result = main(["test"])

        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Test error" in error_output

    @patch('doq.main.ArgumentParser')
    @patch('doq.main.ProviderFactory')
    def test_main_provider_error(self, mock_factory, mock_parser_class):
        """Test main function handles provider errors."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        request = RequestStructure(text_query="test")
        mock_parser.parse_args.return_value = request

        mock_factory_instance = Mock()
        mock_factory_instance.create_provider.side_effect = ValueError("Provider error")
        mock_factory.return_value = mock_factory_instance

        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            result = main(["test"])

        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Provider error" in error_output

    @patch('doq.main.ArgumentParser')
    @patch('doq.main.ProviderFactory')
    def test_main_keyboard_interrupt(self, mock_factory, mock_parser_class):
        """Test main function handles keyboard interrupt."""
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        request = RequestStructure(text_query="test")
        mock_parser.parse_args.return_value = request

        mock_provider = Mock()
        mock_provider.send_request.side_effect = KeyboardInterrupt()
        mock_factory_instance = Mock()
        mock_factory_instance.create_provider.return_value = mock_provider
        mock_factory.return_value = mock_factory_instance

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = main(["test"])

        assert result == 130
        output = mock_stdout.getvalue()
        assert "interrupted by user" in output


class TestPrintDryRunInfo:
    """Test cases for print_dry_run_info function."""

    def test_print_dry_run_basic(self):
        """Test printing dry run info for basic request."""
        request = RequestStructure(
            text_query="test query",
            provider="claude",
            raw_args=["test", "query"]
        )

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            print_dry_run_info(request)

        output = mock_stdout.getvalue()
        assert "DRY RUN" in output
        assert "Provider: claude" in output
        assert "test query" in output
        assert "test query" in output

    def test_print_dry_run_with_files(self):
        """Test printing dry run info with files."""
        files = [
            FileInfo(
                path="/test/file.txt",
                is_binary=False,
                size=1024,
                include_mode="full"
            ),
            FileInfo(
                path="/test/binary.bin",
                is_binary=True,
                size=2048,
                include_mode="truncated"
            )
        ]

        request = RequestStructure(
            text_query="test query",
            provider="openai",
            interactive=True,
            files=files,
            raw_args=["test", "file.txt", "binary.bin"]
        )

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            print_dry_run_info(request)

        output = mock_stdout.getvalue()
        assert "Files to be included:" in output
        assert "/test/file.txt" in output
        assert "/test/binary.bin" in output
        assert "1024 bytes" in output
        assert "2048 bytes" in output
        assert "Binary: False" in output
        assert "Binary: True" in output
        assert "Include mode: full" in output
        assert "Include mode: truncated" in output

    def test_print_dry_run_complex_args(self):
        """Test printing dry run info with complex arguments."""
        request = RequestStructure(
            text_query="complex query with quotes",
            provider="deepseek",
            interactive=True,
            dry_run=True,
            raw_args=["-i", "--llm=deepseek", '"complex query"', "with", "quotes", "--dry-run"]
        )

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            print_dry_run_info(request)

        output = mock_stdout.getvalue()
        assert "Provider: deepseek" in output
        assert "Interactive mode: True" in output
        assert "complex query with quotes" in output
        assert '"-i"' in output or "-i" in output
        assert '"complex query"' in output


class TestCLIIntegration:
    """Integration tests for CLI components."""

    @patch('doq.main.ProviderFactory')
    def test_end_to_end_simple_query(self, mock_factory):
        """Test end-to-end simple query processing."""
        mock_provider = Mock()
        mock_provider.send_request.return_value = iter(["Hello", " world", "!"])
        mock_factory_instance = Mock()
        mock_factory_instance.create_provider.return_value = mock_provider
        mock_factory.return_value = mock_factory_instance

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = main(["Hello", "world"])

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Hello world!" in output

    @patch('doq.main.ProviderFactory')
    def test_end_to_end_with_provider(self, mock_factory):
        """Test end-to-end with specific provider."""
        mock_provider = Mock()
        mock_provider.send_request.return_value = iter(["OpenAI response"])
        mock_factory_instance = Mock()
        mock_factory_instance.create_provider.return_value = mock_provider
        mock_factory.return_value = mock_factory_instance

        with patch('sys.stdout', new=StringIO()):
            result = main(["--llm=openai", "test", "query"])

        assert result == 0
        mock_factory_instance.create_provider.assert_called_once_with("openai")


if __name__ == "__main__":
    pytest.main([__file__])
