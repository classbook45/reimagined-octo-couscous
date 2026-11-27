set -euo pipefail
git clone https://github.com/Metalit/CustomModels.git CustomModels
git -C CustomModels checkout --detach "$CUSTOMMODELS_REVISION"
git -C CustomModels submodule update --init --recursive
test "$(git -C CustomModels rev-parse HEAD)" = "$CUSTOMMODELS_REVISION"
echo "CustomModels source pinned at $CUSTOMMODELS_REVISION"
