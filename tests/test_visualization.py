"""Check the PlantUML graph and its SVG export contract."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dependency_graph import Package
from visualization import export_graph, plantuml_source


class VisualizationTests(unittest.TestCase):
    """Cover distinct nodes, cycle edges and both output files."""

    def test_plantuml_preserves_cycle_and_leaf(self):
        """Use separate node IDs even when labels share the package name."""
        first = Package("sample", "1-r0")
        second = Package("sample", "2-r0")
        leaf = Package("leaf")
        source = plantuml_source({
            first: (second, leaf), second: (first,), leaf: (),
        })
        for line in (
            'rectangle "sample=1-r0" as p0',
            'rectangle "sample=2-r0" as p1',
            'rectangle "leaf" as p2',
            "p0 --> p1", "p0 --> p2", "p1 --> p0",
        ):
            self.assertIn(line, source.splitlines())
        self.assertTrue(source.endswith("@enduml\n"))

    def test_export_uses_requested_filename(self):
        """Store the SVG and the matching UTF-8 PlantUML source together."""
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        root = Package("root")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "my graph.SVG"
            with patch("visualization.render_svg", return_value=svg) as render:
                with patch("builtins.print"):
                    export_graph({root: ()}, output)
            source = output.with_suffix(".puml").read_text(encoding="utf-8")
            render.assert_called_once_with(source)
            self.assertEqual(output.read_bytes(), svg)

    def test_renderer_failure_preserves_previous_files(self):
        """Leave an existing export intact when PlantUML cannot render."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "graph.svg"
            output.write_bytes(b"previous svg")
            diagram = output.with_suffix(".puml")
            diagram.write_text("previous diagram", encoding="utf-8")
            with patch("visualization.render_svg", side_effect=ValueError):
                with self.assertRaises(ValueError):
                    export_graph({}, output)
            self.assertEqual(output.read_bytes(), b"previous svg")
            self.assertEqual(diagram.read_text(encoding="utf-8"),
                             "previous diagram")
