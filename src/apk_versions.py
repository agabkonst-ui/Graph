"""Compare the version components used in Alpine package constraints."""

import re
from itertools import zip_longest


VERSION_PART = re.compile(
    r"(?P<major>^[0-9]+)|\.(?P<number>[0-9]+)|"
    r"_(?P<suffix>[a-z]+)|(?P<sequence>[0-9]+)|(?P<letter>[a-z])|"
    r"~(?P<commit>[0-9a-f]+)|-r(?P<revision>[0-9]+)"
)
PART_ORDER = (
    "end", "revision", "commit", "sequence", "suffix",
    "letter", "number", "major",
)
SUFFIX_ORDER = (
    "alpha", "beta", "pre", "rc", "", "cvs", "svn", "git", "hg", "p",
)
PRE_RELEASES = {"alpha", "beta", "pre", "rc"}
END = ("end", "")


def parts(version):
    """Yield each typed version component in its original order."""
    for match in VERSION_PART.finditer(version):
        kind = match.lastgroup
        yield kind, match[kind]


def compare_values(kind, left, right):
    """Compare components of the same type and return a comparison symbol."""
    if kind == "suffix":
        left, right = SUFFIX_ORDER.index(left), SUFFIX_ORDER.index(right)
    elif kind in {"major", "sequence", "revision"}:
        left, right = int(left), int(right)
    elif kind == "number" and not any(
        value.startswith("0") for value in (left, right)
    ):
        left, right = int(left), int(right)
    if left == right:
        return "="
    return "<" if left < right else ">"


def compare_kinds(left, right, fuzzy):
    """Order unlike components, including prereleases and fuzzy prefixes."""
    left_kind, left_value = left
    right_kind, right_value = right
    if fuzzy and right == END:
        return "="
    if left_kind == "suffix" and left_value in PRE_RELEASES:
        return "<"
    if right_kind == "suffix" and right_value in PRE_RELEASES:
        return ">"
    if PART_ORDER.index(left_kind) < PART_ORDER.index(right_kind):
        return "<"
    return ">"


def compare_versions(actual, expected, fuzzy):
    """Compare valid Alpine versions, allowing a component prefix for ~."""
    pairs = zip_longest(parts(actual), parts(expected), fillvalue=END)
    for left, right in pairs:
        if left[0] != right[0]:
            return compare_kinds(left, right, fuzzy)
        comparison = compare_values(left[0], left[1], right[1])
        if comparison != "=":
            return comparison
    return "="


def satisfies(actual, operator, expected):
    """Check an unversioned, ordered, or fuzzy version requirement."""
    if not operator:
        return True
    if not actual or not expected:
        return False
    comparison = compare_versions(actual, expected, fuzzy="~" in operator)
    accepted = operator.replace("~", "=")
    return comparison in accepted
