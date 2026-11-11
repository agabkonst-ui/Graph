"""Exercise valid and invalid XML configuration files."""

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.config import load_config


PROJECT = Path(__file__).resolve().parents[1]
EXAMPLE = PROJECT / "config.xml"


class ConfigTests(unittest.TestCase):
    """Test the XML contract of the command-line analyzer."""

    def test_default_configuration(self):
        """Load the sample and convert Boolean and numeric settings."""
        config = load_config(EXAMPLE)
        self.assertEqual(config.package_name, "7zip")
        self.assertEqual(config.package_version, "24.09-r0")
        self.assertFalse(config.test_mode)
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(config.filter_substring, "")

    def test_bad_values(self):
        """Reject an invalid value for each setting with a format constraint."""
        bad_values = {
            "package_name": "../7zip",
            "package_version": "latest",
            "repository": "file:///var/tmp/APKINDEX",
            "test_mode": "maybe",
            "output_file": "../graph.svg",
            "max_depth": "-1",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            for key, value in bad_values.items():
                with self.subTest(key=key):
                    tree = ElementTree.parse(EXAMPLE)
                    tree.find(key).text = value
                    tree.write(path, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, key):
                        load_config(path)

    def test_missing_filter_element(self):
        """Require the filter element even though an empty filter is valid."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            tree = ElementTree.parse(EXAMPLE)
            root = tree.getroot()
            root.remove(root.find("filter_substring"))
            tree.write(path, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "filter_substring"):
                load_config(path)

    def test_local_path_is_relative_to_xml(self):
        """Resolve a test repository from the configuration directory."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.xml"
            index = path.with_name("APKINDEX")
            index.touch()
            tree = ElementTree.parse(EXAMPLE)
            tree.find("repository").text = index.name
            tree.find("test_mode").text = "true"
            tree.write(path, encoding="utf-8")
            self.assertEqual(load_config(path).repository, str(index.resolve()))
