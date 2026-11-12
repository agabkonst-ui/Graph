"""Verify BFS, filtering and the offline graph command."""

import contextlib
import io
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from config import load_config
from dependency_graph import Package, breadth_first
from local_graph import parse_line
from main import main, run_graph


PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "config"


class DependencyGraphTests(unittest.TestCase):
    """Exercise cycles, shared nodes, filtering and the depth limit."""

    def output_for(self, filename):
        """Run the normal CLI entry point against an example XML."""
        argv = ["main.py", str(CONFIG / filename)]
        output = io.StringIO()
        with patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(), 0)
        return output.getvalue().splitlines()[1:]

    def test_cycle_and_shared_dependency(self):
        """Keep the cycle edge and print each package once in BFS order."""
        self.assertEqual(self.output_for("stage3-cycle.xml"), [
            "[0] A -> B, C", "[1] B -> D", "[1] C -> D, SKIP",
            "[2] D -> A", "[2] SKIP -> HIDDEN", "[3] HIDDEN -> —",
        ])

    def test_filter_uses_substring_and_cuts_branch(self):
        """Skip matching names while retaining shared dependencies."""
        config = load_config(CONFIG / "default.xml")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_graph(replace(config, filter_substring="KIP"))
        self.assertEqual(output.getvalue().splitlines()[1:], [
            "[0] A -> B, C", "[1] B -> D", "[1] C -> D", "[2] D -> A",
        ])

    def test_depth_limit(self):
        """Include direct neighbors without expanding them at depth one."""
        self.assertEqual(self.output_for("stage3-depth.xml"), [
            "[0] A -> B, C", "[1] B -> —", "[1] C -> —",
        ])

    def test_zero_depth_does_not_read_neighbors(self):
        """Return a graph with only the root at depth zero."""
        root = Package("A")
        neighbors = Mock()
        adjacency, depths = breadth_first(root, neighbors, 0)
        neighbors.assert_not_called()
        self.assertEqual(adjacency, {root: ()})
        self.assertEqual(depths, {root: 0})

    def test_root_filter(self):
        """Print an empty graph when the root name matches the filter."""
        config = load_config(CONFIG / "default.xml")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_graph(replace(config, filter_substring="A"))
        self.assertIn("Граф пуст", output.getvalue())

    def test_rejects_non_uppercase_names(self):
        """Report the line number for a malformed test graph."""
        with self.assertRaisesRegex(ValueError, "Строка 2"):
            parse_line("A: wrong", 2)
