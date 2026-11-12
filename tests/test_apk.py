"""Test APK metadata parsing and dependency collection."""

import gzip
import io
import subprocess
import sys
import tarfile
import unittest
from dataclasses import replace
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from src.apk import get_dependencies, remote_dependencies
from src.config import load_config


PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / "tests" / "fixtures"
REPOSITORY = "https://example.invalid/alpine/main/x86_64"
INDEX_URL = f"{REPOSITORY}/APKINDEX.tar.gz"
PACKAGE_URL = f"{REPOSITORY}/sample-app-2.0-r0.apk"
EXPECTED = ("sample-lib>=1.2-r0", "so:libsample.so.1", "cmd:sample-helper")


def archive_segment(name, text):
    """Build a gzipped TAR segment in memory."""
    archive_bytes = io.BytesIO()
    data = text.encode("utf-8")
    member = tarfile.TarInfo(name)
    member.size = len(data)
    with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
        archive.addfile(member, io.BytesIO(data))
    return gzip.compress(archive_bytes.getvalue())


def signed_archive(name, text):
    """Simulate an APK v2 archive with a separate gzip signature member."""
    return archive_segment(".SIGN.RSA.test", "test") + archive_segment(
        name, text
    )


def missing_response(url):
    """Build the HTTP error raised for a missing remote file."""
    return HTTPError(url, HTTPStatus.NOT_FOUND, "Not Found", {}, io.BytesIO())


class ApkTests(unittest.TestCase):
    """Cover exact versions, archive sources, and command-line output."""

    def test_selects_exact_version(self):
        """Keep version constraints and virtual dependencies verbatim."""
        config = load_config(FIXTURES / "config.xml")
        self.assertEqual(get_dependencies(config), EXPECTED)
        older = replace(config, package_version="1.0-r0")
        self.assertEqual(get_dependencies(older), ("old-lib",))

    def test_missing_version(self):
        """Report an error if the requested version is absent."""
        config = load_config(FIXTURES / "config.xml")
        missing = replace(config, package_version="3.0-r0")
        with self.assertRaisesRegex(ValueError, "3.0-r0"):
            get_dependencies(missing)

    def test_package_with_no_dependencies(self):
        """Return an empty tuple for a present package with no D field."""
        config = load_config(FIXTURES / "config.xml")
        leaf = replace(config, package_name="transitive-lib")
        leaf = replace(leaf, package_version="1.0-r0")
        self.assertEqual(get_dependencies(leaf), ())

    def test_remote_signed_index(self):
        """Read APKINDEX after a gzip signature and use the exact URL."""
        text = (FIXTURES / "APKINDEX").read_text(encoding="utf-8")
        response = io.BytesIO(signed_archive("APKINDEX", text))
        with patch("src.apk.urlopen", return_value=response) as request:
            result = remote_dependencies(INDEX_URL, "sample-app", "2.0-r0")
        self.assertEqual(result, EXPECTED)
        self.assertEqual(request.call_args.args, (INDEX_URL,))

    def test_exact_apk_when_version_is_absent_from_index(self):
        """Download the named package and read its repeated depend fields."""
        index = "P:sample-app\nV:1.0-r0\nD:old-lib\n"
        package = (
            "pkgname = sample-app\n"
            "pkgver = 2.0-r0\n"
            "depend = sample-lib>=1.2-r0\n"
            "depend = so:libsample.so.1\n"
            "depend = cmd:sample-helper\n"
        )
        responses = [
            io.BytesIO(signed_archive("APKINDEX", index)),
            io.BytesIO(signed_archive("./.PKGINFO", package)),
        ]
        with patch("src.apk.urlopen", side_effect=responses) as request:
            result = remote_dependencies(REPOSITORY, "sample-app", "2.0-r0")
        self.assertEqual(result, EXPECTED)
        urls = [call.args[0] for call in request.call_args_list]
        self.assertEqual(urls, [INDEX_URL, PACKAGE_URL])

    def test_both_remote_files_are_missing(self):
        """Return no match when both the index and exact .apk return 404."""
        responses = [missing_response(INDEX_URL), missing_response(PACKAGE_URL)]
        with patch("src.apk.urlopen", side_effect=responses):
            result = remote_dependencies(REPOSITORY, "sample-app", "2.0-r0")
        self.assertIsNone(result)

    def test_apk_with_mismatched_version(self):
        """Reject a package with metadata for a different version."""
        text = "pkgname = sample-app\npkgver = 1.0-r0\n"
        responses = [
            missing_response(INDEX_URL),
            io.BytesIO(signed_archive(".PKGINFO", text)),
        ]
        with patch("src.apk.urlopen", side_effect=responses):
            with self.assertRaisesRegex(ValueError, "2.0-r0"):
                remote_dependencies(REPOSITORY, "sample-app", "2.0-r0")

    def test_invalid_archive(self):
        """Report a corrupt gzip archive as a readable application error."""
        with patch("src.apk.urlopen", return_value=io.BytesIO(b"not gzip")):
            with self.assertRaisesRegex(ValueError, "APKINDEX"):
                remote_dependencies(REPOSITORY, "sample-app", "2.0-r0")

    def test_cli_prints_only_direct_dependencies(self):
        """Run the CLI and compare the output against the direct edges."""
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "src/main.py", "--direct",
             str(FIXTURES / "config.xml")],
            cwd=PROJECT, capture_output=True, encoding="utf-8", check=True,
        )
        lines = result.stdout.splitlines()
        self.assertIn("sample-app=2.0-r0", lines[0])
        self.assertEqual(lines[1:], [f"- {item}" for item in EXPECTED])

    def test_cli_reports_invalid_config(self):
        """Print a configuration error and exit with a nonzero code."""
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "src/main.py",
             "missing-config.xml"],
            cwd=PROJECT, capture_output=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing-config.xml", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
