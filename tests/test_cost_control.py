"""Тесты для функции cost_control."""

from unittest.mock import patch

from doq.parser import FileInfo
from doq.validator import (CostControlLimits, EnhancedRequestValidator,
                           ValidationLimits)


class TestCostControl:
    """Тесты для функциональности cost_control."""

    def setup_method(self):
        """Настройка тестовых данных."""
        self.limits = ValidationLimits()
        self.cost_limits = CostControlLimits()
        self.validator = EnhancedRequestValidator(self.limits, self.cost_limits)

    def test_cost_control_defaults(self):
        """Тест значений по умолчанию для cost_control."""
        assert self.cost_limits.warn_token_threshold == 20000
        assert self.cost_limits.block_token_threshold == 50000
        assert self.cost_limits.show_cost_estimates is True

    def test_cost_estimates_shown_for_large_requests(self):
        """Тест отображения оценки стоимости для больших запросов."""
        # Создаем файлы с большим содержимым для превышения порога в 1000 токенов
        large_content = "x" * 10000  # ~2500+ токенов
        files = [
            FileInfo(
                path="test1.py",
                is_binary=False,
                size=len(large_content),
                include_mode="as_file",
                content=large_content
            )
        ]

        result = self.validator.validate_request_enhanced(files, "Analyze this large file")

        # Проверяем, что есть предупреждение с оценкой стоимости
        cost_warnings = [w for w in result.warnings if "Estimated cost:" in w]
        assert len(cost_warnings) > 0, "Should show cost estimate for large requests"

        # Проверяем формат предупреждения
        cost_warning = cost_warnings[0]
        assert "$" in cost_warning
        assert "tokens" in cost_warning

    def test_warning_threshold_triggered(self):
        """Тест срабатывания порога предупреждения."""
        # Устанавливаем низкий порог предупреждения для тестирования
        cost_limits = CostControlLimits(warn_token_threshold=1000, block_token_threshold=50000)
        validator = EnhancedRequestValidator(self.limits, cost_limits)

        # Создаем файл с содержимым, превышающим порог предупреждения
        large_content = "x" * 5000  # ~1400+ токенов
        files = [
            FileInfo(
                path="test.py",
                is_binary=False,
                size=len(large_content),
                include_mode="as_file",
                content=large_content
            )
        ]

        result = validator.validate_request_enhanced(files, "Test query")

        # Проверяем наличие предупреждения о высоком количестве токенов
        token_warnings = [w for w in result.warnings if "High token count:" in w]
        assert len(token_warnings) > 0, "Should warn about high token count"

        warning = token_warnings[0]
        assert "warning threshold: 1,000" in warning

    def test_blocking_threshold_triggered(self):
        """Тест срабатывания блокирующего порога."""
        # Устанавливаем низкий блокирующий порог для тестирования
        cost_limits = CostControlLimits(warn_token_threshold=1000, block_token_threshold=2000)
        validator = EnhancedRequestValidator(self.limits, cost_limits)

        # Создаем файл с содержимым, превышающим блокирующий порог
        huge_content = "x" * 10000  # ~2800+ токенов
        files = [
            FileInfo(
                path="huge_test.py",
                is_binary=False,
                size=len(huge_content),
                include_mode="as_file",
                content=huge_content
            )
        ]

        result = validator.validate_request_enhanced(files, "Test query")

        # Проверяем, что запрос заблокирован
        assert not result.is_valid, "Request should be blocked due to high token count"

        # Проверяем наличие ошибки блокировки
        block_errors = [e for e in result.errors if "Token count too high:" in e]
        assert len(block_errors) > 0, "Should have blocking error"

        error = block_errors[0]
        assert "limit: 2,000" in error
        assert "Please reduce request size" in error

    def test_cost_estimates_disabled(self):
        """Тест отключения показа оценки стоимости."""
        cost_limits = CostControlLimits(show_cost_estimates=False)
        validator = EnhancedRequestValidator(self.limits, cost_limits)

        # Создаем большой файл
        large_content = "x" * 10000  # ~2500+ токенов
        files = [
            FileInfo(
                path="test.py",
                is_binary=False,
                size=len(large_content),
                include_mode="as_file",
                content=large_content
            )
        ]

        result = validator.validate_request_enhanced(files, "Test query")

        # Проверяем, что нет предупреждений о стоимости
        cost_warnings = [w for w in result.warnings if "Estimated cost:" in w]
        assert len(cost_warnings) == 0, "Should not show cost estimates when disabled"

    def test_small_requests_no_cost_estimate(self):
        """Тест отсутствия оценки стоимости для маленьких запросов."""
        small_content = "print('hello')"  # ~5 токенов
        files = [
            FileInfo(
                path="small.py",
                is_binary=False,
                size=len(small_content),
                include_mode="as_file",
                content=small_content
            )
        ]

        result = self.validator.validate_request_enhanced(files, "Small query")

        # Проверяем, что нет предупреждений о стоимости для маленьких запросов
        cost_warnings = [w for w in result.warnings if "Estimated cost:" in w]
        assert len(cost_warnings) == 0, "Should not show cost estimates for small requests"

    def test_config_loading_cost_control(self):
        """Тест загрузки настроек cost_control из конфига."""
        # Создаем временный конфиг
        config_content = {
            'cost_control': {
                'warn_token_threshold': 15000,
                'block_token_threshold': 40000,
                'show_cost_estimates': False
            }
        }

        with patch('yaml.safe_load', return_value=config_content):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open'):
                    from doq.validator import create_validator_from_config
                    validator = create_validator_from_config()

                    # Проверяем, что настройки загружены корректно
                    assert validator.cost_limits.warn_token_threshold == 15000
                    assert validator.cost_limits.block_token_threshold == 40000
                    assert validator.cost_limits.show_cost_estimates is False

    def test_token_estimation_accuracy(self):
        """Тест точности оценки токенов."""
        # Тестируем с известным текстом
        test_content = "def hello_world():\n    print('Hello, World!')\n    return True"
        files = [
            FileInfo(
                path="test.py",
                is_binary=False,
                size=len(test_content),
                include_mode="as_file",
                content=test_content
            )
        ]

        estimated_tokens = self.validator._estimate_tokens("Analyze this code", files)

        # Проверяем разумность оценки (примерно 1 токен на 3.5 символа)
        total_chars = len("Analyze this code") + len(test_content)
        expected_tokens = int(total_chars / 3.5)

        # Позволяем некоторую погрешность в оценке
        assert abs(
            estimated_tokens - expected_tokens
        ) < 50, f"Token estimation should be accurate: got {estimated_tokens}, expected ~{expected_tokens}"

    def test_binary_file_token_estimation(self):
        """Тест оценки токенов для бинарных файлов."""
        binary_content = b"\x00\x01\x02\x03" * 100  # Бинарные данные
        files = [
            FileInfo(
                path="test.bin",
                is_binary=True,
                size=len(binary_content),
                include_mode="as_file",
                content=binary_content.decode('latin1')  # Сохраняем как строку для тестирования
            )
        ]

        estimated_tokens = self.validator._estimate_tokens("Analyze this binary", files)

        # Бинарные файлы должны оцениваться с коэффициентом 1.2
        total_chars = len("Analyze this binary") + int(len(binary_content) * 1.2)
        expected_tokens = int(total_chars / 3.5)

        assert abs(
            estimated_tokens - expected_tokens) < 50, "Binary file token estimation should account for hex encoding"

    def test_updated_default_values(self):
        """Тест обновленных значений по умолчанию для ValidationLimits."""
        limits = ValidationLimits()

        # Проверяем новые значения по умолчанию из конфига
        assert limits.max_files == 10, f"Expected max_files=10, got {limits.max_files}"
        assert limits.max_text_lines == 10000, f"Expected max_text_lines=10000, got {limits.max_text_lines}"
        assert limits.max_binary_size_kb == 10, f"Expected max_binary_size_kb=10, got {limits.max_binary_size_kb}"
        assert limits.max_total_size_mb == 1, f"Expected max_total_size_mb=1, got {limits.max_total_size_mb}"
        assert limits.max_directory_depth == 8, f"Expected max_directory_depth=8, got {limits.max_directory_depth}"

        # Проверяем обновленные ignore_patterns
        expected_patterns = [
            "__pycache__", ".git", ".svn", ".hg", "node_modules",
            ".venv", "venv", ".env", "*.pyc", "*.pyo", "*.pyd",
            ".DS_Store", "Thumbs.db", "*.log", "*.tmp", "*.temp",
            ".pytest_cache", ".coverage", "*.egg-info", ".idea",
            ".vscode", "build", "dist", "target", ".tox", ".mypy_cache"
        ]

        for pattern in expected_patterns:
            assert pattern in limits.ignore_patterns, f"Pattern '{pattern}' should be in ignore_patterns"
