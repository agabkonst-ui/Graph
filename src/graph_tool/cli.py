"""CLI этапа 1: вывод XML-параметров или ошибок конфигурации."""

import argparse
import sys
from pathlib import Path

from .errors import ConfigError
from .model import format_config
from .xml_config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config/default.xml"
SUCCESS = 0
CONFIG_ERROR = 2


def create_parser():
    """Создаёт единственную опцию выбора XML, без подмены его настроек."""
    parser = argparse.ArgumentParser(
        description="Вариант 1, этап 1: XML-конфигурация анализа зависимостей"
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        metavar="FILE", help="путь к XML-конфигурации")
    return parser


def main(argv=None, out=None, err=None):
    """Выводит семь параметров либо ошибки и возвращает код завершения."""
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    args = create_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации:\n{error}", file=err)
        return CONFIG_ERROR
    print(format_config(config), file=out)
    return SUCCESS
