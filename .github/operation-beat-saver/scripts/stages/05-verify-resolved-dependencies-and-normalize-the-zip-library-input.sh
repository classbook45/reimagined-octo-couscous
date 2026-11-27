set -euo pipefail
python3 - <<'PY'
import json, re
from pathlib import Path

shared = json.loads(Path("qpm.shared.json").read_text())
resolved = {
    item.get("dependency", {}).get("id"): item.get("version", "")
    for item in shared.get("restoredDependencies", [])
}
minimums = {
    "beatsaber-hook": "9.3.0",
    "bs-cordl": "4503.0.0",
    "metacore": "2.0.6",
    "metacore-bs": "1.0.1",
    "custom-types": "0.21.2",
    "lapiz": "0.3.7",
    "rapidjson-macros": "3.0.0",
    "config-utils": "3.0.0",
    "bsml": "0.6.7",
    "paper2_scotland2": "4.8.0",
}

def version_tuple(value):
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value or "")
    return tuple(map(int, match.groups())) if match else None

failures = []
for dep_id, minimum in minimums.items():
    actual = resolved.get(dep_id, "")
    actual_tuple = version_tuple(actual)
    minimum_tuple = version_tuple(minimum)
    print(f"{dep_id}: {actual or 'MISSING'} (minimum {minimum})")
    if actual_tuple is None or actual_tuple < minimum_tuple:
        failures.append(f"{dep_id}: expected >= {minimum}, resolved {actual or 'missing'}")
if failures:
    raise SystemExit("Dependency graph is not aligned:\n" + "\n".join(failures))
PY

# CustomModels' CMakeLists.txt still consumes this legacy filename
# during its post-build step. The pinned QPM zip package only
# publishes the regular libzip.so, not a separate debugSoLink.
if [[ ! -s extern/libs/libzip.so ]]; then
  if [[ -s extern/libs/libzip.so.so ]]; then
    cp extern/libs/libzip.so.so extern/libs/libzip.so
  else
    echo "QPM did not restore extern/libs/libzip.so"
    find extern/libs -maxdepth 1 -type f -printf '%f\n' | sort || true
    exit 1
  fi
fi
cp -f extern/libs/libzip.so extern/libs/libzip.debug.so
test -s extern/libs/libzip.debug.so
