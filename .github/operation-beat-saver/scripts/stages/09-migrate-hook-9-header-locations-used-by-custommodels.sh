set -euo pipefail
python3 - <<'PY'
from pathlib import Path

replacements = {
    'beatsaber-hook/shared/utils/hooking.hpp': 'beatsaber-hook/shared/hooking.hpp',
    'beatsaber-hook/shared/utils/logging.hpp': 'beatsaber-hook/shared/utils.hpp',
    'beatsaber-hook/shared/utils/utils.h': 'beatsaber-hook/shared/utils.hpp',
    'metacore/shared/ui.hpp': 'metacore-bs/shared/ui.hpp',
}
changed = []
for root in (Path("include"), Path("src")):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".h", ".hpp", ".cpp"}:
            continue
        source = path.read_text()
        updated = source
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != source:
            path.write_text(updated)
            changed.append(str(path))
if not changed:
    raise SystemExit("Expected legacy Hook header includes were not found; refusing a no-op migration")
print("Migrated Hook 9 header locations in:")
print("\n".join(changed))
PY
