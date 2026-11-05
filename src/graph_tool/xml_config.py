"""Загрузка и проверка структуры XML-конфигурации."""

import xml.etree.ElementTree as element_tree
from dataclasses import fields
from pathlib import Path

from .errors import ConfigError
from .model import Config
from .validation import validate_config

ROOT_TAG = "config"
EXPECTED_FIELDS = tuple(field.name for field in fields(Config))


def read_root(path):
    """Читает XML с учётом декларации кодировки и обрабатывает ошибки."""
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ConfigError(f"config: невозможно прочитать {path}: {error}")
    try:
        return element_tree.fromstring(data)
    except (element_tree.ParseError, ValueError, LookupError) as error:
        raise ConfigError(f"config: неверный XML: {error}") from None


def check_element(child, values):
    """Проверяет имя, уникальность и простую структуру тега."""
    if child.tag not in EXPECTED_FIELDS:
        raise ConfigError(f"config: неизвестный параметр {child.tag}")
    if child.tag in values:
        raise ConfigError(f"config: повтор параметра {child.tag}")
    if child.attrib or list(child):
        raise ConfigError(f"{child.tag}: нужен текст без вложенных тегов")


def check_xml_text(root):
    """Не допускает посторонний текст между параметрами."""
    fragments = [root.text, *(child.tail for child in root)]
    if any(text and text.strip() for text in fragments):
        raise ConfigError("config: текст вне параметров недопустим")


def extract_values(root):
    """Требует семь известных простых элементов без атрибутов."""
    if root.tag != ROOT_TAG or root.attrib:
        raise ConfigError("config: нужен корень <config> без атрибутов")
    values = {}
    for child in root:
        check_element(child, values)
        values[child.tag] = (child.text or "").strip()
    missing = [name for name in EXPECTED_FIELDS if name not in values]
    if missing:
        message = "config: отсутствуют параметры: " + ", ".join(missing)
        raise ConfigError(message)
    check_xml_text(root)
    return values


def load_config(filename):
    """Загружает XML; пути отсчитываются от каталога конфигурации."""
    try:
        path = Path(filename).resolve()
        values = extract_values(read_root(path))
        return validate_config(values, path.parent)
    except (OSError, ValueError) as error:
        if isinstance(error, ConfigError):
            raise
        raise ConfigError(f"config: {error}") from None
