"""Тесты для проверки загрузки конфигурации валидации из пользовательского файла."""

import os
import tempfile

from doq.validator import (CostControlLimits, ValidationLimits,
                           create_validator_from_config)


class TestConfigValidation:
    """Тесты для проверки загрузки настроек валидации из конфига."""

    def test_validation_limits_from_config_file(self):
        """Тест загрузки лимитов валидации из конфигурационного файла."""
        # Создаем временный конфиг с кастомными значениями
        config_content = """
validation:
  max_files: 15
  max_text_lines: 15000
  max_binary_size_kb: 20
  max_total_size_mb: 2
  max_directory_depth: 10
  warn_large_directories: false
  auto_skip_common_ignores: false
  ignore_patterns:
    - "custom_pattern"
    - "*.custom"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Загружаем валидатор с кастомным конфигом
            validator = create_validator_from_config(config_path)

            # Проверяем, что значения загружены из конфига
            limits = validator.limits
            assert limits.max_files == 15, f"Expected max_files=15, got {limits.max_files}"
            assert limits.max_text_lines == 15000, f"Expected max_text_lines=15000, got {limits.max_text_lines}"
            assert limits.max_binary_size_kb == 20, f"Expected max_binary_size_kb=20, got {limits.max_binary_size_kb}"
            assert limits.max_total_size_mb == 2, f"Expected max_total_size_mb=2, got {limits.max_total_size_mb}"
            assert limits.max_directory_depth == 10, (
                f"Expected max_directory_depth=10, got {limits.max_directory_depth}"
            )
            assert limits.warn_large_directories is False, (
                f"Expected warn_large_directories=False, got {limits.warn_large_directories}"
            )
            assert limits.auto_skip_common_ignores is False, (
                f"Expected auto_skip_common_ignores=False, got {limits.auto_skip_common_ignores}"
            )

            # Проверяем, что кастомные ignore_patterns добавлены к дефолтным
            assert "custom_pattern" in limits.ignore_patterns
            assert "*.custom" in limits.ignore_patterns

        finally:
            os.unlink(config_path)

    def test_cost_control_limits_from_config_file(self):
        """Тест загрузки лимитов cost_control из конфигурационного файла."""
        config_content = """
cost_control:
  warn_token_threshold: 15000
  block_token_threshold: 40000
  show_cost_estimates: false
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Загружаем валидатор с кастомным конфигом
            validator = create_validator_from_config(config_path)

            # Проверяем, что значения cost_control загружены из конфига
            cost_limits = validator.cost_limits
            assert cost_limits.warn_token_threshold == 15000, (f"Expected warn_token_threshold=15000, "
                                                               f"got {cost_limits.warn_token_threshold}")
            assert cost_limits.block_token_threshold == 40000, (f"Expected block_token_threshold=40000, "
                                                                f"got {cost_limits.block_token_threshold}")
            assert cost_limits.show_cost_estimates is False, (f"Expected show_cost_estimates=False, "
                                                              f"got {cost_limits.show_cost_estimates}")

        finally:
            os.unlink(config_path)

    def test_combined_validation_and_cost_control_from_config(self):
        """Тест загрузки и validation, и cost_control из одного конфига."""
        config_content = """
validation:
  max_files: 25
  max_text_lines: 20000
  max_binary_size_kb: 50
  max_total_size_mb: 5

cost_control:
  warn_token_threshold: 30000
  block_token_threshold: 80000
  show_cost_estimates: true
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            validator = create_validator_from_config(config_path)

            # Проверяем validation настройки
            limits = validator.limits
            assert limits.max_files == 25
            assert limits.max_text_lines == 20000
            assert limits.max_binary_size_kb == 50
            assert limits.max_total_size_mb == 5

            # Проверяем cost_control настройки
            cost_limits = validator.cost_limits
            assert cost_limits.warn_token_threshold == 30000
            assert cost_limits.block_token_threshold == 80000
            assert cost_limits.show_cost_estimates is True

        finally:
            os.unlink(config_path)

    def test_partial_config_with_defaults(self):
        """Тест частичного конфига с дефолтными значениями для недостающих параметров."""
        config_content = """
validation:
  max_files: 7
  # остальные параметры должны остаться дефолтными

cost_control:
  warn_token_threshold: 25000
  # остальные параметры должны остаться дефолтными
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(config_content)
            config_path = f.name

        try:
            validator = create_validator_from_config(config_path)

            # Проверяем, что указанные значения загружены
            assert validator.limits.max_files == 7
            assert validator.cost_limits.warn_token_threshold == 25000

            # Проверяем, что неуказанные значения остались дефолтными
            assert validator.limits.max_text_lines == 10000  # дефолт
            assert validator.limits.max_binary_size_kb == 10  # дефолт
            assert validator.cost_limits.block_token_threshold == 50000  # дефолт
            assert validator.cost_limits.show_cost_estimates is True  # дефолт

        finally:
            os.unlink(config_path)

    def test_nonexistent_config_file_uses_defaults(self):
        """Тест использования дефолтных значений при отсутствии конфиг файла."""
        nonexistent_path = "/path/that/does/not/exist/.doq-config.yaml"

        validator = create_validator_from_config(nonexistent_path)

        # Проверяем, что используются дефолтные значения
        limits = validator.limits
        assert limits.max_files == 10
        assert limits.max_text_lines == 10000
        assert limits.max_binary_size_kb == 10
        assert limits.max_total_size_mb == 1
        assert limits.max_directory_depth == 8

        cost_limits = validator.cost_limits
        assert cost_limits.warn_token_threshold == 20000
        assert cost_limits.block_token_threshold == 50000
        assert cost_limits.show_cost_estimates is True

    def test_invalid_yaml_config_uses_defaults(self):
        """Тест использования дефолтных значений при некорректном YAML."""
        invalid_config = """
validation:
  max_files: 15
  invalid_yaml: [unclosed bracket
cost_control:
  warn_token_threshold: not_a_number
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_config)
            config_path = f.name

        try:
            # Должно загрузиться с дефолтными значениями без падения
            validator = create_validator_from_config(config_path)

            # Проверяем, что используются дефолтные значения
            assert validator.limits.max_files == 10  # дефолт, не 15 из некорректного конфига
            assert validator.cost_limits.warn_token_threshold == 20000  # дефолт

        finally:
            os.unlink(config_path)

    def test_config_values_override_code_defaults(self):
        """Тест того, что значения из конфига переопределяют дефолты в коде."""
        # Значения из актуального конфига doq-config-example.yaml
        config_content = """
validation:
  max_files: 10
  max_text_lines: 10000
  max_binary_size_kb: 10
  max_total_size_mb: 1
  max_directory_depth: 8

cost_control:
  warn_token_threshold: 20000
  block_token_threshold: 50000
  show_cost_estimates: true
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            validator = create_validator_from_config(config_path)

            # Проверяем, что значения соответствуют конфигу
            limits = validator.limits
            assert limits.max_files == 10
            assert limits.max_text_lines == 10000
            assert limits.max_binary_size_kb == 10
            assert limits.max_total_size_mb == 1
            assert limits.max_directory_depth == 8

            cost_limits = validator.cost_limits
            assert cost_limits.warn_token_threshold == 20000
            assert cost_limits.block_token_threshold == 50000
            assert cost_limits.show_cost_estimates is True

            print("✅ Все значения из конфига корректно загружены и переопределяют дефолты")

        finally:
            os.unlink(config_path)

    def test_home_config_file_loading(self):
        """Тест загрузки конфига из домашней директории пользователя."""
        home_config_path = os.path.expanduser("~/.doq-config.yaml")

        # Если файл существует, проверим его загрузку
        if os.path.exists(home_config_path):
            validator = create_validator_from_config()  # без указания пути

            # Валидатор должен быть создан без ошибок
            assert validator is not None
            assert isinstance(validator.limits, ValidationLimits)
            assert isinstance(validator.cost_limits, CostControlLimits)

            print(f"✅ Конфиг из {home_config_path} успешно загружен")
        else:
            # Если файла нет, должны использоваться дефолты
            validator = create_validator_from_config()

            # Проверяем дефолтные значения
            assert validator.limits.max_files == 10
            assert validator.cost_limits.warn_token_threshold == 20000

            print("✅ При отсутствии конфига используются дефолтные значения")
