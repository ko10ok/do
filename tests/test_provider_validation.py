"""Тесты для валидации провайдеров LLM."""

from io import StringIO
from unittest.mock import patch

import pytest

from doq.main import main
from doq.parser import ArgumentParser


class TestProviderValidation:
    """Тесты для проверки валидации провайдеров."""

    def test_invalid_provider_raises_error(self):
        """Тест ошибки при указании неподдерживаемого провайдера."""
        parser = ArgumentParser()

        invalid_providers = [
            "gpt4",
            "chatgpt",
            "anthropic",
            "gemini",
            "llama",
            "invalid_provider",
            "test123"
        ]

        for invalid_provider in invalid_providers:
            args = [f"--llm={invalid_provider}", "test", "query"]

            with pytest.raises(ValueError) as exc_info:
                parser.parse_args(args)

            error_msg = str(exc_info.value)
            assert f"Unknown provider '{invalid_provider}'" in error_msg
            assert "Available providers: claude, deepseek, openai" in error_msg

    def test_valid_providers_work(self):
        """Тест корректной работы поддерживаемых провайдеров."""
        parser = ArgumentParser()

        valid_providers = ["claude", "openai", "deepseek"]

        for provider in valid_providers:
            args = [f"--llm={provider}", "test", "query"]
            result = parser.parse_args(args)
            assert result.provider == provider

    def test_case_sensitivity(self):
        """Тест чувствительности к регистру."""
        parser = ArgumentParser()

        # Проверяем, что неправильный регистр вызывает ошибку
        case_variants = ["Claude", "CLAUDE", "OpenAI", "OPENAI", "DeepSeek", "DEEPSEEK"]

        for variant in case_variants:
            args = [f"--llm={variant}", "test", "query"]

            with pytest.raises(ValueError) as exc_info:
                parser.parse_args(args)

            assert f"Unknown provider '{variant}'" in str(exc_info.value)

    def test_main_function_provider_error_handling(self):
        """Тест обработки ошибки провайдера в main функции."""
        captured_stderr = StringIO()

        with patch('sys.stderr', captured_stderr):
            exit_code = main(["--llm=invalid", "test", "query"])

        # Проверяем код выхода с ошибкой
        assert exit_code == 1

        # Проверяем сообщение об ошибке
        error_output = captured_stderr.getvalue()
        assert "Error:" in error_output
        assert "Unknown provider 'invalid'" in error_output

    def test_provider_error_with_file_arguments(self):
        """Тест ошибки провайдера при наличии файловых аргументов."""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовый файл
            file_path = f"{temp_dir}/test.py"
            with open(file_path, 'w') as f:
                f.write("def test(): pass")

            parser = ArgumentParser(working_dir=temp_dir)

            # Проверяем ошибку даже при наличии файлов
            with pytest.raises(ValueError) as exc_info:
                parser.parse_args(["--llm=badprovider", "analyze", file_path])

            assert "Unknown provider 'badprovider'" in str(exc_info.value)

    def test_provider_error_in_dry_run_mode(self):
        """Тест ошибки провайдера в режиме dry-run."""
        parser = ArgumentParser()

        # Ошибка должна возникать до выполнения dry-run
        with pytest.raises(ValueError) as exc_info:
            parser.parse_args(["--llm=unknown", "--dry-run", "test", "query"])

        assert "Unknown provider 'unknown'" in str(exc_info.value)

    def test_empty_provider_name_error(self):
        """Тест ошибки при пустом имени провайдера."""
        parser = ArgumentParser()

        with pytest.raises(ValueError) as exc_info:
            parser.parse_args(["--llm=", "test", "query"])

        assert "Unknown provider ''" in str(exc_info.value)

    def test_provider_with_special_characters(self):
        """Тест ошибки при использовании специальных символов в имени провайдера."""
        parser = ArgumentParser()

        special_providers = ["claude@", "openai!", "deep-seek", "claude.ai", "openai/gpt"]

        for special_provider in special_providers:
            with pytest.raises(ValueError) as exc_info:
                parser.parse_args([f"--llm={special_provider}", "test", "query"])

            assert f"Unknown provider '{special_provider}'" in str(exc_info.value)
