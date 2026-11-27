set -euo pipefail
python3 - <<'PY'
from pathlib import Path

# QPM resolves reflect-cpp transitively through ConfigUtils 3, but its
# package metadata does not mark the shared library for CMake linking.
# Ensure the resolved Android binary is available to this target.
library = Path("extern/libs/libreflectcpp.so")
if not library.is_file() or library.stat().st_size == 0:
    cache = Path.home() / ".local/share/QPM-RS/cache/reflectcpp/0.25.0"
    matches = list(cache.rglob("libreflectcpp.so"))
    if len(matches) != 1 or matches[0].stat().st_size == 0:
        raise SystemExit(f"Expected one cached reflectcpp 0.25.0 shared library, found {matches}")
    library.parent.mkdir(parents=True, exist_ok=True)
    library.write_bytes(matches[0].read_bytes())

# Hook 9.4.3 declares Flamingo 1.2.1 as a transitive dependency.
# QPM restores Hook's manifest but does not reliably materialize transitive
# shared libraries into the top-level cache, so use its pinned release asset
# as a deterministic fallback instead of assuming a cache directory exists.
flamingo_library = Path("extern/libs/libflamingo.so")
if not flamingo_library.is_file() or flamingo_library.stat().st_size == 0:
    cache_root = Path.home() / ".local/share/QPM-RS/cache"
    matches = list(cache_root.rglob("libflamingo.so"))
    matches = [p for p in matches if p.is_file() and p.stat().st_size > 0]
    if len(matches) == 1:
        flamingo_library.parent.mkdir(parents=True, exist_ok=True)
        flamingo_library.write_bytes(matches[0].read_bytes())
    elif len(matches) > 1:
        raise SystemExit(f"Ambiguous cached Flamingo libraries: {matches}")
    else:
        import subprocess
        flamingo_library.parent.mkdir(parents=True, exist_ok=True)
        url = "https://github.com/QuestPackageManager/Flamingo/releases/download/v1.2.1/libflamingo.so"
        subprocess.run(["curl", "--fail", "--location", "--retry", "3", "--output", str(flamingo_library), url], check=True)
        if not flamingo_library.is_file() or flamingo_library.stat().st_size == 0:
            raise SystemExit("Pinned Flamingo 1.2.1 download produced no shared library")

cmake = Path("CMakeLists.txt")
source = cmake.read_text()
anchor = "include(extern.cmake)"
link = 'target_link_libraries(\u0024{COMPILE_ID} PRIVATE "\u0024{CMAKE_CURRENT_SOURCE_DIR}/extern/libs/libreflectcpp.so")'
flamingo = 'target_link_libraries(\u0024{COMPILE_ID} PRIVATE "\u0024{CMAKE_CURRENT_SOURCE_DIR}/extern/libs/libflamingo.so")'
if source.count(anchor) != 1:
    raise SystemExit("Expected exactly one include(extern.cmake) in CMakeLists.txt")
if link not in source:
    source = source.replace(anchor, anchor + "\n\n# ConfigUtils 3 uses reflect-cpp; link its QPM-restored implementation explicitly.\n" + link, 1)
if flamingo not in source:
    source = source.replace(link, link + "\n\n# Hook 9.4 delegates hook installation to Flamingo; link its QPM-restored implementation.\n" + flamingo, 1)
cmake.write_text(source)

defaults = Path("src/defaults.cpp")
source = defaults.read_text()
anchor = '#include "BGLib/UnityExtension/AddressablesExtensions.hpp"'
include = '#include "System/Collections/Generic/zzzz__IList_1_impl.hpp"'
if source.count(anchor) != 1:
    raise SystemExit("defaults.cpp no longer matches the pinned Addressables include layout")
if include not in source:
    source = source.replace(anchor, anchor + "\n" + include, 1)
    defaults.write_text(source)
print("Explicit reflect-cpp and Flamingo links plus Cordl IList_1 template implementation are installed.")
PY
test -s extern/libs/libreflectcpp.so
"$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-nm" -D --defined-only extern/libs/libreflectcpp.so > /tmp/reflectcpp.symbols
c++filt < /tmp/reflectcpp.symbols > /tmp/reflectcpp.demangled
grep -q 'rfl::json::Writer::Writer()' /tmp/reflectcpp.demangled
grep -q 'yyjson_read_opts' /tmp/reflectcpp.symbols
grep -n 'libreflectcpp.so' CMakeLists.txt
grep -n 'zzzz__IList_1_impl.hpp' src/defaults.cpp

test -s extern/libs/libflamingo.so
"$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-nm" -D --defined-only extern/libs/libflamingo.so > /tmp/flamingo.symbols
c++filt < /tmp/flamingo.symbols > /tmp/flamingo.demangled
grep -F "flamingo::Install(flamingo::HookInfo&&)" /tmp/flamingo.demangled
grep -n "libflamingo.so" CMakeLists.txt
