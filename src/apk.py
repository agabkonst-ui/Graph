"""Read direct dependencies from Alpine APK v2 package metadata."""

import gzip
import tarfile
import zlib
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen


INDEX_ARCHIVE = "APKINDEX.tar.gz"
INDEX_MEMBER = "APKINDEX"
PACKAGE_MEMBER = ".PKGINFO"
INDEX_FIELDS = {"P", "V", "D"}
NETWORK_TIMEOUT = 20


def positive_dependencies(dependencies):
    """Keep dependency expressions while excluding conflict declarations."""
    return tuple(item for item in dependencies if not item.startswith("!"))


def index_records(index_text):
    """Yield the package fields from records separated by blank lines."""
    fields = {}
    for line in index_text.split("\n"):
        if not line.strip():
            if fields:
                yield fields
                fields = {}
            continue
        key, separator, value = line.partition(":")
        if separator and key in INDEX_FIELDS:
            fields[key] = value.strip()
    if fields:
        yield fields


def index_dependencies(index_text, name, version):
    """Return dependencies for the exact package version or None if absent."""
    for fields in index_records(index_text):
        if fields.get("P") == name and fields.get("V") == version:
            return positive_dependencies(fields.get("D", "").split())
    return None


def package_dependencies(package_text, name, version):
    """Read repeated depend fields and check the identity in .PKGINFO."""
    fields = {}
    dependencies = []
    for line in package_text.split("\n"):
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if key == "depend":
            dependencies.extend(value.split())
        elif key in {"pkgname", "pkgver"}:
            fields[key] = value
    if fields.get("pkgname") != name or fields.get("pkgver") != version:
        raise ValueError(f"В .PKGINFO нет пакета {name} версии {version}.")
    return positive_dependencies(dependencies)


def archive_member(response, member_name):
    """Read one text member from an APK archive with gzip streams."""
    try:
        with gzip.GzipFile(fileobj=response) as expanded:
            with tarfile.open(
                fileobj=expanded, mode="r|", ignore_zeros=True
            ) as archive:
                for member in archive:
                    name = member.name.removeprefix("./")
                    if name == member_name and member.isfile():
                        with archive.extractfile(member) as content:
                            return content.read().decode("utf-8")
    except (tarfile.TarError, gzip.BadGzipFile, EOFError, zlib.error) as error:
        raise ValueError(f"Повреждён архив с {member_name}: {error}") from error
    raise ValueError(f"В архиве отсутствует файл {member_name}.")


def remote_metadata(url, member_name):
    """Fetch an archive member, returning None only for HTTP 404."""
    try:
        with urlopen(url, timeout=NETWORK_TIMEOUT) as response:
            return archive_member(response, member_name)
    except HTTPError as error:
        if error.code != HTTPStatus.NOT_FOUND:
            raise
        error.close()
        return None


def remote_dependencies(repository, name, version):
    """Search the index, then try the exact .apk file if needed."""
    location = repository.rstrip("/")
    index_suffix = f"/{INDEX_ARCHIVE}"
    directory = location.removesuffix(index_suffix)
    index = remote_metadata(directory + index_suffix, INDEX_MEMBER)
    if index is not None:
        dependencies = index_dependencies(index, name, version)
        if dependencies is not None:
            return dependencies

    filename = quote(f"{name}-{version}.apk")
    package = remote_metadata(f"{directory}/{filename}", PACKAGE_MEMBER)
    if package is not None:
        return package_dependencies(package, name, version)
    return None


def get_dependencies(config):
    """Read the configured package's dependencies or report its absence."""
    name = config.package_name
    version = config.package_version
    if config.test_mode:
        index = Path(config.repository).read_text(encoding="utf-8")
        dependencies = index_dependencies(index, name, version)
    else:
        dependencies = remote_dependencies(config.repository, name, version)
    if dependencies is None:
        raise ValueError(f"Пакет {name} версии {version} не найден.")
    return dependencies
