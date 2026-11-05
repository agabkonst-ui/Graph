"""Проверки CLI, кодов завершения и вывода всех настроек."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from support import valid_values, write_config
from graph_tool.cli import CONFIG_ERROR, DEFAULT_CONFIG, SUCCESS, main


class CliTests(unittest.TestCase):
    """Проверяет пользовательский интерфейс приложения."""

    def setUp(self):
        """Готовит корректный XML в отдельном временном каталоге."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.path = self.base / "config.xml"
        self.values = valid_values(self.base)
        write_config(self.path, self.values)

    def test_all_seven_values_printed(self):
        """Вывод содержит ровно семь пар ключ-значение без ошибок."""
        out, err = io.StringIO(), io.StringIO()
        status = main(["--config", str(self.path)], out, err)
        self.assertEqual(status, SUCCESS)
        self.assertEqual(err.getvalue(), "")
        expected = "\n".join(f"{key}={value}"
                             for key, value in self.values.items()) + "\n"
        self.assertEqual(out.getvalue(), expected)

    def test_empty_filter_printed(self):
        """Даже пустой фильтр выводится отдельной строкой."""
        out = io.StringIO()
        main(["--config", str(self.path)], out, io.StringIO())
        self.assertIn("filter_substring=\n", out.getvalue())

    def test_config_error_returns_two(self):
        """Ошибка параметра даёт код 2 и сообщение в stderr."""
        self.values["max_depth"] = "-1"
        write_config(self.path, self.values)
        out, err = io.StringIO(), io.StringIO()
        status = main(["--config", str(self.path)], out, err)
        self.assertEqual(status, CONFIG_ERROR)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("max_depth:", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_help(self):
        """Справка описывает опцию выбора XML-файла."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            main(["--help"])
        self.assertIn("--config", out.getvalue())

    def test_unknown_cli_option(self):
        """Настройки анализа нельзя подменять произвольными опциями CLI."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(["--package", "busybox"])
        self.assertEqual(caught.exception.code, CONFIG_ERROR)

    def test_missing_config_argument(self):
        """Опция --config требует путь к файлу."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(["--config"])
        self.assertEqual(caught.exception.code, CONFIG_ERROR)

    def test_default_config_runs(self):
        """Комплектный пример запускается без обязательных аргументов."""
        self.assertTrue(DEFAULT_CONFIG.is_file())
        self.assertEqual(main([], io.StringIO(), io.StringIO()), SUCCESS)
