set -euo pipefail
python3 - <<'PY'
from pathlib import Path
path = Path("include/zip.hpp")
data = path.read_text()
missing = [header for header in ("vector", "utility") if f"#include <{header}>" not in data]
if missing:
    anchor = "#include <string>"
    if data.count(anchor) != 1:
        raise SystemExit("Expected exactly one <string> include in include/zip.hpp")
    addition = "".join(f"\n#include <{header}>" for header in missing)
    path.write_text(data.replace(anchor, anchor + addition, 1))
    print("Added required standard headers: " + ", ".join(missing))
else:
    print("zip.hpp already includes vector and utility")
PY
