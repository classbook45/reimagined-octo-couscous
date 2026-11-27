set -euo pipefail
python3 ../.github/operation-beat-saver/scripts/port_custommodels_1453.py
git diff --check
git diff --stat
