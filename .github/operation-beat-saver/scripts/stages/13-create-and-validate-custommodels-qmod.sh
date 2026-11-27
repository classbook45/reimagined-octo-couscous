set -euo pipefail
pwsh ./scripts/createqmod.ps1 -QmodName CustomModels
python3 - <<'PY'
import pathlib, struct, zipfile
path = pathlib.Path("CustomModels.qmod")
if not path.is_file():
    raise SystemExit("CustomModels.qmod was not created")
with zipfile.ZipFile(path) as archive:
    names = archive.namelist()
    libs = [archive.read(name) for name in names if name.endswith("libcustommodels.so")]
if not libs:
    raise SystemExit("QMOD does not contain libcustommodels.so")
valid = any(
    len(data) >= 20 and data[:4] == b"\x7fELF" and
    data[4] == 2 and data[5] == 1 and
    struct.unpack("<H", data[18:20])[0] == 183
    for data in libs
)
if not valid:
    raise SystemExit("CustomModels QMOD does not contain an ARM64 ELF library")
print("Validated ARM64 CustomModels QMOD:", path)
print("QMOD entries:", names)
PY
mkdir -p ../artifacts
cp CustomModels.qmod ../artifacts/
