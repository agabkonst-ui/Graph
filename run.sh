#!/bin/sh
exec python3 -B -X utf8 "$(dirname "$0")/src/main.py" "$@"
