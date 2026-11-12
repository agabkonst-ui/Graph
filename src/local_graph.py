"""Parse the uppercase adjacency-list format used for offline examples."""

import re
from pathlib import Path

from dependency_graph import Package, excluded


TEST_NAME = re.compile(r"[A-Z]+")


def parse_line(line, number):
    """Read one package declaration and validate every name on the line."""
    name, colon, targets = line.partition(":")
    name = name.strip()
    children = targets.split()
    names = [name, *children]
    if not colon or not all(TEST_NAME.fullmatch(item) for item in names):
        raise ValueError(f"Строка {number}: ожидается формат A: B C.")
    return name, children


def read_test_graph(path):
    """Read explicit rows and accept dependencies without rows as leaves."""
    graph = {}
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        name, children = parse_line(line, number)
        if name in graph:
            raise ValueError(f"Строка {number}: пакет {name} уже объявлен.")
        graph[name] = children
    leaves = {child for children in graph.values() for child in children}
    for name in leaves - graph.keys():
        graph[name] = []
    return graph


def local_source(config):
    """Return the configured root and the test graph's neighbor function."""
    graph = read_test_graph(config.repository)
    root = Package(config.package_name)
    if root.name not in graph:
        raise ValueError(f"Пакет {root.name} отсутствует в тестовом графе.")

    def neighbors(package):
        """Yield dependencies that pass the name filter."""
        for name in graph[package.name]:
            if not excluded(name, config.filter_substring):
                yield Package(name)

    return root, neighbors
