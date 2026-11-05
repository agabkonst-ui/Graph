"""Согласование режима работы и накопление ошибок параметров."""

import re

from .errors import ConfigError
from .locations import validate_output, validate_repository
from .model import Config
from .scalars import PARSERS

TEST_PACKAGE_PATTERN = r"[A-Z]+"
REAL_PACKAGE_PATTERN = r"[a-z0-9][a-z0-9+_.-]*"


def check_package_mode(values):
    """Требует большие буквы для тестового графа, строчное имя для apk."""
    if "package_name" not in values or "test_mode" not in values:
        return
    pattern = REAL_PACKAGE_PATTERN
    if values["test_mode"]:
        pattern = TEST_PACKAGE_PATTERN
    if re.fullmatch(pattern, values["package_name"]) is None:
        raise ConfigError("package_name: в тестовом режиме нужны A..Z, "
                          "в обычном — строчное имя пакета")


def check_locations(values, base, errors):
    """Добавляет ошибки источника репозитория и пути изображения."""
    if "repository" in values and "test_mode" in values:
        try:
            validate_repository(values["repository"], values["test_mode"], base)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    if "output_file" in values:
        try:
            validate_output(values["output_file"], base)
        except (OSError, ValueError) as error:
            errors.append(str(error))


def validate_config(raw, base):
    """Возвращает проверенную модель либо все независимые ошибки."""
    values = {}
    errors = []
    for name, parse in PARSERS.items():
        try:
            values[name] = parse(raw[name])
        except ConfigError as error:
            errors.append(str(error))
    try:
        check_package_mode(values)
    except ConfigError as error:
        errors.append(str(error))
    check_locations(values, base, errors)
    if errors:
        raise ConfigError("\n".join(errors))
    return Config(**values)
