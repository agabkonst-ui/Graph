"""Provide the command-line entry point for the dependency analyzer."""

import argparse
import sys
from http.client import HTTPException
from pathlib import Path
from xml.etree.ElementTree import ParseError

from apk import get_dependencies
from config import load_config


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.xml"


def parse_arguments():
    """Read the optional path to the XML configuration from the command line."""
    parser = argparse.ArgumentParser(description="Анализатор пакетов Alpine.")
    parser.add_argument(
        "config", nargs="?", type=Path, default=DEFAULT_CONFIG,
        help="путь к XML-файлу, по умолчанию config.xml в корне проекта",
    )
    return parser.parse_args()


def main():
    """Read the configuration and print the selected direct dependencies."""
    arguments = parse_arguments()
    try:
        config = load_config(arguments.config)
        dependencies = get_dependencies(config)
    except (HTTPException, OSError, ParseError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    package = f"{config.package_name}={config.package_version}"
    print(f"Прямые зависимости {package}:")
    if not dependencies:
        print("Прямых зависимостей нет.")
    for dependency in dependencies:
        print(f"- {dependency}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
