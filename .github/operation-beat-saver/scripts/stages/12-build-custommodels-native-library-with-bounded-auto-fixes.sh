set -euo pipefail
# Apply the previously buildable 1.45.3 source port here, immediately before compilation.
# Keep the Unity AssetBundle compatibility fix as a separate, narrow patch.
python3 "$GITHUB_WORKSPACE/.github/operation-beat-saver/scripts/port_custommodels_1453.py"
python3 "$GITHUB_WORKSPACE/.github/operation-beat-saver/scripts/apply_assetbundle_loader_patch.py"
git diff --check
test -f qpm_defines.cmake
rm -rf build
cmake -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DHOT_RELOAD=OFF -B build .
python3 ../.github/operation-beat-saver/scripts/autofix_custommodels_build.py
LIBRARY="$(find build -type f -name 'libcustommodels.so' -print -quit)"
test -n "$LIBRARY"
file "$LIBRARY"
readelf -h "$LIBRARY" | grep -E 'Class:|Machine:'
