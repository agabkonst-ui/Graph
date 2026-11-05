"""Модель семи параметров и вывод ключ-значение."""

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Config:
    """Проверенные настройки будущего анализатора зависимостей."""

    package_name: str
    repository: str
    test_mode: bool
    package_version: str
    output_file: str
    max_depth: int
    filter_substring: str


def format_config(config):
    """Представляет все поля, включая пустой фильтр, отдельными строками."""
    lines = []
    for field in fields(config):
        value = getattr(config, field.name)
        if isinstance(value, bool):
            value = str(value).lower()
        lines.append(f"{field.name}={value}")
    return "\n".join(lines)
