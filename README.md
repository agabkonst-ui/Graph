# Анализатор зависимостей Alpine Linux

Конфигурационное управление. Вариант 1, этап 2 «Сбор данных».
Программа читает XML-конфигурацию и выводит прямые зависимости точной
версии пакета Alpine Linux в формате APK v2.

## Как работает сбор данных

1. Программа скачивает `APKINDEX.tar.gz` из каталога репозитория.
2. В файле `APKINDEX` она ищет запись с нужными полями `P` (имя) и `V`
   (версия) и берёт зависимости из поля `D`.
3. Если индекс или запись отсутствует, программа пробует скачать
   `<имя>-<версия>.apk` и читает поля `depend` из `.PKGINFO`.
4. Зависимости выводятся построчно. Ограничения версий и имена `so:`,
   `cmd:` и `pc:` сохраняются. Записи с `!` обозначают конфликты и пропускаются.

Загрузка, чтение архивов и разбор метаданных выполняются стандартной
библиотекой Python. Формат полей описан в [документации Alpine][apk-metadata].

## Запуск и тесты

Нужен Python 3.10 или новее. Сборка и установка зависимостей не требуются.
Команды выполняются из корня репозитория.

| Действие | Windows PowerShell | Linux / macOS |
| --- | --- | --- |
| Запуск с `config.xml` | `.\run.bat` | `sh run.sh` |
| Запуск с другим XML | `.\run.bat my-config.xml` | `sh run.sh my-config.xml` |

Тесты запускаются без интернета.

```powershell
py -3 -B -m unittest discover -s tests -v
```

В Windows без команды `py` используйте `python -B -m unittest discover -s tests -v`.
В Linux и macOS используйте `python3 -B -m unittest discover -s tests -v`.

## Настройки `config.xml`

Корневой элемент — `<config>`. Каждый параметр указывается один раз.

| Параметр | Значение |
| --- | --- |
| `package_name` | Имя пакета APK, например `7zip`. |
| `repository` | URL каталога Alpine с архитектурой (`.../main/x86_64/`) или URL самого `APKINDEX.tar.gz`. |
| `test_mode` | `false` для URL, `true` для локального текстового `APKINDEX`. |
| `package_version` | Полная версия из репозитория, например `24.09-r0`. |
| `output_file` | Имя SVG-файла для этапа 5, например `dependencies.svg`. |
| `max_depth` | Максимальная глубина для этапа 3, целое число от 0. |
| `filter_substring` | Подстрока для этапа 3. Пустой элемент отключает фильтр. |

В тестовом режиме `repository` содержит путь к распакованному файлу
`APKINDEX`. Относительный путь отсчитывается от каталога XML.
Для сетевого запуска можно выбрать другой пакет и версию в [каталоге Alpine][packages]
и обновить `package_name`, `package_version` и `repository` в XML.
При ошибке программа печатает сообщение и завершает работу с кодом `1`.

## Исходный код

- `src/main.py` — `parse_arguments` читает аргументы, `main` запускает
  сбор зависимостей и печатает результат или сообщение об ошибке.
- `src/config.py` — `load_config` собирает настройки, `read_settings` читает XML,
  `read_depth` преобразует глубину, `read_repository` разрешает локальный путь
  или вызывает `validate_url` для проверки URL.
- `src/apk.py` — `get_dependencies` выбирает локальный или сетевой источник.
  `remote_dependencies` ищет версию, `remote_metadata` загружает архив,
  а `archive_member` читает нужный файл. `index_records` разбивает индекс
  на записи, `index_dependencies` находит запись нужной версии,
  `package_dependencies` читает `.PKGINFO`, а `positive_dependencies`
  отделяет зависимости от конфликтов.

## Пример с официальным репозиторием

Команда `.\run.bat` или `sh run.sh` использует настройки из `config.xml`
и выводит зависимости `7zip` для Alpine v3.22, `main`, `x86_64`.

```text
Прямые зависимости 7zip=24.09-r0:
- so:libc.musl-x86_64.so.1
- so:libgcc_s.so.1
- so:libstdc++.so.6
```

## Пример без интернета

В Windows выполните `.\run.bat tests/fixtures/config.xml`.
В Linux и macOS выполните `sh run.sh tests/fixtures/config.xml`.
В тестовом индексе две версии `sample-app` с разными зависимостями.

```text
Прямые зависимости sample-app=2.0-r0:
- sample-lib>=1.2-r0
- so:libsample.so.1
- cmd:sample-helper
```

[apk-metadata]: https://github.com/alpinelinux/apk-tools/blob/master/doc/apk-package.5.scd
[packages]: https://pkgs.alpinelinux.org/packages
