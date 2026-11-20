"""Export a dependency graph to PlantUML and render it locally as SVG."""

import os
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree


UNSAFE_LABEL_CHAR = re.compile(r"[^A-Za-z0-9 .,:?=~+()/-]")
RENDER_TIMEOUT = 60
SVG_TAG = "{http://www.w3.org/2000/svg}svg"


def plantuml_label(label):
    """Escape characters that could be interpreted as PlantUML syntax."""
    return UNSAFE_LABEL_CHAR.sub(
        lambda match: f"<U+{ord(match.group()):04X}>", label
    )


def plantuml_source(adjacency):
    """Represent all vertices and directed edges with stable node IDs."""
    lines = [
        "@startuml",
        "!pragma layout smetana",
        "left to right direction",
        "skinparam shadowing false",
    ]
    aliases = {package: f"p{index}" for index, package in enumerate(adjacency)}
    for package, alias in aliases.items():
        label = plantuml_label(package.label())
        lines.append(f'rectangle "{label}" as {alias}')
    for package, dependencies in adjacency.items():
        for dependency in dependencies:
            lines.append(f"{aliases[package]} --> {aliases[dependency]}")
    if not aliases:
        lines.append('rectangle "No packages match the filter"')
    return "\n".join([*lines, "@enduml", ""])


def render_svg(source):
    """Invoke the configured PlantUML jar and verify the SVG response."""
    jar = os.environ.get("PLANTUML_JAR")
    if not jar or not Path(jar).is_file():
        raise ValueError("Укажите путь к PlantUML JAR в PLANTUML_JAR.")
    java = os.environ.get("JAVA_EXE") or "java"
    command = [
        java, "-Djava.awt.headless=true", "-DPLANTUML_SECURITY_PROFILE=SANDBOX",
        "-jar", jar, "-charset", "UTF-8", "-tsvg", "-pipe",
    ]
    try:
        result = subprocess.run(
            command, input=source.encode("utf-8"), capture_output=True,
            check=True, timeout=RENDER_TIMEOUT,
        )
        if ElementTree.fromstring(result.stdout).tag != SVG_TAG:
            raise ValueError("PlantUML не вернул документ SVG.")
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Ошибка PlantUML: {message or error.returncode}")
    except subprocess.TimeoutExpired as error:
        raise ValueError("Истекло время ожидания PlantUML.") from error
    return result.stdout


def export_graph(adjacency, output):
    """Write the PlantUML and SVG files after successful rendering."""
    source = plantuml_source(adjacency)
    svg = render_svg(source)
    diagram = output.with_suffix(".puml")
    diagram.write_bytes(source.encode("utf-8"))
    output.write_bytes(svg)
    print(f"PlantUML: {diagram}")
    print(f"SVG: {output}")
