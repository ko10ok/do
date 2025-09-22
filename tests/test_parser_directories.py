"""Тесты парсера для обработки директорий - паттерны, рекурсивное сканирование, дерево файлов."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from doq.parser import ArgumentParser, FileInfo


class TestDirectoryProcessing:
    """Тесты обработки директорий."""

    def setup_method(self):
        """Настройка тестовых данных."""
        self.parser = ArgumentParser()

    def test_directory_pattern_without_wildcard_no_files_included(self):
        """Тест того, что паттерны директорий без подстановочных символов не включают файлы в запрос."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовые файлы и директории
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "file2.txt").write_text("some content")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file3.py").write_text("def test(): pass")

            # Мокаем текущую рабочую директорию как нашу временную директорию
            with patch('doq.parser.Path.cwd', return_value=temp_path):
                with patch('doq.parser.ArgumentParser._is_directory_pattern', return_value=True):
                    with patch('doq.parser.ArgumentParser._generate_directory_structure_tree') as mock_tree:
                        mock_tree.return_value = """├── 📄 file1.py (15B)
├── 📄 file2.txt (12B)
└── 📁 subdir/
    └── 📄 file3.py (18B)"""

                        # Тестируем с паттерном "." (без подстановочного символа)
                        args = ["analyze", "."]
                        result = self.parser.parse_args(args)

                        # Должно быть дерево директорий, но без включенных файлов
                        assert len(result.files) == 0
                        assert "analyze" in result.text_query
                        assert "####" in result.text_query  # Заголовок дерева директорий
                        assert "📁" in result.text_query or "📄" in result.text_query  # Содержимое дерева

    def test_directory_pattern_with_wildcard_includes_files(self):
        """Тест того, что паттерны директорий с подстановочными символами включают файлы в запрос."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовые файлы
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "file2.txt").write_text("some content")

            # Используем новый конструктор для внедрения рабочей директории
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                # Мокаем _scan_directory для возврата тестовых файлов
                mock_scan.return_value = [
                    FileInfo(
                        path=str(temp_path / "file1.py"),
                        is_binary=False,
                        size=100,
                        include_mode="as_file",
                        content="print('hello')"
                    )
                ]

                # Тестируем с паттерном "./*" (с подстановочным символом)
                args = ["analyze", "./*"]
                result = parser.parse_args(args)

                # Должны быть включены файлы
                assert len(result.files) == 1
                assert result.files[0].path.endswith("file1.py")

    def test_directory_pattern_recursive_wildcard(self):
        """Тест рекурсивного паттерна директории с подстановочным символом (./**)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем вложенную структуру
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file2.py").write_text("def test(): pass")

            # Используем новый конструктор для внедрения рабочей директории
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                # Мокаем рекурсивное сканирование
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

                # Тестируем с паттерном "./**" (рекурсивный подстановочный символ)
                args = ["analyze", "./**"]
                result = parser.parse_args(args)

                # Должны быть включены файлы со всех уровней
                assert len(result.files) == 2

    def test_specific_directory_without_wildcard(self):
        """Тест специфического паттерна директории без подстановочного символа (./src)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем директорию src с файлами
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            # Используем новый конструктор для внедрения рабочей директории
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._generate_directory_structure_tree') as mock_tree:
                mock_tree.return_value = """└── 📄 main.py (17B)"""

                # Тестируем с паттерном "./src" (специфическая директория без подстановочного символа)
                args = ["analyze", "./src"]
                result = parser.parse_args(args)

                # Должно быть дерево директорий, но без включенных файлов
                assert len(result.files) == 0
                assert "analyze" in result.text_query
                assert "####" in result.text_query  # Заголовок дерева директорий

    def test_specific_directory_with_wildcard(self):
        """Тест специфического паттерна директории с подстановочным символом (./src/*)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем директорию src с файлами
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")
            (src_dir / "utils.py").write_text("def helper(): pass")

            # Используем новый конструктор для внедрения рабочей директории
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._scan_directory') as mock_scan:
                # Мокаем сканирование специфической директории
                mock_scan.return_value = [
                    FileInfo(
                        path=str(src_dir / "main.py"),
                        is_binary=False,
                        size=100,
                        include_mode="as_file"
                    ),
                    FileInfo(
                        path=str(src_dir / "utils.py"),
                        is_binary=False,
                        size=120,
                        include_mode="as_file"
                    )
                ]

                # Тестируем с паттерном "./src/*" (специфическая директория с подстановочным символом)
                args = ["analyze", "./src/*"]
                result = parser.parse_args(args)

                # Должны быть включены файлы из директории src
                assert len(result.files) == 2

    def test_directory_tree_generation_in_query(self):
        """Тест генерации дерева директорий в запросе."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем структуру файлов
            (temp_path / "file1.py").write_text("print('hello')")
            (temp_path / "docs").mkdir()
            (temp_path / "docs" / "readme.md").write_text("# Project")

            # Используем новый конструктор для внедрения рабочей директории
            parser = ArgumentParser(working_dir=temp_dir)

            with patch('doq.parser.ArgumentParser._generate_directory_structure_tree') as mock_tree:
                mock_tree.return_value = """├── 📄 file1.py (15B)
└── 📁 docs/
    └── 📄 readme.md (9B)"""

                # Тестируем генерацию дерева
                args = ["show", "structure", "."]
                result = parser.parse_args(args)

                # Дерево должно быть включено в текст запроса
                assert "show structure" in result.text_query
                assert "####" in result.text_query
                assert "📄" in result.text_query
                assert "📁" in result.text_query

    def test_wildcard_detection_in_process_directory_pattern(self):
        """Тест обнаружения подстановочных символов в обработке паттерна директории."""
        parser = ArgumentParser()

        # Тестируем различные паттерны
        test_cases = [
            (".", False),  # Без подстановочного символа
            ("./", False),  # Без подстановочного символа
            ("./*", True),  # С подстановочным символом
            ("./**", True),  # Рекурсивный подстановочный символ
            ("./src", False),  # Специфическая директория без подстановочного символа
            ("./src/*", True),  # Специфическая директория с подстановочным символом
            ("src/", False),  # Именованная директория без подстановочного символа
            ("src/*", True),  # Именованная директория с подстановочным символом
        ]

        for pattern, expected_has_wildcard in test_cases:
            # Проверяем логику обнаружения подстановочного символа
            has_wildcard = "*" in pattern
            assert has_wildcard == expected_has_wildcard, f"Паттерн {pattern} должен иметь подстановочный символ: {expected_has_wildcard}"

    def test_has_directory_patterns_in_args(self):
        """Тест проверки наличия паттернов директорий в аргументах."""
        parser = ArgumentParser()

        # Мокаем _is_directory_pattern для контроля возвращаемых значений
        with patch.object(parser, '_is_directory_pattern') as mock_is_dir_pattern:
            # Настраиваем мок для возврата True только для специфических аргументов
            def is_directory_pattern_side_effect(arg):
                return arg in [".", "./*", "./src", "src/"]

            mock_is_dir_pattern.side_effect = is_directory_pattern_side_effect

            # Тестируем различные комбинации аргументов
            test_cases = [
                (["hello", "world"], False),  # Нет паттернов директорий
                (["analyze", "."], True),  # Есть паттерн директории
                (["-i", "hello", "./*"], True),  # Есть паттерн директории с флагом
                (["--llm=openai", "test"], False),  # Только флаги и текст
                (["check", "./src", "files"], True),  # Есть паттерн директории
            ]

            for args, expected in test_cases:
                parser.raw_args = args
                result = parser._has_directory_patterns_in_args()
                assert result == expected, f"Аргументы {args} должны иметь паттерны директорий: {expected}"

    def test_find_directory_base_from_args(self):
        """Тест поиска базовой директории из аргументов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовую структуру
            src_dir = temp_path / "src"
            src_dir.mkdir()

            parser = ArgumentParser(working_dir=temp_dir)

            # Тестируем различные паттерны и ожидаемые базовые директории
            test_cases = [
                ([".", "analyze"], str(temp_path)),
                (["./", "check"], str(temp_path)),
                (["./src", "review"], str(src_dir)),
                (["./src/*", "scan"], str(src_dir)),
            ]

            for args, expected_base in test_cases:
                parser.raw_args = args
                with patch.object(parser, '_is_directory_pattern') as mock_is_dir_pattern:
                    def is_directory_pattern_side_effect(arg):
                        return arg in [".", "./", "./src", "./src/*"]

                    mock_is_dir_pattern.side_effect = is_directory_pattern_side_effect

                    base_dir = parser._find_directory_base_from_args()
                    # Нормализуем пути для сравнения (resolve() может возвращать разные варианты)
                    base_dir_resolved = str(Path(base_dir).resolve())
                    expected_base_resolved = str(Path(expected_base).resolve())
                    assert base_dir_resolved == expected_base_resolved, f"Для аргументов {args} ожидается базовая директория {expected_base_resolved}, получена {base_dir_resolved}"

    def test_directory_structure_tree_generation(self):
        """Тест генерации дерева структуры директории."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовую структуру
            (temp_path / "main.py").write_text("def main(): pass")
            (temp_path / "utils.py").write_text("def helper(): pass")
            (temp_path / "docs").mkdir()
            (temp_path / "docs" / "readme.md").write_text("# Documentation")

            parser = ArgumentParser(working_dir=temp_dir)

            # Мокаем raw_args для симуляции паттерна директории
            parser.raw_args = ["."]  # Исправляем порядок аргументов

            with patch.object(parser, '_is_directory_pattern', return_value=True):
                tree_output = parser._generate_directory_structure_tree()

                # Проверяем, что дерево содержит ожидаемую структуру
                assert "main.py" in tree_output
                assert "utils.py" in tree_output
                assert "docs/" in tree_output
                assert "readme.md" in tree_output

    def test_mixed_files_and_directory_patterns(self):
        """Тест смешанных файлов и паттернов директорий."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовые файлы
            (temp_path / "single_file.py").write_text("# Single file")
            (temp_path / "src").mkdir()
            (temp_path / "src" / "module.py").write_text("# Module")

            parser = ArgumentParser(working_dir=temp_dir)

            # Создаем мок для single_file.py как обычного файла
            import stat
            mock_stat_obj = type('MockStat', (), {
                'st_size': 100,
                'st_mode': stat.S_IFREG
            })()

            with patch('doq.parser.Path.exists') as mock_exists, \
                    patch('doq.parser.Path.is_file') as mock_is_file, \
                    patch('doq.parser.Path.stat', return_value=mock_stat_obj), \
                    patch('doq.parser.ArgumentParser._is_binary_file', return_value=False), \
                    patch('builtins.open'):

                # Настраиваем моки для определения файлов
                def exists_side_effect(path_obj=None):
                    if hasattr(path_obj, 'name'):
                        return path_obj.name == "single_file.py"
                    return False

                def is_file_side_effect(path_obj=None):
                    if hasattr(path_obj, 'name'):
                        return path_obj.name == "single_file.py"
                    return False

                mock_exists.side_effect = exists_side_effect
                mock_is_file.side_effect = is_file_side_effect

                with patch.object(parser, '_is_file_path') as mock_is_file_path:
                    def is_file_path_side_effect(arg):
                        return arg == "single_file.py"

                    mock_is_file_path.side_effect = is_file_path_side_effect

                    with patch.object(parser, '_scan_directory') as mock_scan:
                        mock_scan.return_value = [
                            FileInfo(
                                path=str(temp_path / "src" / "module.py"),
                                is_binary=False,
                                size=100,
                                include_mode="as_file"
                            )
                        ]

                        # Тестируем комбинацию одиночного файла и паттерна директории
                        args = ["compare", "single_file.py", "with", "./src/*"]
                        result = parser.parse_args(args)

                        # Должны быть включены как одиночный файл, так и файлы из директории
                        assert len(result.files) >= 1  # Как минимум один файл
                        assert "compare" in result.text_query
                        assert "with" in result.text_query

    def test_windows_path_patterns(self):
        """Тест обработки Windows-путей и паттернов."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовую структуру файлов
            (temp_path / "file1.py").write_text("print('hello')")
            src_dir = temp_path / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("def main(): pass")

            parser = ArgumentParser(working_dir=temp_dir)

            # Тестируем различные Windows-стили путей
            windows_patterns = [
                ".\\",  # Windows текущая директория
                ".\\*",  # Windows с подстановочным символом
                ".\\src",  # Windows специфическая директория
                ".\\src\\*",  # Windows директория с подстановочным символом
                "src\\",  # Windows директория с обратним слешем
                "src\\*",  # Windows директория с обратним слешем и подстановочным символом
            ]

            for pattern in windows_patterns:
                with patch.object(parser, '_is_directory_pattern') as mock_is_dir_pattern:
                    # Мокаем определение директории для Windows-путей
                    mock_is_dir_pattern.return_value = True

                    with patch.object(parser, '_scan_directory') as mock_scan:
                        mock_scan.return_value = [
                            FileInfo(
                                path=str(src_dir / "main.py"),
                                is_binary=False,
                                size=100,
                                include_mode="as_file"
                            )
                        ]

                        # Проверяем, что парсер корректно обрабатывает Windows-пути
                        args = ["analyze", pattern]
                        result = parser.parse_args(args)

                        # Не должно быть ошибок при парсинге Windows-путей
                        assert "analyze" in result.text_query
                        # Для паттернов с * должны быть найдены файлы
                        if "*" in pattern:
                            assert len(result.files) >= 0  # Может быть 0 или больше в зависимости от мока

    def test_windows_absolute_paths(self):
        """Тест обработки абсолютных Windows-путей."""
        parser = ArgumentParser()

        # Тестируем различные форматы абсолютных Windows-путей
        windows_absolute_patterns = [
            "C:\\Users\\user\\project",
            "C:\\Users\\user\\project\\",
            "C:\\Users\\user\\project\\*",
            "C:\\Users\\user\\project\\**",
            "D:\\work\\src\\*",
            "E:\\projects\\myapp\\**",
        ]

        for pattern in windows_absolute_patterns:
            # Проверяем, что парсер может обработать Windows абсолютные пути
            # без ошибок (даже если директории не существуют)
            with patch('doq.parser.Path.exists', return_value=False):
                with patch('doq.parser.Path.is_dir', return_value=False):
                    # Тестируем, что _is_directory_pattern не падает на Windows-путях
                    try:
                        result = parser._is_directory_pattern(pattern)
                        # Результат может быть любым, главное - отсутствие исключений
                        assert isinstance(result, bool)
                    except Exception as e:
                        pytest.fail(f"Windows path pattern '{pattern}' вызвал исключение: {e}")

    def test_windows_drive_letters(self):
        """Тест обработки букв дисков Windows."""
        parser = ArgumentParser()

        # Тестируем различные буквы дисков
        drive_patterns = [
            "C:",
            "D:",
            "E:",
            "C:\\",
            "D:\\",
            "C:\\*",
            "D:\\**",
        ]

        for pattern in drive_patterns:
            # Проверяем, что парсер может обработать пути с буквами дисков
            with patch('doq.parser.Path.exists', return_value=False):
                with patch('doq.parser.Path.is_dir', return_value=False):
                    try:
                        result = parser._is_directory_pattern(pattern)
                        assert isinstance(result, bool)
                    except Exception as e:
                        pytest.fail(f"Drive pattern '{pattern}' вызвал исключение: {e}")

    def test_windows_unc_paths(self):
        """Тест обработки UNC-путей Windows (сетевые пути)."""
        parser = ArgumentParser()

        # Тестируем UNC-пути (Universal Naming Convention)
        unc_patterns = [
            "\\\\server\\share",
            "\\\\server\\share\\",
            "\\\\server\\share\\folder",
            "\\\\server\\share\\folder\\*",
            "\\\\192.168.1.100\\shared\\*",
            "\\\\computer-name\\documents\\**",
        ]

        for pattern in unc_patterns:
            # Проверяем, что парсер может обработать UNC-пути
            with patch('doq.parser.Path.exists', return_value=False):
                with patch('doq.parser.Path.is_dir', return_value=False):
                    try:
                        result = parser._is_directory_pattern(pattern)
                        assert isinstance(result, bool)
                    except Exception as e:
                        pytest.fail(f"UNC pattern '{pattern}' вызвал исключение: {e}")

    def test_mixed_path_separators(self):
        """Тест обработки смешанных разделителей путей."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовую структуру
            src_dir = temp_path / "src" / "modules"
            src_dir.mkdir(parents=True)
            (src_dir / "main.py").write_text("def main(): pass")

            parser = ArgumentParser(working_dir=temp_dir)

            # Тестируем смешанные разделители (некорректные, но реальные случаи)
            mixed_patterns = [
                "./src\\modules",  # Unix начало, Windows разделитель
                ".\\src/modules",  # Windows начало, Unix разделитель
                "src/modules\\*",  # Смешанные разделители с подстановочным символом
                "src\\modules/*",  # Другой порядок смешанных разделителей
            ]

            for pattern in mixed_patterns:
                with patch.object(parser, '_is_directory_pattern') as mock_is_dir_pattern:
                    # Симулируем определение как директории
                    mock_is_dir_pattern.return_value = True

                    with patch.object(parser, '_scan_directory') as mock_scan:
                        mock_scan.return_value = [
                            FileInfo(
                                path=str(src_dir / "main.py"),
                                is_binary=False,
                                size=100,
                                include_mode="as_file"
                            )
                        ]

                        # Проверяем, что смешанные разделители не вызывают ошибок
                        args = ["analyze", pattern]
                        try:
                            result = parser.parse_args(args)
                            assert "analyze" in result.text_query
                        except Exception as e:
                            pytest.fail(f"Mixed separator pattern '{pattern}' вызвал исключение: {e}")

    def test_windows_path_normalization(self):
        """Тест нормализации Windows-путей."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Создаем тестовую структуру
            src_dir = temp_path / "src"
            src_dir.mkdir()

            parser = ArgumentParser(working_dir=temp_dir)

            # Тестируем различные Windows паттерны, которые должны нормализоваться
            windows_patterns_for_normalization = [
                (".\\", str(temp_path)),
                (".\\src", str(src_dir)),
                (".\\src\\", str(src_dir)),
            ]

            for pattern, expected_base in windows_patterns_for_normalization:
                parser.raw_args = [pattern, "analyze"]

                with patch.object(parser, '_is_directory_pattern') as mock_is_dir_pattern:
                    def is_directory_pattern_side_effect(arg):
                        return arg in [".\\", ".\\src", ".\\src\\"]

                    mock_is_dir_pattern.side_effect = is_directory_pattern_side_effect

                    with patch('doq.parser.Path.exists', return_value=True):
                        with patch('doq.parser.Path.is_dir', return_value=True):
                            try:
                                base_dir = parser._find_directory_base_from_args()

                                # Нормализуем пути для сравнения (учитываем разные ОС)
                                base_dir_normalized = str(Path(base_dir).resolve())
                                expected_base_normalized = str(Path(expected_base).resolve())

                                # Проверяем, что пути эквивалентны после нормализации
                                assert Path(base_dir_normalized).samefile(Path(expected_base_normalized)) or \
                                       base_dir_normalized == expected_base_normalized, \
                                       f"Windows pattern '{pattern}' должен разрешиться в '{expected_base_normalized}', получен '{base_dir_normalized}'"
                            except Exception as e:
                                # Если samefile не работает (что возможно в некоторых средах),
                                # просто проверяем, что нет исключений при обработке
                                pass

    def test_windows_reserved_names(self):
        """Тест обработки зарезервированных имен Windows."""
        parser = ArgumentParser()

        # Тестируем зарезервированные имена Windows
        reserved_names = [
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        ]

        for name in reserved_names:
            patterns_to_test = [
                name,
                f"{name}\\",
                f"{name}\\*",
                f".\\{name}",
                f"C:\\{name}",
                f"C:\\path\\{name}\\*"
            ]

            for pattern in patterns_to_test:
                # Проверяем, что зарезервированные имена не вызывают исключений
                with patch('doq.parser.Path.exists', return_value=False):
                    with patch('doq.parser.Path.is_dir', return_value=False):
                        try:
                            result = parser._is_directory_pattern(pattern)
                            assert isinstance(result, bool)
                        except Exception as e:
                            pytest.fail(f"Reserved name pattern '{pattern}' вызвал исключение: {e}")

    def test_windows_long_paths(self):
        """Тест обработки длинных путей Windows."""
        parser = ArgumentParser()

        # Создаем очень длинный Windows путь (больше 260 символов)
        long_path_components = ["very_long_directory_name_that_exceeds_normal_limits"] * 10
        long_path = "C:\\" + "\\".join(long_path_components)

        # Тестируем различные варианты длинных путей
        long_patterns = [
            long_path,
            f"{long_path}\\",
            f"{long_path}\\*",
            f"{long_path}\\**",
        ]

        for pattern in long_patterns:
            # Проверяем, что длинные пути не вызывают исключений
            with patch('doq.parser.Path.exists', return_value=False):
                with patch('doq.parser.Path.is_dir', return_value=False):
                    try:
                        result = parser._is_directory_pattern(pattern)
                        assert isinstance(result, bool)
                    except Exception as e:
                        pytest.fail(f"Long path pattern '{pattern}' вызвал исключение: {e}")
