"""Парсеры всех семи пользовательских параметров."""

import re

from .errors import ConfigError

PACKAGE_PATTERN = r"[A-Za-z0-9][A-Za-z0-9+_.-]*"
VERSION_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._+~:-]*"
FILTER_PATTERN = r"[A-Za-z0-9+_.-]*"
DEPTH_PATTERN = r"[0-9]+"
BOOLEAN_VALUES = {"true": True, "false": False}


def match_value(name, value, pattern, message):
    """Возвращает строку, соответствующую полному шаблону."""
    if re.fullmatch(pattern, value) is None:
        raise ConfigError(f"{name}: {message}")
    return value


def parse_package(value):
    """Проверяет базовый синтаксис имени без пробелов и путей."""
    return match_value("package_name", value, PACKAGE_PATTERN,
                       "нужно имя из латиницы, цифр и символов +_.-")


def parse_repository(value):
    """Требует непустой адрес или путь без управляющих разделителей."""
    if not value or any(symbol in value for symbol in ("\n", "\r", "\t")):
        raise ConfigError("repository: нужен непустой адрес или путь")
    return value


def parse_mode(value):
    """Принимает true или false без учёта регистра."""
    normalized = value.lower()
    if normalized not in BOOLEAN_VALUES:
        raise ConfigError("test_mode: допустимы только true и false")
    return BOOLEAN_VALUES[normalized]


def parse_version(value):
    """Проверяет непустой идентификатор версии без пробелов и слешей."""
    return match_value("package_version", value, VERSION_PATTERN,
                       "нужна непустая версия без пробелов и слешей")


def parse_output(value):
    """Требует имя будущего изображения."""
    if not value:
        raise ConfigError("output_file: имя файла не должно быть пустым")
    return value


def parse_depth(value):
    """Преобразует неотрицательную целую глубину; 0 означает корень."""
    match_value("max_depth", value, DEPTH_PATTERN,
                "нужно целое неотрицательное число, например 0 или 3")
    try:
        return int(value)
    except ValueError:
        raise ConfigError("max_depth: слишком длинная запись числа") from None


def parse_filter(value):
    """Принимает пустой фильтр или обычную подстроку имени пакета."""
    return match_value("filter_substring", value, FILTER_PATTERN,
                       "допустимы латиница, цифры и +_.-; можно пустую строку")


PARSERS = {
    "package_name": parse_package,
    "repository": parse_repository,
    "test_mode": parse_mode,
    "package_version": parse_version,
    "output_file": parse_output,
    "max_depth": parse_depth,
    "filter_substring": parse_filter,
}
