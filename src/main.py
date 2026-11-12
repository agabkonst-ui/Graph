"""Provide the command-line entry point for the dependency analyzer."""

import argparse
import sys
from http.client import HTTPException
from pathlib import Path
from xml.etree.ElementTree import ParseError

from apk import get_dependencies
from apk_graph import remote_source
from config import load_config
from dependency_graph import breadth_first, excluded, print_graph
from local_graph import TEST_NAME, local_source


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.xml"


def parse_arguments():
    """Read the optional path to the XML configuration from the command line."""
    parser = argparse.ArgumentParser(description="Анализатор пакетов Alpine.")
    parser.add_argument(
        "config", nargs="?", type=Path, default=DEFAULT_CONFIG,
        help="путь к XML-файлу, по умолчанию config.xml в корне проекта",
    )
    parser.add_argument(
        "--direct", action="store_true",
        help="вывести прямые зависимости в режиме этапа 2",
    )
    return parser.parse_args()


def print_direct(config):
    """Run the stage 2 command with its original output and sources."""
    dependencies = get_dependencies(config)
    package = f"{config.package_name}={config.package_version}"
    print(f"Прямые зависимости {package}:")
    if not dependencies:
        print("Прямых зависимостей нет.")
    for dependency in dependencies:
        print(f"- {dependency}")


def run_graph(config):
    """Build a graph from the configured remote or offline repository."""
    if config.test_mode and not TEST_NAME.fullmatch(config.package_name):
        raise ValueError("В тестовом графе package_name состоит из букв A–Z.")
    if excluded(config.package_name, config.filter_substring):
        print_graph({}, {})
        return
    source = local_source if config.test_mode else remote_source
    root, neighbors = source(config)
    adjacency, depths = breadth_first(root, neighbors, config.max_depth)
    print_graph(adjacency, depths)


def main():
    """Read the configuration and run the selected analysis mode."""
    arguments = parse_arguments()
    try:
        config = load_config(arguments.config)
        analyze = print_direct if arguments.direct else run_graph
        analyze(config)
    except (HTTPException, OSError, ParseError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
