"""Verify reverse traversal with local graphs and a controlled APK index."""

import io
import subprocess
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch

from apk_graph import remote_source
from config import load_config
from dependency_graph import Package, breadth_first
from test_apk import PROJECT, signed_archive


def reverse_cli(config_name):
    """Run the stage 4 CLI and return its printed package rows."""
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(PROJECT / "src/main.py"),
         "--reverse", str(PROJECT / "config" / config_name)],
        capture_output=True, encoding="utf-8", check=True,
    )
    return result.stdout.splitlines()[1:]


class ReverseTests(unittest.TestCase):
    """Check shortest reverse distances, filtering and APK resolution."""

    def test_cycle_and_shared_dependent(self):
        """Exclude the selected package and visit the shared package once."""
        rows = reverse_cli("stage3-cycle.xml")
        self.assertEqual(rows, ["[1] D", "[2] B", "[2] C"])

    def test_depth_limit(self):
        """At depth one report only the immediate dependent of A."""
        self.assertEqual(reverse_cli("stage3-depth.xml"), ["[1] D"])

    def test_filter_cuts_reverse_chain(self):
        """Removing SKIP blocks every reverse path from HIDDEN."""
        self.assertEqual(
            reverse_cli("stage4-transitive.xml"),
            ["[1] SKIP", "[2] C", "[3] A"],
        )
        self.assertEqual(
            reverse_cli("stage4-filter.xml"),
            ["В пределах заданной глубины обратных зависимостей нет."],
        )

    def test_remote_reverse_edges_respect_versions(self):
        """Resolve virtual providers and omit incompatible versions."""
        index = (
            "P:lib\nV:1-r0\n\nP:lib\nV:2-r0\np:so:lib=2\n\n"
            "P:client\nV:1-r0\nD:so:lib>=2\n\n"
            "P:other\nV:1-r0\nD:lib=1-r0\n\n"
            "P:app\nV:1-r0\nD:client\n"
        )
        config = replace(load_config(PROJECT / "config.xml"),
                         package_name="lib", package_version="2-r0")
        response = io.BytesIO(signed_archive("APKINDEX", index))
        with patch("apk.urlopen", return_value=response) as request:
            root, neighbors = remote_source(config, reverse=True)
            _, depths = breadth_first(root, neighbors, config.max_depth)
        request.assert_called_once()
        self.assertEqual(depths, {
            Package("lib", "2-r0"): 0,
            Package("client", "1-r0"): 1,
            Package("app", "1-r0"): 2,
        })
