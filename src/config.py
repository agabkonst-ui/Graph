"""Load and validate user settings from an XML file."""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree


PACKAGE_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+\-]*")
PACKAGE_VERSION_PATTERN = re.compile(
    r"[0-9]+(?:\.[0-9]+)*[a-z]?"
    r"(?:_(?:alpha|beta|pre|rc|cvs|svn|git|hg|p)[0-9]*)*"
    r"(?:~[0-9a-f]+)?(?:-r[0-9]+)?"
)
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MIN_DEPTH = 0
MIN_PORT = 1
BOOLEAN_VALUES = {"true": True, "false": False}


@dataclass(frozen=True)
class Config:
    """Store the seven validated settings for the dependency analyzer."""

    package_name: str
    repository: str
    test_mode: bool
    package_version: str
    output_file: str
    max_depth: int
    filter_substring: str


def read_settings(path):
    """Read each expected XML element exactly once."""
    root = ElementTree.parse(path).getroot()
    if root.tag != "config" or root.attrib:
        raise ValueError("Ожидается корневой элемент <config> без атрибутов.")
    expected = set(Config.__annotations__)
    settings = {}
    for element in root:
        key = element.tag
        if key not in expected or key in settings:
            raise ValueError(f"Неизвестный или повторяющийся параметр: {key}.")
        if list(element) or element.attrib:
            raise ValueError(f"Параметр {key} должен содержать только текст.")
        settings[key] = (element.text or "").strip()
    missing = expected - settings.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Отсутствуют параметры: {names}.")
    return settings


def validate_url(value):
    """Check the URL scheme, host, port, and allowed URL components."""
    if any(character.isspace() for character in value):
        raise ValueError("URL в repository не должен содержать пробелы.")
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError as error:
        raise ValueError("Некорректный URL в repository.") from error
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ValueError("Укажите в repository URL с http:// или https://.")
    if any((url.username is not None, url.query, url.fragment)):
        raise ValueError("repository требует URL без логина, запроса и якоря.")
    if port is not None and port < MIN_PORT:
        raise ValueError("Порт repository должен быть больше нуля.")


def read_repository(value, test_mode, config_path):
    """Resolve a local test file or validate an HTTP(S) repository URL."""
    if test_mode:
        path = config_path.parent / value
        if not path.is_file():
            raise ValueError(f"Тестовый файл repository не найден: {path}.")
        return str(path.resolve())
    validate_url(value)
    return value


def read_depth(value):
    """Convert max_depth to a non-negative integer."""
    try:
        depth = int(value)
    except ValueError as error:
        raise ValueError("max_depth должен быть целым числом.") from error
    if depth < MIN_DEPTH:
        raise ValueError("max_depth должен быть неотрицательным числом.")
    return depth


def load_config(path):
    """Validate an XML configuration and return its typed settings."""
    settings = read_settings(path)
    if not PACKAGE_NAME_PATTERN.fullmatch(settings["package_name"]):
        raise ValueError("package_name должен содержать допустимое имя APK.")
    if not PACKAGE_VERSION_PATTERN.fullmatch(settings["package_version"]):
        raise ValueError("package_version должен содержать версию, как 1.2-r0.")
    mode = settings["test_mode"].lower()
    if mode not in BOOLEAN_VALUES:
        raise ValueError("test_mode должен иметь значение true или false.")
    settings["test_mode"] = BOOLEAN_VALUES[mode]
    name = settings["output_file"]
    if not name.lower().endswith(".svg") or INVALID_FILENAME_CHARS.search(name):
        raise ValueError("Укажите в output_file имя файла с расширением .svg.")
    if name.lower() == ".svg":
        raise ValueError("Укажите в output_file имя перед расширением .svg.")
    settings["max_depth"] = read_depth(settings["max_depth"])
    settings["repository"] = read_repository(
        settings["repository"], settings["test_mode"], path
    )
    return Config(**settings)
