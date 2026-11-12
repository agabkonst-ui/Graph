"""Build and display a directed dependency graph in BFS order."""

from collections import deque
from dataclasses import dataclass


ROOT_DEPTH = 0


def excluded(name, substring):
    """Match the configured substring against a package name."""
    return bool(substring and substring in name)


@dataclass(frozen=True)
class Package:
    """Identify a test node, versioned APK, or unresolved dependency."""

    name: str
    version: str = ""
    unresolved: str = ""

    def label(self):
        """Return the node label used in the console graph."""
        if self.unresolved:
            return f"{self.unresolved} (?)"
        if self.version:
            return f"{self.name}={self.version}"
        return self.name


def breadth_first(root, neighbors, max_depth):
    """Return adjacency and shortest depths, retaining edges into cycles."""
    depths = {root: ROOT_DEPTH}
    adjacency = {}
    queue = deque([root])
    while queue:
        package = queue.popleft()
        depth = depths[package]
        children = ()
        if depth < max_depth:
            children = tuple(dict.fromkeys(neighbors(package)))
        adjacency[package] = children
        for child in children:
            if child not in depths:
                depths[child] = depth + 1
                queue.append(child)
    return adjacency, depths


def print_graph(adjacency, depths):
    """Print one adjacency row per visited package with its BFS depth."""
    if not adjacency:
        print("Граф пуст: исходный пакет исключён фильтром.")
        return
    print("Граф зависимостей (BFS):")
    for package, children in adjacency.items():
        labels = ", ".join(child.label() for child in children) or "—"
        print(f"[{depths[package]}] {package.label()} -> {labels}")
