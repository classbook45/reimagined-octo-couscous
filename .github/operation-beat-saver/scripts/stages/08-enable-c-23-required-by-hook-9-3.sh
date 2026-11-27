set -euo pipefail
python3 - <<'PY'
from pathlib import Path
import re
path = Path("CMakeLists.txt")
source = path.read_text()
pattern = r"(?m)^set\(CMAKE_CXX_STANDARD 20\)\r?\nset\(CMAKE_CXX_STANDARD_REQUIRED 20\)$"
updated, count = re.subn(pattern, "set(CMAKE_CXX_STANDARD 23)\nset(CMAKE_CXX_STANDARD_REQUIRED ON)", source)
if count != 1:
    raise SystemExit(f"Expected one C++20 declaration pair; found {count}")
path.write_text(updated)
print("Updated CustomModels to C++23 for Hook 9.3 std::expected APIs")
PY
grep -n "CMAKE_CXX_STANDARD" CMakeLists.txt
