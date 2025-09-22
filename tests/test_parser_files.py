"""Тесты парсера для обработки файлов - загрузка, бинарные файлы, большие файлы."""

import stat
from unittest.mock import mock_open, patch

from doq.parser import ArgumentParser


class TestFileProcessing:
    """Тесты обработки файлов."""

    def setup_method(self):
        """Настройка тестовых данных."""
        self.parser = ArgumentParser()

    @patch('doq.parser.ArgumentParser._is_binary_file')
    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    @patch('doq.parser.Path.stat')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.exists')
    def test_text_file_processing(self, mock_exists, mock_is_file, mock_stat, mock_open_file, mock_is_binary):
        """Тест обработки текстовых файлов."""
        # Создаем mock объект stat с st_mode для вызовов is_dir()
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Режим обычного файла
        })()
        mock_stat.return_value = mock_stat_obj

        # Настройка моков - только test.txt должен рассматриваться как файл
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_binary.return_value = False

        # Мокаем определение паттерна директории, чтобы вернуть False для test.txt
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            # Только test.txt существует
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg == "test.txt"

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["hello", "test.txt"]
                result = self.parser.parse_args(args)

        assert len(result.files) == 1
        assert result.files[0].path.endswith("test.txt")
        assert not result.files[0].is_binary
        assert result.files[0].include_mode == "as_file"  # Провайдер Claude использует режим as_file
        assert "hello" in result.text_query

    @patch('doq.parser.ArgumentParser._is_binary_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'\x00\x01\x02\x03')
    @patch('doq.parser.Path.stat')
    @patch('doq.parser.Path.is_file')
    @patch('doq.parser.Path.exists')
    def test_binary_file_processing(self, mock_exists, mock_is_file, mock_stat, mock_open_file, mock_is_binary):
        """Тест обработки бинарных файлов."""
        # Создаем mock объект stat с st_mode для вызовов is_dir()
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Режим обычного файла
        })()
        mock_stat.return_value = mock_stat_obj

        # Настройка моков - только test.bin должен рассматриваться как файл
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_binary.return_value = True

        # Мокаем определение паттерна директории, чтобы вернуть False для test.bin
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
        """Тест отклонения больших файлов."""
        # Создаем mock объект stat с st_mode для вызовов is_dir()
        mock_stat_obj = type('MockStat', (), {
            'st_size': ArgumentParser.LARGE_FILE_THRESHOLD + 1,
            'st_mode': stat.S_IFREG  # Режим обычного файла
        })()
        mock_stat.return_value = mock_stat_obj

        # Настройка моков с использованием return_value вместо side_effect
        mock_exists.return_value = True
        mock_is_file.return_value = True

        # Мокаем определение паттерна директории, чтобы вернуть False для large_file.txt
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
        """Тест принятия больших файлов."""
        # Создаем mock объект stat с st_mode для вызовов is_dir()
        mock_stat_obj = type('MockStat', (), {
            'st_size': ArgumentParser.LARGE_FILE_THRESHOLD + 1,
            'st_mode': stat.S_IFREG  # Режим обычного файла
        })()
        mock_stat.return_value = mock_stat_obj

        # Настройка моков с использованием return_value вместо side_effect
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_binary.return_value = False

        # Мокаем определение паттерна директории, чтобы вернуть False для large_file.txt
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
        """Тест различения путей к файлам от обычных аргументов."""
        # Несуществующий файл должен рассматриваться как обычный аргумент
        args = ["hello", "nonexistent.txt"]
        result = self.parser.parse_args(args)

        assert result.text_query == "hello nonexistent.txt"
        assert len(result.files) == 0

    def test_claude_provider_file_mode(self):
        """Тест того, что провайдер Claude использует файловый режим для поддерживаемых файлов."""
        # Создаем mock объект stat с st_mode
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Режим обычного файла
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

    def test_unquoted_russian_with_real_file(self):
        """Тест парсинга команды на русском с реальным файлом."""
        # Создаем mock объект stat
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Режим обычного файла - должно быть целым числом
        })()

        with patch('doq.parser.Path.exists') as mock_exists, \
                patch('doq.parser.Path.is_file') as mock_is_file, \
                patch('doq.parser.Path.is_dir') as mock_is_dir, \
                patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                patch('builtins.open', new_callable=mock_open, read_data="# Python code\nprint('Hello')"), \
                patch('doq.parser.ArgumentParser._is_binary_file', return_value=False):

            mock_exists.side_effect = lambda: "./file.py" in str(mock_exists.return_value)
            mock_is_file.side_effect = lambda: "./file.py" in str(mock_is_file.return_value)
            mock_is_dir.side_effect = lambda: False

            # Мокаем _is_file_path, чтобы возвращать True только для ./file.py
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
                # Для провайдера Claude файл отправляется как вложение (режим as_file)
                assert result.files[0].include_mode == "as_file"
                # Содержимое не включается в text_query для Claude
                assert "# Python code" not in result.text_query

    def test_unquoted_command_with_multiple_files(self):
        """Тест парсинга команды с несколькими файлами."""
        # Создаем mock объект stat с st_mode для вызовов is_dir()
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Режим обычного файла
        })()

        with patch('doq.parser.Path.exists', return_value=True), \
                patch('doq.parser.Path.is_file', return_value=True), \
                patch('doq.parser.Path.is_dir', return_value=False), \
                patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                patch('builtins.open', new_callable=mock_open, read_data="# Code content"), \
                patch('doq.parser.ArgumentParser._is_binary_file', return_value=False), \
                patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            # Мокаем _is_file_path, чтобы возвращать True только для .py и .js файлов
            with patch('doq.parser.ArgumentParser._is_file_path') as mock_is_file_path:
                def is_file_path_side_effect(arg):
                    return arg.endswith(('.py', '.js'))

                mock_is_file_path.side_effect = is_file_path_side_effect

                args = ["сравни", "main.py", "и", "utils.js", "найди", "различия"]
                result = self.parser.parse_args(args)

                assert "сравни" in result.text_query
                assert "найди различия" in result.text_query
                assert len(result.files) == 2
                # Файлы должны быть включены в текстовое содержимое,
                # поскольку провайдер по умолчанию - claude (режим as_file)

    def test_complex_argument_parsing(self):
        """Тест сложной комбинации аргументов."""
        # Создаем mock объект stat с st_mode
        mock_stat_obj = type('MockStat', (), {
            'st_size': 100,
            'st_mode': stat.S_IFREG  # Режим обычного файла
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

    def test_unquoted_command_with_path_separators(self):
        """Тест парсинга команды с путями файлов, содержащими разделители."""
        # Мокаем определение паттерна директории, чтобы предотвратить нежелательную генерацию дерева директорий
        with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=False):
            args = ["проанализируй", "файл", "./src/utils.py", "и", "покажи", "функции"]
            result = self.parser.parse_args(args)

            assert result.text_query == "проанализируй файл ./src/utils.py и покажи функции"
            assert "./src/utils.py" in result.text_query
            assert len(result.files) == 0  # Файл не существует, рассматривается как текст
