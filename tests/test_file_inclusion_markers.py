"""Тесты для проверки включения файлов в тело запроса и маркера '### file end ###'."""

import tempfile
import os
from unittest.mock import patch
from io import StringIO
import sys

from doq.parser import ArgumentParser
from doq.main import main, print_dry_run_info


class TestFileInclusionAndMarkers:
    """Тесты для проверки включения файлов в тело запроса."""

    def test_file_included_in_body_with_openai_provider(self):
        """Тест включения файла в тело запроса для провайдера OpenAI."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовый файл
            file_path = os.path.join(temp_dir, "test.py")
            test_content = "def hello():\n    print('Hello World')"
            with open(file_path, 'w') as f:
                f.write(test_content)

            # Создаем парсер с OpenAI провайдером (не поддерживает файлы)
            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=openai", "analyze", "this", "code", file_path]
            result = parser.parse_args(args)

            # Проверяем, что файл включен в тело запроса
            assert len(result.files) == 1
            assert result.files[0].include_mode != "as_file"
            assert result.files[0].content is not None

            # Проверяем, что содержимое файла есть в текстовом запросе
            assert test_content in result.text_query
            assert f"### {file_path} ###" in result.text_query

            # Проверяем наличие маркера окончания файла
            assert "### file end ###" in result.text_query

            # Проверяем количество маркеров
            file_end_count = result.text_query.count("### file end ###")
            inlined_files = [f for f in result.files if f.include_mode != "as_file" and f.content]
            assert file_end_count == len(inlined_files)

    def test_file_not_included_in_body_with_claude_provider(self):
        """Тест НЕ включения файла в тело запроса для провайдера Claude."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовый файл
            file_path = os.path.join(temp_dir, "test.py")
            test_content = "def hello():\n    print('Hello World')"
            with open(file_path, 'w') as f:
                f.write(test_content)

            # Создаем парсер с Claude провайдером (поддерживает файлы)
            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=claude", "analyze", "this", "code", file_path]
            result = parser.parse_args(args)

            # Проверяем, что файл НЕ включен в тело запроса
            assert len(result.files) == 1
            assert result.files[0].include_mode == "as_file"
            assert result.files[0].content is None

            # Проверяем, что содержимое файла НЕТ в текстовом запросе
            assert test_content not in result.text_query

            # Проверяем отсутствие маркеров окончания файла
            assert "### file end ###" not in result.text_query

    def test_multiple_files_included_in_body(self):
        """Тест включения нескольких файлов в тело запроса."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем несколько тестовых файлов
            files_content = {
                "file1.py": "def func1():\n    return 1",
                "file2.py": "def func2():\n    return 2",
                "file3.js": "function func3() {\n    return 3;\n}"
            }

            file_paths = []
            for filename, content in files_content.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                file_paths.append(file_path)

            # Создаем парсер с DeepSeek провайдером (не поддерживает файлы)
            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=deepseek", "analyze", "these", "files"] + file_paths
            result = parser.parse_args(args)

            # Проверяем, что все файлы включены в тело запроса
            assert len(result.files) == 3
            for file_info in result.files:
                assert file_info.include_mode != "as_file"
                assert file_info.content is not None

            # Проверяем, что содержимое всех файлов есть в текстовом запросе
            for content in files_content.values():
                assert content in result.text_query

            # Проверяем количество маркеров окончания файлов
            file_end_count = result.text_query.count("### file end ###")
            assert file_end_count == 3

            # Проверяем порядок файлов и маркеров
            for i, (filename, content) in enumerate(files_content.items()):
                # Проверяем, что после содержимого каждого файла идет маркер
                content_index = result.text_query.find(content)
                assert content_index != -1

                # Находим следующий маркер после содержимого файла
                next_marker_index = result.text_query.find("### file end ###", content_index)
                assert next_marker_index != -1

    def test_binary_file_inclusion(self):
        """Тест включения бинарного файла в тело запроса."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем бинарный файл
            file_path = os.path.join(temp_dir, "binary_test.bin")
            binary_data = b'\x00\x01\x02\x03\xFF\xFE\xFD'
            with open(file_path, 'wb') as f:
                f.write(binary_data)

            parser = ArgumentParser(working_dir=temp_dir)

            # Мокаем пользовательский ввод для бинарного файла
            with patch('builtins.input', return_value='f'):  # 'f' для full
                args = ["--llm=openai", "analyze", "binary", "file", file_path]
                result = parser.parse_args(args)

            # Проверяем, что бинарный файл включен
            assert len(result.files) == 1
            assert result.files[0].is_binary is True
            assert result.files[0].include_mode != "as_file"
            assert result.files[0].content is not None

            # Проверяем наличие hex-данных в запросе
            assert "binary" in result.text_query
            assert hex(binary_data[0])[2:].zfill(2) in result.text_query.lower()

            # Проверяем наличие маркера окончания файла
            assert "### file end ###" in result.text_query

    def test_url_content_inclusion(self):
        """Тест включения содержимого URL в тело запроса."""
        with patch('doq.parser.requests') as mock_requests:
            # Мокаем ответ от URL
            mock_response = mock_requests.get.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {'content-type': 'text/plain'}
            mock_response.content = b"URL content example"
            mock_response.text = "URL content example"

            parser = ArgumentParser()

            # Для OpenAI провайдера (не поддерживает файлы)
            args = ["--llm=openai", "analyze", "this", "url", "https://example.com/test.txt"]
            result = parser.parse_args(args)

            # Проверяем, что URL контент включен в тело запроса
            assert len(result.files) == 1
            assert result.files[0].include_mode != "as_file"
            assert result.files[0].content is not None
            assert "URL content example" in result.text_query

            # Проверяем наличие маркера окончания файла
            assert "### file end ###" in result.text_query


class TestDryRunWithFileMarkers:
    """Тесты для проверки вывода при --dry-run."""

    def test_dry_run_shows_file_inclusion_info(self):
        """Тест отображения информации о включении файлов при --dry-run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовый файл
            file_path = os.path.join(temp_dir, "test.py")
            test_content = "def test():\n    pass"
            with open(file_path, 'w') as f:
                f.write(test_content)

            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=openai", "--dry-run", "analyze", file_path]
            result = parser.parse_args(args)

            # Проверяем, что dry_run установлен
            assert result.dry_run is True

            # Проверяем, что файл будет включен в тело запроса
            assert len(result.files) == 1
            assert result.files[0].include_mode != "as_file"

            # Проверяем, что маркер окончания файла присутствует в финальном запросе
            assert "### file end ###" in result.text_query

    def test_dry_run_output_format(self):
        """Тест формата вывода при --dry-run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовый файл
            file_path = os.path.join(temp_dir, "example.py")
            test_content = "print('Hello, World!')"
            with open(file_path, 'w') as f:
                f.write(test_content)

            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=openai", "--dry-run", "explain", "this", "code", file_path]
            result = parser.parse_args(args)

            # Перехватываем stdout для проверки вывода
            captured_output = StringIO()

            # Мокаем ValidationResult для print_dry_run_info
            class MockValidationResult:
                warnings = []
                errors = []
                file_count = 1
                text_files = 1
                binary_files = 0
                total_size_bytes = len(test_content)

            mock_validation = MockValidationResult()

            with patch('sys.stdout', captured_output):
                print_dry_run_info(result, mock_validation)

            output = captured_output.getvalue()

            # Проверяем ключевые элементы вывода
            assert "DRY RUN - Request Information" in output
            assert "Provider: openai" in output
            assert "Files to be included:" in output
            assert "example.py" in output
            assert "Include mode:" in output
            assert "Final query text:" in output

            # Проверяем, что в финальном запросе есть маркер окончания файла
            assert "### file end ###" in result.text_query

    def test_dry_run_multiple_files_output(self):
        """Тест вывода при --dry-run с несколькими файлами."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем несколько файлов
            files_data = [
                ("file1.py", "def func1(): pass"),
                ("file2.js", "function func2() {}"),
                ("data.txt", "Some text data")
            ]

            file_paths = []
            for filename, content in files_data:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                file_paths.append(file_path)

            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=deepseek", "--dry-run", "analyze", "all", "files"] + file_paths
            result = parser.parse_args(args)

            # Проверяем количество файлов
            assert len(result.files) == 3

            # Проверяем, что все файлы будут включены в тело запроса
            for file_info in result.files:
                assert file_info.include_mode != "as_file"

            # Проверяем количество маркеров окончания файлов
            file_end_count = result.text_query.count("### file end ###")
            assert file_end_count == 3

            # Проверяем, что содержимое всех файлов присутствует
            for _, content in files_data:
                assert content in result.text_query

    def test_dry_run_with_claude_provider_no_inline(self):
        """Тест --dry-run с Claude провайдером (файлы как вложения)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовый файл
            file_path = os.path.join(temp_dir, "test.py")
            test_content = "def test(): return True"
            with open(file_path, 'w') as f:
                f.write(test_content)

            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=claude", "--dry-run", "review", "code", file_path]
            result = parser.parse_args(args)

            # Проверяем, что файл НЕ включен в тело запроса
            assert len(result.files) == 1
            assert result.files[0].include_mode == "as_file"
            assert result.files[0].content is None

            # Проверяем отсутствие маркеров окончания файла
            assert "### file end ###" not in result.text_query

            # Проверяем, что содержимое файла НЕ включено в текст запроса
            assert test_content not in result.text_query

    def test_file_end_marker_position(self):
        """Тест корректного позиционирования маркера окончания файла."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем файл с определенным содержимым
            file_path = os.path.join(temp_dir, "position_test.py")
            test_content = "def position_test():\n    return 'marker test'"
            with open(file_path, 'w') as f:
                f.write(test_content)

            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=openai", "test", "marker", "position", file_path]
            result = parser.parse_args(args)

            # Находим позицию содержимого файла
            content_start = result.text_query.find(test_content)
            assert content_start != -1

            # Находим позицию маркера окончания файла
            marker_pos = result.text_query.find("### file end ###")
            assert marker_pos != -1

            # Проверяем, что маркер идет ПОСЛЕ содержимого файла
            assert marker_pos > content_start + len(test_content)

            # Проверяем, что между содержимым файла и маркером есть символ новой строки
            text_between = result.text_query[content_start + len(test_content):marker_pos]
            assert '\n' in text_between

    def test_dry_run_query_shows_file_end_markers(self):
        """Тест показа маркеров окончания файлов в запросе при --dry-run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем файл
            file_path = os.path.join(temp_dir, "marker_test.py")
            test_content = "def marker_test():\n    return 'test'"
            with open(file_path, 'w') as f:
                f.write(test_content)

            parser = ArgumentParser(working_dir=temp_dir)
            args = ["--llm=openai", "--dry-run", "check", "markers", file_path]
            result = parser.parse_args(args)

            # Перехватываем stdout
            captured_output = StringIO()

            # Мокаем ValidationResult
            class MockValidationResult:
                warnings = []
                errors = []
                file_count = 1
                text_files = 1
                binary_files = 0
                total_size_bytes = len(test_content)

            mock_validation = MockValidationResult()

            with patch('sys.stdout', captured_output):
                print_dry_run_info(result, mock_validation)

            output = captured_output.getvalue()

            # Проверяем, что маркер окончания файла виден в выводе финального запроса
            assert "### file end ###" in output
            assert test_content in output
