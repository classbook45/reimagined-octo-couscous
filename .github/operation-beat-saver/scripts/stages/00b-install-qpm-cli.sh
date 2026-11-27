set -euo pipefail
curl --retry 3 --retry-all-errors --retry-delay 3 -fsSL -o /tmp/qpm.zip https://github.com/QuestPackageManager/QPM.CLI/releases/latest/download/qpm-linux-x64.zip
unzip -oq /tmp/qpm.zip -d /tmp/qpm
QPM_BIN="$(find /tmp/qpm -type f -name qpm -print -quit)"
test -n "$QPM_BIN"
sudo install -m 755 "$QPM_BIN" /usr/local/bin/qpm
qpm --version
