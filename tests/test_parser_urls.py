"""Тесты парсера для обработки URL - определение ссылок, загрузка контента, обработка различных типов содержимого."""

from unittest.mock import Mock, patch

import pytest
from doq.parser import ArgumentParser, FileInfo


class TestURLProcessing:
    """Тесты для обработки URL."""

    def setup_method(self):
        """Настройка тестовых данных."""
        self.parser = ArgumentParser()

    def test_url_detection_valid_urls(self):
        """Тест определения валидных URL."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://example.com/path",
            "https://example.com/path/to/file.txt",
            "http://192.168.1.1",
            "https://localhost:8080",
            "http://sub.domain.com:3000/api/data"
        ]

        for url in valid_urls:
            assert self.parser._is_url(url), f"URL {url} должен быть определен как валидный"

    def test_url_detection_invalid_urls(self):
        """Тест определения невалидных URL."""
        invalid_urls = [
            "ftp://example.com",  # не http/https
            "example.com",  # нет протокола
            "http://",  # неполный URL
            "https://",  # неполный URL
            "not a url",  # обычный текст
            "файл.txt",  # локальный файл
            ""  # пустая строка
        ]

        for url in invalid_urls:
            assert not self.parser._is_url(url), f"URL {url} должен быть определен как невалидный"

    @patch('doq.parser.requests')
    def test_successful_text_url_processing(self, mock_requests):
        """Тест успешной обработки текстового URL."""
        # Настройка мока
        mock_response = Mock()
        mock_response.content = b"Hello, World!"
        mock_response.text = "Hello, World!"
        mock_response.headers = {'content-type': 'text/plain'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Тест
        result = self.parser._process_url("http://example.com/test.txt")

        # Проверки
        assert result is not None
        assert result.path == "http://example.com/test.txt -> test.txt"
        assert not result.is_binary
        assert result.size == 13
        assert result.content is not None
        assert "Hello, World!" in result.content
        mock_requests.get.assert_called_once()

    @patch('doq.parser.requests')
    def test_successful_json_url_processing(self, mock_requests):
        """Тест успешной обработки JSON URL."""
        # Настройка мока
        mock_response = Mock()
        json_content = '{"key": "value"}'
        mock_response.content = json_content.encode()
        mock_response.text = json_content
        mock_response.headers = {'content-type': 'application/json'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Тест
        result = self.parser._process_url("http://api.example.com/data.json")

        # Проверки
        assert result is not None
        assert not result.is_binary
        assert result.content is not None
        assert '{"key": "value"}' in result.content

    @patch('doq.parser.requests')
    def test_binary_url_processing(self, mock_requests):
        """Тест обработки бинарного URL."""
        # Настройка мока
        mock_response = Mock()
        binary_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        mock_response.content = binary_data
        mock_response.headers = {'content-type': 'image/png'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Тест
        result = self.parser._process_url("http://example.com/image.png")

        # Проверки
        assert result is not None
        assert result.is_binary
        assert result.size == len(binary_data)
        # Для бинарных файлов у Claude провайдера используется режим as_file, поэтому content может быть None
        if result.include_mode == "as_file":
            assert result.content is None
        else:
            assert result.content is not None
            assert "binary" in result.content

    @patch('doq.parser.requests')
    @patch('builtins.input', return_value='n')
    def test_large_url_content_rejection(self, mock_input, mock_requests):
        """Тест отклонения большого URL контента."""
        # Настройка мока
        mock_response = Mock()
        large_content = b'x' * (15 * 1024 * 1024)  # 15MB
        mock_response.content = large_content
        mock_response.headers = {'content-type': 'text/plain'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Тест
        result = self.parser._process_url("http://example.com/large.txt")

        # Проверки
        assert result is None
        mock_input.assert_called_once()

    @patch('doq.parser.requests')
    @patch('builtins.input', return_value='y')
    def test_large_url_content_acceptance(self, mock_input, mock_requests):
        """Тест принятия большого URL контента."""
        # Настройка мока
        mock_response = Mock()
        large_content = b'x' * (15 * 1024 * 1024)  # 15MB
        mock_response.content = large_content
        mock_response.text = 'x' * (15 * 1024 * 1024)
        mock_response.headers = {'content-type': 'text/plain'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Тест
        result = self.parser._process_url("http://example.com/large.txt")

        # Проверки
        assert result is not None
        assert result.size == 15 * 1024 * 1024

    @patch('doq.parser.requests')
    def test_url_request_error_handling(self, mock_requests):
        """Тест обработки ошибок при запросе URL."""
        # Настройка мока для ошибки
        mock_requests.get.side_effect = Exception("Network error")

        # Тест
        result = self.parser._process_url("http://example.com/error.txt")

        # Проверки
        assert result is None

    @patch('doq.parser.requests')
    def test_claude_provider_url_as_file_mode(self, mock_requests):
        """Тест режима as_file для Claude провайдера с бинарным URL."""
        # Настройка мока для бинарного содержимого
        mock_response = Mock()
        mock_response.content = b"Test binary content"
        mock_response.headers = {'content-type': 'image/png'}  # Бинарный тип
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Настройка провайдера
        self.parser.provider = "claude"

        # Тест
        result = self.parser._process_url("http://example.com/test.png")

        # Проверки
        assert result is not None
        assert result.include_mode == "as_file"

    @patch('doq.parser.requests')
    def test_non_claude_provider_url_content_mode(self, mock_requests):
        """Тест режима content для не-Claude провайдера с URL."""
        # Настройка мока
        mock_response = Mock()
        mock_response.content = b"Test content"
        mock_response.text = "Test content"
        mock_response.headers = {'content-type': 'text/plain'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Настройка провайдера
        self.parser.provider = "openai"

        # Тест
        result = self.parser._process_url("http://example.com/test.txt")

        # Проверки
        assert result is not None
        assert result.include_mode == "full"
        assert result.content is not None

    def test_url_in_argument_parsing(self):
        """Тест парсинга URL в аргументах."""
        with patch.object(self.parser, '_process_url') as mock_process:
            mock_file_info = FileInfo(
                path="http://example.com -> test.txt",
                is_binary=False,
                size=100,
                include_mode="full",
                content="Test content"
            )
            mock_process.return_value = mock_file_info

            # Тест
            result = self.parser.parse_args(["analyze", "http://example.com/test.txt"])

            # Проверки
            assert len(result.files) == 1
            assert result.files[0].path == "http://example.com -> test.txt"
            assert "analyze" in result.text_query

    def test_multiple_urls_in_arguments(self):
        """Тест парсинга нескольких URL в аргументах."""
        with patch.object(self.parser, '_process_url') as mock_process:
            mock_file_info1 = FileInfo(
                path="http://example.com -> test1.txt",
                is_binary=False,
                size=100,
                include_mode="full",
                content="Content 1"
            )
            mock_file_info2 = FileInfo(
                path="http://example.com -> test2.txt",
                is_binary=False,
                size=200,
                include_mode="full",
                content="Content 2"
            )
            mock_process.side_effect = [mock_file_info1, mock_file_info2]

            # Тест
            result = self.parser.parse_args([
                "compare",
                "http://example.com/test1.txt",
                "with",
                "http://example.com/test2.txt"
            ])

            # Проверки
            assert len(result.files) == 2
            assert "compare" in result.text_query
            assert "with" in result.text_query

    def test_url_fallback_to_text_on_error(self):
        """Тест фоллбэка к тексту при ошибке обработки URL."""
        with patch.object(self.parser, '_process_url', return_value=None):
            # Тест
            result = self.parser.parse_args(["analyze", "http://example.com/error.txt"])

            # Проверки
            assert len(result.files) == 0
            assert "http://example.com/error.txt" in result.text_query

    @patch('doq.parser.requests')
    def test_url_filename_extraction(self, mock_requests):
        """Тест извлечения имени файла из URL."""
        # Настройка мока
        mock_response = Mock()
        mock_response.content = b"Test content"
        mock_response.text = "Test content"
        mock_response.headers = {'content-type': 'text/plain'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        test_cases = [
            ("http://example.com/path/file.txt", "file.txt"),
            ("http://example.com/", "content_from_example_com"),  # Обновлено для соответствия логике замены точек
            ("http://example.com", "content_from_example_com"),   # Обновлено для соответствия логике замены точек
            ("http://example.com/path/", "content_from_example_com")  # Обновлено для соответствия логике замены точек
        ]

        for url, expected_filename in test_cases:
            result = self.parser._process_url(url)
            assert result is not None
            assert expected_filename in result.path

    @patch('doq.parser.requests')
    def test_unicode_decode_error_handling(self, mock_requests):
        """Тест обработки ошибок декодирования Unicode."""
        # Настройка мока
        mock_response = Mock()
        mock_response.content = b'\x80\x81\x82'  # Некорректная UTF-8 последовательность
        mock_response.headers = {'content-type': 'text/plain'}
        mock_requests.get.return_value = mock_response
        mock_response.raise_for_status.return_value = None

        # Исправленная симуляция UnicodeDecodeError при доступе к .text
        def raise_unicode_error(self):
            raise UnicodeDecodeError('utf-8', b'\x80\x81\x82', 0, 1, 'invalid start byte')

        type(mock_response).text = property(raise_unicode_error)

        # Тест
        result = self.parser._process_url("http://example.com/bad_encoding.txt")

        # Проверки
        assert result is not None
        assert result.content is not None
        assert "binary fallback" in result.content

    def test_content_type_detection(self):
        """Тест определения типа контента."""
        test_cases = [
            ("text/plain", False),
            ("text/html", False),
            ("application/json", False),
            ("application/xml", False),
            ("application/javascript", False),
            ("application/x-javascript", False),
            ("image/png", True),
            ("application/pdf", True),
            ("video/mp4", True),
            ("", True),  # Неизвестный тип считается бинарным
        ]

        for content_type, expected_binary in test_cases:
            with patch('doq.parser.requests') as mock_requests:
                mock_response = Mock()
                mock_response.content = b"test"
                mock_response.text = "test"
                mock_response.headers = {'content-type': content_type}
                mock_requests.get.return_value = mock_response
                mock_response.raise_for_status.return_value = None

                result = self.parser._process_url("http://example.com/file")
                assert result is not None
                assert result.is_binary == expected_binary
