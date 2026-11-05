"""Проверка путей и URL без сетевых запросов и создания изображения."""

from pathlib import Path
from urllib.parse import urlsplit

from .errors import ConfigError

ALLOWED_SCHEMES = {"http", "https"}
IMAGE_SUFFIX = ".svg"
INVALID_NAME_CHARACTERS = frozenset('<>:"|?*')
MIN_PORT = 1
MAX_PORT = 65535
READ_PROBE_SIZE = 1
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"}
WINDOWS_RESERVED.update(f"COM{number}" for number in range(1, 10))
WINDOWS_RESERVED.update(f"LPT{number}" for number in range(1, 10))


def local_path(value, base):
    """Отсчитывает относительный путь от каталога XML."""
    try:
        path = Path(value)
        return path if path.is_absolute() else base / path
    except (OSError, ValueError) as error:
        raise ConfigError(f"недопустимый путь: {error}") from None


def check_url_parts(parts):
    """Проверяет схему, сервер, порт и отсутствие данных авторизации."""
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise ValueError("нужен полный URL с http:// или https://")
    if parts.username or parts.password or parts.fragment:
        raise ValueError("логин, пароль и фрагмент в URL не поддерживаются")
    port = parts.port
    if port is not None and not MIN_PORT <= port <= MAX_PORT:
        raise ValueError("порт должен быть в диапазоне 1..65535")


def validate_url(value):
    """Проверяет синтаксис HTTP(S) URL без обращения к серверу."""
    try:
        check_url_parts(urlsplit(value))
        if any(character.isspace() for character in value):
            raise ValueError("URL не должен содержать пробелы")
    except ValueError as error:
        raise ConfigError(f"repository: неверный URL: {error}") from None


def validate_repository(value, test_mode, base):
    """Требует читаемый файл в тестовом режиме или HTTP(S) URL в обычном."""
    if not test_mode:
        validate_url(value)
        return
    if "://" in value:
        raise ConfigError("repository: при test_mode=true нужен путь к файлу")
    path = local_path(value, base)
    try:
        with path.open("rb") as stream:
            stream.read(READ_PROBE_SIZE)
    except (OSError, ValueError) as error:
        raise ConfigError(f"repository: файл недоступен: {error}") from None


def check_filename(name):
    """Проверяет символы и зарезервированные имена Windows."""
    if any(character in INVALID_NAME_CHARACTERS for character in name):
        raise ConfigError("output_file: имя содержит недопустимые символы")
    if any(ord(character) < ord(" ") for character in name):
        raise ConfigError("output_file: управляющие символы недопустимы")
    if name.endswith((" ", ".")):
        raise ConfigError("output_file: имя не должно оканчиваться точкой")
    stem = name.split(".")[0].upper()
    if stem in WINDOWS_RESERVED:
        raise ConfigError("output_file: зарезервированное имя Windows")


def validate_output(value, base):
    """Проверяет SVG-имя и каталог, ничего не записывая."""
    path = local_path(value, base)
    if path.suffix.lower() != IMAGE_SUFFIX:
        raise ConfigError("output_file: нужно расширение .svg")
    for part in path.parts:
        if part not in (path.anchor, ".", ".."):
            check_filename(part)
    if not path.parent.is_dir():
        raise ConfigError("output_file: родительский каталог не существует")
    if path.is_dir():
        raise ConfigError("output_file: указан каталог вместо файла")
