"""Базовые тесты парсера аргументов - парсинг текста, флагов и кавычек."""

import pytest
from doq.parser import ArgumentParser


class TestBasicParsing:
    """Тесты базового парсинга аргументов."""

    def setup_method(self):
        """Настройка тестовых данных."""
        self.parser = ArgumentParser()

    def test_simple_text_parsing(self):
        """Тест парсинга простых текстовых аргументов."""
        args = ["hello", "world", "test"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test"
        assert result.provider == "claude"
        assert not result.interactive
        assert not result.dry_run
        assert len(result.files) == 0

    def test_quoted_string_parsing(self):
        """Тест парсинга строк в кавычках."""
        args = ['"hello world"', "test"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test"

    def test_quoted_string_with_spaces(self):
        """Тест парсинга строк в кавычках, которые охватывают несколько аргументов."""
        args = ['"hello', 'world', 'test"', "after"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test after"

    def test_escaped_quotes(self):
        """Тест парсинга строк с экранированными кавычками."""
        args = ['"hello \\"world\\" test"']
        result = self.parser.parse_args(args)

        assert result.text_query == 'hello "world" test'

    def test_single_quotes(self):
        """Тест парсинга строк в одинарных кавычках."""
        args = ["'hello world'", "test"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello world test"

    def test_provider_parameter(self):
        """Тест парсинга параметра провайдера."""
        args = ["--llm=openai", "hello", "world"]
        result = self.parser.parse_args(args)

        assert result.provider == "openai"
        assert result.text_query == "hello world"

    def test_interactive_flag(self):
        """Тест парсинга флага интерактивного режима."""
        args = ["-i", "hello", "world"]
        result = self.parser.parse_args(args)

        assert result.interactive is True
        assert result.text_query == "hello world"

    def test_dry_run_flag(self):
        """Тест парсинга флага dry-run."""
        args = ["--dry-run", "hello", "world"]
        result = self.parser.parse_args(args)

        assert result.dry_run is True
        assert result.text_query == "hello world"

    def test_combined_flags(self):
        """Тест парсинга комбинации флагов."""
        args = ["-i", "--llm=deepseek", "--dry-run", "hello"]
        result = self.parser.parse_args(args)

        assert result.interactive is True
        assert result.dry_run is True
        assert result.provider == "deepseek"
        assert result.text_query == "hello"

    def test_unquoted_russian_command(self):
        """Тест парсинга команды на русском языке без кавычек."""
        args = ["проверь", "содержимое", "файла", "script.py"]
        result = self.parser.parse_args(args)

        assert result.text_query == "проверь содержимое файла script.py"
        assert result.provider == "claude"
        assert not result.interactive
        assert not result.dry_run
        # script.py рассматривается как обычный текст, поскольку не существует
        assert len(result.files) == 0

    def test_unquoted_mixed_language_command(self):
        """Тест парсинга команды со смешанными русским и английским языками."""
        args = ["analyze", "код", "в", "файле", "main.py", "and", "объясни", "логику"]
        result = self.parser.parse_args(args)

        assert result.text_query == "analyze код в файле main.py and объясни логику"
        assert result.provider == "claude"
        assert len(result.files) == 0

    def test_unquoted_command_with_provider_flag(self):
        """Тест парсинга команды на русском с флагом провайдера."""
        args = ["--llm=openai", "переведи", "текст", "на", "английский"]
        result = self.parser.parse_args(args)

        assert result.provider == "openai"
        assert result.text_query == "переведи текст на английский"
        assert len(result.files) == 0

    def test_unquoted_command_with_interactive_flag(self):
        """Тест парсинга команды с флагом интерактивного режима."""
        args = ["-i", "создай", "документацию", "для", "проекта"]
        result = self.parser.parse_args(args)

        assert result.interactive is True
        assert result.text_query == "создай документацию для проекта"
        assert len(result.files) == 0

    def test_unquoted_long_russian_command(self):
        """Тест парсинга длинной команды на русском языке."""
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

    def test_unquoted_command_with_special_characters(self):
        """Тест парсинга команды со специальными символами и пунктуацией."""
        args = ["что", "делает", "функция", "test()", "в", "коде?"]
        result = self.parser.parse_args(args)

        assert result.text_query == "что делает функция test() в коде?"
        assert len(result.files) == 0

    def test_unquoted_command_with_numbers(self):
        """Тест парсинга команды с числами."""
        args = ["найди", "ошибки", "в", "строках", "1-10", "и", "25-30"]
        result = self.parser.parse_args(args)

        assert result.text_query == "найди ошибки в строках 1-10 и 25-30"
        assert len(result.files) == 0

    def test_unquoted_empty_command(self):
        """Тест парсинга пустой команды."""
        args = []
        result = self.parser.parse_args(args)

        assert result.text_query == ""
        assert len(result.files) == 0

    def test_unquoted_single_word_command(self):
        """Тест парсинга команды из одного слова."""
        args = ["помощь"]
        result = self.parser.parse_args(args)

        assert result.text_query == "помощь"
        assert len(result.files) == 0
