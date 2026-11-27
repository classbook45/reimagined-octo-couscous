set -euo pipefail
sudo apt-get update
sudo apt-get install -y cmake ninja-build build-essential binutils
cmake --version
ninja --version
readelf --version
pwsh --version
