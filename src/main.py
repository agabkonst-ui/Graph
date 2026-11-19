"""Provide the command-line entry point for the dependency analyzer."""

import argparse
import sys
from http.client import HTTPException
from pathlib import Path
from xml.etree.ElementTree import ParseError

from apk import get_dependencies
from apk_graph import remote_source
from config import load_config
from dependency_graph import (
    Package, breadth_first, excluded, print_graph, print_reverse,
)
from local_graph import TEST_NAME, local_source
from visualization import export_graph


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.xml"


def parse_arguments():
    """Read the optional path to the XML configuration from the command line."""
    parser = argparse.ArgumentParser(description="Анализатор пакетов Alpine.")
    parser.add_argument(
        "config", nargs="?", type=Path, default=DEFAULT_CONFIG,
        help="путь к XML-файлу, по умолчанию config.xml в корне проекта",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--direct", action="store_true",
        help="вывести прямые зависимости в режиме этапа 2",
    )
    mode.add_argument(
        "--reverse", action="store_true",
        help="вывести обратные зависимости в режиме этапа 4",
    )
    mode.add_argument(
        "--visualize", action="store_true",
        help="сохранить граф в PlantUML и SVG в режиме этапа 5",
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


def run_graph(config, reverse=False, output=None):
    """Build a graph from the configured remote or offline repository."""
    if config.test_mode and not TEST_NAME.fullmatch(config.package_name):
        raise ValueError("В тестовом графе package_name состоит из букв A–Z.")
    if excluded(config.package_name, config.filter_substring):
        if output is not None:
            export_graph({}, output)
        elif reverse:
            version = "" if config.test_mode else config.package_version
            print_reverse(Package(config.package_name, version), {})
        else:
            print_graph({}, {})
        return
    source = local_source if config.test_mode else remote_source
    root, neighbors = source(config, reverse=reverse)
    adjacency, depths = breadth_first(root, neighbors, config.max_depth)
    if output is not None:
        export_graph(adjacency, output)
    elif reverse:
        print_reverse(root, depths)
    else:
        print_graph(adjacency, depths)


def main():
    """Read the configuration and run the selected analysis mode."""
    arguments = parse_arguments()
    try:
        config = load_config(arguments.config)
        if arguments.direct:
            print_direct(config)
        else:
            output = None
            if arguments.visualize:
                output = arguments.config.resolve().parent / config.output_file
            run_graph(config, reverse=arguments.reverse, output=output)
    except (HTTPException, OSError, ParseError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
