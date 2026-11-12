"""Resolve dependencies from the APKINDEX of the configured repository."""

import re
from collections import defaultdict
from dataclasses import dataclass
from itertools import chain

from apk import (
    fetch_index, fetch_package, index_records, positive_dependencies,
    repository_directory,
)
from apk_versions import satisfies
from dependency_graph import Package, excluded


REQUIREMENT = re.compile(r"([^<>=~]+)([<>=~]*)(.*)")
CHECKSUM_OPERATOR = "><"


@dataclass(frozen=True)
class Candidate:
    """Describe a package and the version exposed by a provided name."""

    package: Package
    provided_version: str
    checksum: str = ""

    def matches(self, operator, expected):
        """Match a version or APK identity checksum."""
        if operator == CHECKSUM_OPERATOR:
            return bool(self.checksum) and self.checksum == expected
        return satisfies(self.provided_version, operator, expected)


def parse_requirement(expression):
    """Split an APK requirement into its name, operator and version."""
    match = REQUIREMENT.fullmatch(expression)
    if not match:
        raise ValueError(f"Некорректная зависимость APK: {expression}.")
    return match.groups()


class ApkRepository:
    """Index direct requirements and virtual providers for a single URL."""

    def __init__(self, text):
        """Read the available package records in index order."""
        self.dependencies = {}
        self.names = defaultdict(list)
        self.provides = defaultdict(list)
        for fields in index_records(text):
            if fields.get("P") and fields.get("V"):
                self.add_record(fields)

    def add_record(self, fields):
        """Store one package and index the virtual names it provides."""
        package = Package(fields["P"], fields["V"])
        if package in self.dependencies:
            return
        self.dependencies[package] = positive_dependencies(
            fields.get("D", "").split()
        )
        checksum = fields.get("C", "")
        self.names[package.name].append(
            Candidate(package, package.version, checksum)
        )
        for provided in fields.get("p", "").split():
            name, _, version = parse_requirement(provided)
            self.provides[name].append(Candidate(package, version, checksum))

    def resolve(self, expression, substring):
        """Pick an eligible candidate or retain an unresolved reference."""
        name, operator, expected = parse_requirement(expression)
        candidates = chain(
            self.names.get(name, ()), self.provides.get(name, ())
        )
        filtered = excluded(name, substring)
        for candidate in candidates:
            if not candidate.matches(operator, expected):
                continue
            if not excluded(candidate.package.name, substring):
                return candidate.package
            filtered = True
        if filtered:
            return None
        return Package(name, unresolved=expression)

    def neighbors(self, package, substring):
        """Yield available or unresolved dependencies for one package."""
        for expression in self.dependencies.get(package, ()):
            target = self.resolve(expression, substring)
            if target is not None:
                yield target


def remote_source(config):
    """Load one repository index and, if necessary, the exact root APK."""
    directory = repository_directory(config.repository)
    index = fetch_index(directory)
    repository = ApkRepository(index or "")
    root = Package(config.package_name, config.package_version)
    if root not in repository.dependencies:
        dependencies = fetch_package(directory, root.name, root.version)
        if dependencies is None:
            raise ValueError(f"Пакет {root.label()} не найден.")
        repository.add_record({
            "P": root.name, "V": root.version, "D": " ".join(dependencies)
        })

    def neighbors(package):
        """Resolve one package's edges with the configured name filter."""
        return repository.neighbors(package, config.filter_substring)

    return root, neighbors
