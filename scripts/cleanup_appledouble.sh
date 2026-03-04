#!/usr/bin/env bash
set -euo pipefail

# Remove macOS AppleDouble files that can break Python tooling on some external drives.
find . \( -name '.venv' -o -name '.venv312' \) -prune -o -name '._*' -type f -print -delete
