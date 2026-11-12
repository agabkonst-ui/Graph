"""Verify the network graph against controlled APK index responses."""

import io
import unittest
from dataclasses import replace
from unittest.mock import patch

from apk_graph import ApkRepository, remote_source
from apk_versions import satisfies
from config import load_config
from dependency_graph import Package, breadth_first
from test_apk import INDEX_URL, PROJECT, signed_archive


INDEX = (
    "P:7zip\nV:25.0-r0\nD:wrong\n\n"
    "P:7zip\nV:24.09-r0\nD:lib>=1.2-r0 so:example external !conflict\n\n"
    "P:lib\nV:1.1-r0\nD:wrong\n\n"
    "P:lib\nV:1.2-r0\nD:leaf=1-r0\n\n"
    "P:provider\nV:3-r0\np:so:example\nD:leaf=1-r0\n\n"
    "P:leaf\nV:1-r0\nD:7zip=24.09-r0\n"
)


class ApkGraphTests(unittest.TestCase):
    """Cover exact roots, transitive edges and provider resolution."""

    def test_network_graph_reads_index_once(self):
        """Use one signed index for the complete transitive traversal."""
        config = load_config(PROJECT / "config.xml")
        config = replace(config, repository=INDEX_URL)
        response = io.BytesIO(signed_archive("APKINDEX", INDEX))
        with patch("apk.urlopen", return_value=response) as request:
            root, neighbors = remote_source(config)
            graph, depths = breadth_first(root, neighbors, config.max_depth)
        self.assertEqual(request.call_args.args, (INDEX_URL,))
        request.assert_called_once()
        library = Package("lib", "1.2-r0")
        provider = Package("provider", "3-r0")
        leaf = Package("leaf", "1-r0")
        unresolved = Package("external", unresolved="external")
        self.assertEqual(root, Package("7zip", "24.09-r0"))
        self.assertEqual(graph[root], (library, provider, unresolved))
        self.assertEqual(graph[library], (leaf,))
        self.assertEqual(graph[provider], (leaf,))
        self.assertEqual(graph[leaf], (root,))
        self.assertEqual(depths[leaf], 2)

    def test_filter_applies_to_provider_name(self):
        """Skip a filtered provider even when its alias has another name."""
        index = INDEX + "\nP:other\nV:1-r0\np:so:example\n"
        repository = ApkRepository(index)
        chosen = repository.resolve("so:example", "vid")
        self.assertEqual(chosen, Package("other", "1-r0"))
        self.assertIsNone(ApkRepository(INDEX).resolve("so:example", "vid"))

    def test_root_archive_uses_the_index_for_transitive_edges(self):
        """Use exact APK metadata for a root missing from the index."""
        config = load_config(PROJECT / "config.xml")
        index = "P:lib\nV:1-r0\nD:leaf\n\nP:leaf\nV:1-r0\n"
        metadata = "pkgname = 7zip\npkgver = 24.09-r0\ndepend = lib\n"
        responses = [
            io.BytesIO(signed_archive("APKINDEX", index)),
            io.BytesIO(signed_archive(".PKGINFO", metadata)),
        ]
        with patch("apk.urlopen", side_effect=responses) as request:
            root, neighbors = remote_source(config)
            graph, _ = breadth_first(root, neighbors, config.max_depth)
        library = Package("lib", "1-r0")
        self.assertEqual(graph[root], (library,))
        self.assertEqual(graph[library], (Package("leaf", "1-r0"),))
        urls = [call.args[0] for call in request.call_args_list]
        self.assertTrue(urls[-1].endswith("/7zip-24.09-r0.apk"))

    def test_version_constraints(self):
        """Compare numeric components, prereleases and fuzzy prefixes."""
        cases = [
            ("1.10-r0", ">", "1.2-r0", True),
            ("1.2_rc1", "<", "1.2", True),
            ("1.2-r3", ">", "1.2-r2", True),
            ("1.2.1-r0", "~", "1.2", True),
            ("1.20-r0", "~", "1.2", False),
            ("1.02", "<", "1.1", True),
        ]
        for actual, operator, version, expected in cases:
            with self.subTest(actual=actual, version=version):
                self.assertEqual(satisfies(actual, operator, version), expected)
