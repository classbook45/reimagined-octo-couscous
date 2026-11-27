set -euo pipefail
test -f qpm_defines.cmake
rm -rf build
cmake -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DHOT_RELOAD=OFF -B build .
python3 ../.github/operation-beat-saver/scripts/autofix_custommodels_build.py
LIBRARY="$(find build -type f -name 'libcustommodels.so' -print -quit)"
test -n "$LIBRARY"
file "$LIBRARY"
readelf -h "$LIBRARY" | grep -E 'Class:|Machine:'
