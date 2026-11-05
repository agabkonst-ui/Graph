"""Проверки XML-структуры, путей и отсутствующих файлов."""

import tempfile
import unittest
from pathlib import Path

from support import valid_values, write_config
from graph_tool.errors import ConfigError
from graph_tool.xml_config import load_config


class XmlTests(unittest.TestCase):
    """Проверяет чтение и схему семи обязательных XML-параметров."""

    def setUp(self):
        """Создаёт временный каталог и корректные исходные значения."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.path = self.base / "config.xml"
        self.values = valid_values(self.base)

    def test_valid_xml_and_relative_paths(self):
        """Путь репозитория считается относительно XML, а не текущей папки."""
        write_config(self.path, self.values)
        self.assertEqual(load_config(self.path).repository, "repository.txt")

    def test_each_missing_parameter(self):
        """Пропуск любого из семи обязательных тегов является ошибкой."""
        for name in self.values:
            with self.subTest(name=name):
                raw = dict(self.values)
                del raw[name]
                write_config(self.path, raw)
                with self.assertRaises(ConfigError) as caught:
                    load_config(self.path)
                self.assertIn(name, str(caught.exception))

    def test_invalid_structure(self):
        """Повреждённый XML, атрибуты и неизвестные теги отклоняются."""
        documents = (
            "", "<config>", "<wrong />", '<config extra="x" />',
            "<config><unknown>x</unknown></config>",
            "<config><max_depth>1</max_depth><max_depth>2</max_depth></config>",
            '<config><max_depth unit="n">1</max_depth></config>',
            "<config><max_depth><value>1</value></max_depth></config>",
        )
        for document in documents:
            with self.subTest(document=document):
                self.path.write_text(document, encoding="utf-8")
                with self.assertRaises(ConfigError):
                    load_config(self.path)

    def test_unexpected_text(self):
        """Посторонний текст между параметрами недопустим."""
        write_config(self.path, self.values)
        text = self.path.read_text(encoding="utf-8")
        self.path.write_text(text.replace("<config>", "<config>extra"),
                             encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(self.path)

    def test_missing_file(self):
        """Отсутствующий файл даёт понятную ошибку конфигурации."""
        with self.assertRaises(ConfigError) as caught:
            load_config(self.path)
        self.assertIn("config:", str(caught.exception))

    def test_directory_instead_of_config(self):
        """Каталог нельзя открыть как XML-файл."""
        with self.assertRaises(ConfigError):
            load_config(self.base)

    def test_utf8_bom(self):
        """Поддерживается XML с начальным UTF-8 BOM."""
        write_config(self.path, self.values)
        self.path.write_bytes(b"\xef\xbb\xbf" + self.path.read_bytes())
        self.assertEqual(load_config(self.path).package_name, "A")

    def test_whitespace_around_values(self):
        """Внешние пробелы в XML-значениях удаляются."""
        raw = {name: f"  {value}  " for name, value in self.values.items()}
        write_config(self.path, raw)
        self.assertEqual(load_config(self.path).max_depth, 3)

    def test_repository_and_config_remain_unchanged(self):
        """Запуск не меняет входные файлы и не создаёт изображение."""
        write_config(self.path, self.values)
        repo = self.base / "repository.txt"
        before = (self.path.read_bytes(), repo.read_bytes())
        load_config(self.path)
        self.assertEqual((self.path.read_bytes(), repo.read_bytes()), before)
        self.assertFalse((self.base / "graph.svg").exists())
