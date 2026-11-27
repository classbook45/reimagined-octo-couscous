set -euo pipefail
python3 - <<'PY'
import json, os
from pathlib import Path

qpm_path = Path("qpm.json")
shared_path = Path("qpm.shared.json")
qpm = json.loads(qpm_path.read_text())
shared = json.loads(shared_path.read_text())

def align(config):
    config.setdefault("workspace", {})["ndk"] = "^29.0.0"
    target_ranges = {
        "beatsaber-hook": os.environ["HOOK_RANGE"],
        "bs-cordl": os.environ["CORDL_RANGE"],
        # The 1.45.3 mod catalog requires MetaCore 2.0.6.
        # CustomModels' upstream lockfile still pins MetaCore 1.4.0,
        # which cannot coexist with the installed core-mod graph.
        "metacore": "^2.0.6",
        "custom-types": "^0.21.2",
        # Lapiz 0.3.7 is the current line for Hook 9 / Cordl 4503
        # and supports CustomTypes 0.21.x (unlike Lapiz 0.2.x).
        "lapiz": "^0.3.7",
        "paper2_scotland2": "^4.8.0",
        # rapidjson-macros 2.1.0 requires Hook 6.x; v3.0.0 is
        # the compatible release used by current Hook 9.3 projects.
        "rapidjson-macros": "^3.0.0",
        # config-utils 2.x requires Hook 7.x and RapidJSON macros
        # 2.x; use the verified 3.0.0 line for Hook 9 projects.
        "config-utils": "^3.0.0",
        # BSML 0.4.x hard-pins CustomTypes 0.18.x; 0.6.7
        # supports the 0.21.x API used by this Beat Saber target.
        "bsml": "^0.6.7",
    }
    for dep in config.get("dependencies", []):
        dep_id = dep.get("id")
        if dep_id in target_ranges:
            dep["versionRange"] = target_ranges[dep_id]

    # MetaCore 2 split Beat Saber game-state headers into MetaCoreBS.
    # CustomModels still uses Game and Internals APIs from that package.
    if not any(dep.get("id") == "metacore-bs" for dep in config.get("dependencies", [])):
        config.setdefault("dependencies", []).append({
            "id": "metacore-bs",
            "versionRange": "^1.0.1",
            "additionalData": {},
        })

align(qpm)
align(shared["config"])

# Refresh the complete dependency graph so the generated QMOD no
# longer carries the incompatible MetaCore 1.4.0 dependency lock.
qpm_path.write_text(json.dumps(qpm, indent=2) + "\n")
shared_path.write_text(json.dumps(shared, indent=2) + "\n")

template = json.loads(Path("mod.template.json").read_text())
template["packageVersion"] = os.environ["PACKAGE_VERSION"]
Path("mod.template.json").write_text(json.dumps(template, indent=2) + "\n")
PY
qpm ndk resolve -d
qpm restore --update
