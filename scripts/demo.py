"""Демонстрация обоих режимов и ошибок каждого из семи параметров."""

import sys
import tempfile
import xml.etree.ElementTree as element_tree
from pathlib import Path

from graph_tool.cli import CONFIG_ERROR, DEFAULT_CONFIG, SUCCESS, main

INVALID_VALUES = {
    "package_name": "bad name",
    "repository": "missing-repository.txt",
    "test_mode": "maybe",
    "package_version": "1 2",
    "output_file": "graph.png",
    "max_depth": "-1",
    "filter_substring": "bad/filter",
}


def run_case(title, path, expected):
    """Вызывает CLI и сравнивает ожидаемый и фактический коды."""
    print(f"\n=== {title} ===", flush=True)
    actual = main(["--config", str(path)], out=sys.stdout, err=sys.stdout)
    print(f"Код завершения: {actual}; ожидается: {expected}", flush=True)
    if actual != expected:
        raise RuntimeError(f"Неожиданный результат примера: {title}")


def build_tree():
    """Создаёт дерево с абсолютным путём локального репозитория."""
    tree = element_tree.parse(DEFAULT_CONFIG)
    repository = tree.getroot().find("repository")
    repository.text = str((DEFAULT_CONFIG.parent / repository.text).resolve())
    tree.getroot().find("output_file").text = "graph.svg"
    return tree


def demonstrate_errors(base):
    """Показывает неверное значение и отсутствие каждого параметра."""
    path = base / "case.xml"
    for name, invalid in INVALID_VALUES.items():
        tree = build_tree()
        tree.getroot().find(name).text = invalid
        tree.write(path, encoding="utf-8", xml_declaration=True)
        run_case(f"Неверное значение: {name}", path, CONFIG_ERROR)
        tree = build_tree()
        tree.getroot().remove(tree.getroot().find(name))
        tree.write(path, encoding="utf-8", xml_declaration=True)
        run_case(f"Отсутствует параметр: {name}", path, CONFIG_ERROR)


def demonstrate_files(base):
    """Проверяет отсутствующий XML, повреждённый XML и неверный URL."""
    path = base / "case.xml"
    run_case("Отсутствующий XML", base / "absent.xml", CONFIG_ERROR)
    path.write_text("<config>", encoding="utf-8")
    run_case("Повреждённый XML", path, CONFIG_ERROR)
    tree = build_tree()
    tree.getroot().find("test_mode").text = "false"
    tree.getroot().find("package_name").text = "busybox"
    tree.getroot().find("repository").text = "ftp://example.org/repo"
    tree.write(path, encoding="utf-8", xml_declaration=True)
    run_case("Неверный URL в обычном режиме", path, CONFIG_ERROR)


def demonstrate():
    """Выполняет 19 воспроизводимых сценариев без изменения поставки."""
    run_case("Успех: локальный режим", DEFAULT_CONFIG, SUCCESS)
    run_case("Успех: режим URL", DEFAULT_CONFIG.with_name("remote.xml"),
             SUCCESS)
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        demonstrate_errors(base)
        demonstrate_files(base)
    print("\nВсе демонстрационные проверки завершены успешно.")


if __name__ == "__main__":
    demonstrate()
