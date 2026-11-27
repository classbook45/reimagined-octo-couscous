set -euo pipefail
python3 - <<'PY'
from pathlib import Path
cache = Path.home() / ".local/share/QPM-RS/cache"
print("Project headers:")
for root in (Path("include"), Path("extern"), cache):
    if root.exists():
        for name in ("il2cpp-utils-methods.hpp", "typedefs-list.hpp", "RegistrationHelper.hpp"):
            hits = list(root.rglob(name))
            for hit in hits[:10]:
                print(hit)
print("Proceeding with the resolved Hook 9 / Cordl 4503 headers as published.")
PY
