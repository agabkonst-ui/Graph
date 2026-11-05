"""Помощники тестов для временного XML и локального репозитория."""

import xml.etree.ElementTree as element_tree


def valid_values(base):
    """Создаёт семь корректных значений и читаемый файл репозитория."""
    (base / "repository.txt").write_text("A: B\nB:\n", encoding="utf-8")
    return {
        "package_name": "A",
        "repository": "repository.txt",
        "test_mode": "true",
        "package_version": "1.0-r1",
        "output_file": "graph.svg",
        "max_depth": "3",
        "filter_substring": "",
    }


def write_config(path, values):
    """Создаёт XML с корректным экранированием специальных символов."""
    root = element_tree.Element("config")
    for name, value in values.items():
        element_tree.SubElement(root, name).text = value
    element_tree.ElementTree(root).write(path, encoding="utf-8",
                                         xml_declaration=True)
    return path
