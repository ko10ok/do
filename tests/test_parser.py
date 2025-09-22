"""Тесты основных структур данных парсера."""

import pytest
from doq.parser import FileInfo, RequestStructure


class TestFileInfo:
    """Тесты для структуры FileInfo."""

    def test_file_info_creation(self):
        """Тест создания объекта FileInfo."""
        file_info = FileInfo(
            path="/path/to/file.py",
            is_binary=False,
            size=1024,
            include_mode="full",
            content="print('hello')"
        )

        assert file_info.path == "/path/to/file.py"
        assert file_info.is_binary is False
        assert file_info.size == 1024
        assert file_info.include_mode == "full"
        assert file_info.content == "print('hello')"

    def test_file_info_defaults(self):
        """Тест значений по умолчанию для FileInfo."""
        file_info = FileInfo(
            path="/path/to/file.py",
            is_binary=False,
            size=1024,
            include_mode="full"
        )

        assert file_info.content is None


class TestRequestStructure:
    """Тесты для структуры RequestStructure."""

    def test_request_structure_creation(self):
        """Тест создания объекта RequestStructure."""
        files = [
            FileInfo(
                path="/path/to/file.py",
                is_binary=False,
                size=1024,
                include_mode="full"
            )
        ]

        request = RequestStructure(
            text_query="analyze this code",
            provider="claude",
            interactive=True,
            dry_run=False,
            files=files,
            raw_args=["analyze", "this", "code", "file.py"]
        )

        assert request.text_query == "analyze this code"
        assert request.provider == "claude"
        assert request.interactive is True
        assert request.dry_run is False
        assert len(request.files) == 1
        assert request.raw_args == ["analyze", "this", "code", "file.py"]

    def test_request_structure_defaults(self):
        """Тест значений по умолчанию для RequestStructure."""
        request = RequestStructure(text_query="test query")

        assert request.text_query == "test query"
        assert request.provider == "claude"
        assert request.interactive is False
        assert request.dry_run is False
        assert len(request.files) == 0
        assert len(request.raw_args) == 0


if __name__ == "__main__":
    pytest.main([__file__])
