#!/usr/bin/env python3
"""Quest/Android loader preflight for the packaged CustomModels QMOD.

This is a dependency-loader simulation, not a substitute for launching the
proprietary Beat Saber app on a Quest runtime.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import zipfile

ROOT = Path.cwd()
QMOD = ROOT / "CustomModels.qmod"
REPORT = ROOT.parent / "reports" / "runtime-preflight.txt"
TEMPLATE = ROOT / "mod.template.json"
REFLECT = ROOT / "extern" / "libs" / "libreflectcpp.so"

# Non-system DT_NEEDED providers expected from installed QMOD dependencies.
PROVIDERS = {
    "libbeatsaber-hook.so": {"beatsaber-hook"},
    "libflamingo.so": {"beatsaber-hook"},
    "libbsml.so": {"bsml"},
    "libcustom-types.so": {"custom-types"},
    "liblapiz.so": {"lapiz"},
    "libmetacore-bs.so": {"metacore-bs"},
    "libmetacore.so": {"metacore"},
    "libpaper2_scotland2.so": {"paper2_scotland2"},
    "libsl2.so": {"scotland2-loader"},
}
SYSTEM = {
    "libc.so", "libm.so", "libdl.so", "liblog.so", "libandroid.so",
    "libEGL.so", "libGLESv2.so", "libGLESv3.so", "libOpenSLES.so",
    "libz.so", "libjnigraphics.so", "libmediandk.so", "libvulkan.so",
}

def fail(message, lines):
    lines.append("FAIL: " + message)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")
    raise SystemExit(message)

def package():
    if not QMOD.is_file():
        fail("CustomModels.qmod is missing.", [])
    with zipfile.ZipFile(QMOD) as z:
        return z.namelist(), z.read("mod.json")

def patch_reflectcpp_if_needed(names, mod_json, lines):
    metadata = json.loads(mod_json)
    packaged = {Path(n).name for n in names}
    if "libreflectcpp.so" in packaged:
        lines.append("PASS: libreflectcpp.so is present in the QMOD.")
        return False
    if not REFLECT.is_file() or REFLECT.stat().st_size == 0:
        fail("libreflectcpp.so is a DT_NEEDED library but is absent from extern/libs.", lines)
    template = json.loads(TEMPLATE.read_text())
    library_files = template.setdefault("libraryFiles", [])
    if "libreflectcpp.so" not in library_files:
        library_files.append("libreflectcpp.so")
        TEMPLATE.write_text(json.dumps(template, indent=2) + "\n")
        lines.append("AUTO-FIX: added libreflectcpp.so to mod.template.json libraryFiles.")
    else:
        lines.append("AUTO-FIX: template already declares libreflectcpp.so; rebuilding the QMOD.")
    subprocess.run(
        ["pwsh", "./scripts/createqmod.ps1", "-QmodName", "CustomModels"],
        cwd=ROOT, check=True
    )
    return True

def inspect():
    lines = [
        "CustomModels Android/Quest loader preflight",
        "Mode: static ELF + QMOD dependency simulation; no Beat Saber process is launched.",
    ]
    names, mod_json = package()
    changed = patch_reflectcpp_if_needed(names, mod_json, lines)
    if changed:
        names, mod_json = package()
    metadata = json.loads(mod_json)
    archive = zipfile.ZipFile(QMOD)
    packaged = {Path(n).name for n in names}
    deps = {d.get("id") for d in metadata.get("dependencies", [])}
    main = next((n for n in names if Path(n).name == "libcustommodels.so"), None)
    if not main:
        fail("QMOD has no libcustommodels.so.", lines)
    extracted = ROOT / "build" / "runtime-preflight-libcustommodels.so"
    extracted.parent.mkdir(parents=True, exist_ok=True)
    extracted.write_bytes(archive.read(main))
    ndk = Path(__import__("os").environ.get("ANDROID_NDK_HOME", ""))
    readelf = ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"
    if not readelf.is_file():
        readelf = Path(shutil.which("llvm-readelf") or "llvm-readelf")
    result = subprocess.run([str(readelf), "-d", str(extracted)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        fail("llvm-readelf could not inspect libcustommodels.so: " + result.stdout[-3000:], lines)
    needed = sorted(set(re.findall(r"Shared library: \[(.+?)\]", result.stdout)))
    lines.append("DT_NEEDED libraries:")
    lines.extend("  " + item for item in needed)
    errors = []
    for lib in needed:
        if lib in packaged or lib in SYSTEM:
            continue
        providers = PROVIDERS.get(lib)
        if providers and (providers & deps):
            continue
        if lib == "libreflectcpp.so" and lib in packaged:
            continue
        errors.append(lib)
    if errors:
        fail("unresolved runtime library providers: " + ", ".join(errors), lines)
    if "libreflectcpp.so" not in packaged:
        fail("libreflectcpp.so remains absent after packaging repair.", lines)
    lines += [
        "PASS: every DT_NEEDED entry is packaged, an Android system library, or supplied by a declared Quest dependency.",
        "PASS: libreflectcpp.so is bundled because it is directly linked by CustomModels.",
        "LIMITATION: this does not execute Beat Saber, Unity/IL2CPP, Scotland2, or mod initialization; a real Quest runtime log is still required to prove startup stability.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")
    shutil.copy2(QMOD, ROOT.parent / "artifacts" / "CustomModels.qmod")
    print("\n".join(lines))

if __name__ == "__main__":
    inspect()
