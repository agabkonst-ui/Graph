"""Проверки семи параметров и согласования режима с источником."""

import tempfile
import unittest
from pathlib import Path

from support import valid_values
from graph_tool.errors import ConfigError
from graph_tool.validation import validate_config


class ValidationTests(unittest.TestCase):
    """Проверяет допустимые значения и все группы ошибок настроек."""

    def setUp(self):
        """Создаёт отдельные тестовые данные перед каждой проверкой."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.values = valid_values(self.base)

    def check_invalid(self, name, values):
        """Требует информативную ошибку для каждого неверного значения."""
        for value in values:
            with self.subTest(name=name, value=value):
                raw = dict(self.values, **{name: value})
                with self.assertRaises(ConfigError) as caught:
                    validate_config(raw, self.base)
                self.assertIn(name, str(caught.exception))

    def test_test_mode_success(self):
        """Локальный режим принимает параметры и пустой фильтр."""
        config = validate_config(self.values, self.base)
        self.assertEqual(config.package_name, "A")
        self.assertTrue(config.test_mode)
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(config.filter_substring, "")

    def test_remote_mode_success(self):
        """Обычный режим принимает синтаксически корректный HTTP(S) URL."""
        self.values.update(test_mode="false", package_name="busybox",
                           repository="https://example.org/alpine/")
        config = validate_config(self.values, self.base)
        self.assertFalse(config.test_mode)
        self.assertEqual(config.repository, "https://example.org/alpine/")

    def test_invalid_package(self):
        """Отклоняются пустое имя, пробелы и пути."""
        self.check_invalid("package_name", ("", "a b", "../A", "@A"))

    def test_test_package_requires_capitals(self):
        """Имена тестового графа состоят из больших латинских букв."""
        self.check_invalid("package_name", ("busybox", "A1", "А"))

    def test_real_package_requires_lowercase(self):
        """Для обычного режима нужны строчные имена пакетов."""
        self.values.update(test_mode="false",
                           repository="https://example.org/alpine/")
        self.check_invalid("package_name", ("A", "BusyBox"))

    def test_invalid_repository_path(self):
        """Тестовый источник должен быть читаемым файлом."""
        self.check_invalid("repository", ("", "missing.txt", ".",
                                           "https://example.org/test"))

    def test_repository_path_with_spaces(self):
        """Пробелы разрешены в имени локального репозитория."""
        path = self.base / "test repository.txt"
        path.write_text("A:\n", encoding="utf-8")
        self.values["repository"] = path.name
        self.assertTrue(validate_config(self.values, self.base).test_mode)

    def test_absolute_repository_path(self):
        """Можно задать абсолютный путь к тестовому репозиторию."""
        self.values["repository"] = str(self.base / "repository.txt")
        self.assertTrue(validate_config(self.values, self.base).test_mode)

    def test_invalid_repository_url(self):
        """Проверяются схема, сервер, порт, пробелы и данные авторизации."""
        self.values.update(test_mode="false", package_name="busybox")
        self.check_invalid("repository", (
            "repository.txt", "ftp://example.org/a", "https://",
            "https://exa mple.org", "https://example.org:abc",
            "https://example.org:99999", "https://example.org:0",
            "https://user:pass@example.org", "https://example.org/#part",
            "https://[invalid",
        ))

    def test_invalid_mode(self):
        """Режим принимает только true или false."""
        self.check_invalid("test_mode", ("", "yes", "1", "maybe"))

    def test_mode_case_insensitive(self):
        """Регистр boolean-значения не влияет на результат."""
        self.values["test_mode"] = "TRUE"
        self.assertTrue(validate_config(self.values, self.base).test_mode)

    def test_invalid_version(self):
        """Версия не может быть пустой, путём или содержать пробелы."""
        self.check_invalid("package_version", ("", "1 2", "../1", "1/2"))

    def test_invalid_output(self):
        """Проверяются расширение SVG, имя и существование каталога."""
        self.check_invalid("output_file", (
            "", "graph.png", "missing/graph.svg", "bad?.svg",
            "CON.svg", "aux.SVG", "NUL.svg", "graph\nname.svg",
        ))

    def test_output_cannot_be_directory(self):
        """Каталог с расширением SVG не считается файлом."""
        (self.base / "directory.svg").mkdir()
        self.check_invalid("output_file", ("directory.svg",))

    def test_output_parent_cannot_be_file(self):
        """Родитель пути изображения не может быть файлом."""
        self.check_invalid("output_file", ("repository.txt/graph.svg",))

    def test_existing_output_is_not_overwritten(self):
        """Проверка имени не изменяет ранее существовавший файл."""
        output = self.base / "graph.svg"
        output.write_text("existing output", encoding="utf-8")
        validate_config(self.values, self.base)
        self.assertEqual(output.read_text(), "existing output")

    def test_valid_output_with_spaces(self):
        """Пробелы и расширение SVG в другом регистре допустимы."""
        self.values["output_file"] = "my graph.SVG"
        config = validate_config(self.values, self.base)
        self.assertEqual(config.output_file, "my graph.SVG")

    def test_invalid_depth(self):
        """Дробная, отрицательная и нечисловая глубина отклоняются."""
        self.check_invalid("max_depth", ("", "-1", "2.5", "abc", "true"))

    def test_zero_depth(self):
        """Нулевая глубина разрешена."""
        self.values["max_depth"] = "0"
        self.assertEqual(validate_config(self.values, self.base).max_depth, 0)

    def test_invalid_filter(self):
        """В подстроке недопустимы пробелы, слеши и шаблоны."""
        self.check_invalid("filter_substring", ("a b", "/", "*", "[abc]"))

    def test_valid_filter(self):
        """Фильтр хранится как обычная подстрока."""
        self.values["filter_substring"] = "lib-"
        config = validate_config(self.values, self.base)
        self.assertEqual(config.filter_substring, "lib-")

    def test_collects_errors_for_every_parameter(self):
        """Все семь независимых ошибок возвращаются за один запуск."""
        raw = {name: "" for name in self.values}
        raw["filter_substring"] = "/"
        with self.assertRaises(ConfigError) as caught:
            validate_config(raw, self.base)
        for name in self.values:
            self.assertIn(name + ":", str(caught.exception))
