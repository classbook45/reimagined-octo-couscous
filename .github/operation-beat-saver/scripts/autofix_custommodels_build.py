#!/usr/bin/env python3
"""Diagnostics-driven, local-only CustomModels repair/build loop for Beat Saber 1.45.3.

The helper has no network calls and no external AI dependency. It applies only
explicit, reviewed source migrations or uniquely-resolved missing headers,
then retries the real CMake build. Advanced mode allows eight diagnostics-driven repair passes and records each source change. Unknown/ambiguous diagnostics are reported rather than guessed at.
"""
from pathlib import Path
import hashlib
import re
import subprocess
import sys

ROOT = Path.cwd()
SOURCE_DIRS = (ROOT / "include", ROOT / "src")
DEPENDENCY_HEADERS = ROOT / "extern" / "includes"
MAX_ATTEMPTS = 12

def source_files():
    for directory in SOURCE_DIRS:
        if directory.exists():
            yield from (p for p in directory.rglob("*")
                        if p.is_file() and p.suffix in {".h", ".hpp", ".cpp"})

def replace_exact(path, old, new, expected=1):
    if not path.exists():
        return False
    before = path.read_text()
    count = before.count(old)
    if count == 0:
        return False
    if count != expected:
        raise RuntimeError(f"{path.relative_to(ROOT)}: expected {expected} occurrence(s), found {count}; refusing patch")
    path.write_text(before.replace(old, new))
    print(f"FIXED {path.relative_to(ROOT)}: {old[:90]!r}")
    return True

def apply_reviewed_source_fixes():
    changed = []
    rules = {
        "src/saber.cpp": [
            ("""if (auto child = trails->FirstOrDefault([id = trail.info.trailId](auto trail) { return trail->trailId == id; }))
                UpdateTrailColor(child, menu, trail);""",
             """CustomSaberTrail* child = nullptr;
            for (auto candidate : trails) {
                if (candidate && candidate->trailId == trail.info.trailId) {
                    child = candidate;
                    break;
                }
            }
            if (child)
                UpdateTrailColor(child, menu, trail);"""),
            ("""if (auto child = trails->FirstOrDefault([id = trail.info.trailId](auto trail) { return trail->trailId == id; }))
                    UpdateTrailPreview(child->transform, trail, menu);""",
             """CustomSaberTrail* child = nullptr;
                for (auto candidate : trails) {
                    if (candidate && candidate->trailId == trail.info.trailId) {
                        child = candidate;
                        break;
                    }
                }
                if (child)
                    UpdateTrailPreview(child->transform, trail, menu);"""),
        ],
        "src/selection.cpp": [
            ("""ArrayW<uint8_t>({(uint8_t*) bytes.data(), bytes.size()})""",
             """ArrayW<uint8_t>(std::vector<uint8_t>(bytes.begin(), bytes.end()))"""),
        ],
        "src/trail.cpp": [
            ("_trailRenderer->_mesh.unsafePtr()", "_trailRenderer->_mesh.unsafe_ptr()"),
            ("GlobalNamespace::TimeHelper::get_time()", "UnityEngine::Time::get_time()"),
        ],
        "src/settings.cpp": [
            ("auto& profiles = getConfig().Profiles;", "auto& profiles = getConfig().Profiles.GetValue();"),
        ],
        "include/settings.hpp": [
            ('DECLARE_OVERRIDE_METHOD(float, CellSize, ::i2c::find_method({"HMUI", "TableView/IDataSource"}, {"CellSize", 1}), int idx);',
             'DECLARE_OVERRIDE_METHOD(float, CellSize, ::i2c::find_method({"HMUI", "TableView/IDataSource"}, {"CellSize", 0}));'),
        ],
    }
    for relative, replacements in rules.items():
        path = ROOT / relative
        for old, new in replacements:
            if replace_exact(path, old, new):
                changed.append(relative)

    # ArrayW's Hook 9 constructor accepts std::vector; include it explicitly.
    selection = ROOT / "src/selection.cpp"
    if selection.exists():
        data = selection.read_text()
        if "std::vector<uint8_t>" in data and "#include <vector>" not in data:
            anchor = '#include "selection.hpp"'
            if data.count(anchor) != 1:
                raise RuntimeError("selection.cpp include anchor changed; refusing vector include insertion")
            selection.write_text(data.replace(anchor, anchor + "\n#include <vector>", 1))
            changed.append("src/selection.cpp (+ <vector>)")

    trail = ROOT / "src/trail.cpp"
    if trail.exists():
        data = trail.read_text()
        if "UnityEngine::Time::get_time()" in data and '#include "UnityEngine/Time.hpp"' not in data:
            anchor = '#include "trail.hpp"'
            if data.count(anchor) != 1:
                raise RuntimeError("trail.cpp include anchor changed; refusing UnityEngine/Time.hpp insertion")
            trail.write_text(data.replace(anchor, anchor + '\n#include "UnityEngine/Time.hpp"', 1))
            changed.append("src/trail.cpp (+ UnityEngine/Time.hpp)")
    return changed

def repair_unique_missing_headers(output):
    missing = sorted(set(re.findall(r"fatal error: ['<]([^'>]+)['>] file not found", output)))
    changed = []
    if not DEPENDENCY_HEADERS.is_dir():
        return changed
    for include in missing:
        basename = Path(include).name
        candidates = sorted(p for p in DEPENDENCY_HEADERS.rglob(basename) if p.is_file())
        if len(candidates) != 1:
            if candidates:
                print(f"HEADER NOT AUTO-RESOLVED: {include} has {len(candidates)} candidates:")
                for candidate in candidates[:20]:
                    print("  " + candidate.relative_to(DEPENDENCY_HEADERS).as_posix())
            continue
        replacement = candidates[0].relative_to(DEPENDENCY_HEADERS).as_posix()
        old = f'"{include}"'
        new = f'"{replacement}"'
        count = 0
        for path in source_files():
            before = path.read_text()
            occurrences = before.count(old)
            if occurrences:
                path.write_text(before.replace(old, new))
                count += occurrences
                print(f"FIXED HEADER {path.relative_to(ROOT)}: {include} -> {replacement}")
        if count:
            changed.append(f"{include} -> {replacement}")
    return changed

def repair_undefined_symbols(output):
    # Resolve known dependency-owned symbols by verifying the actual exported ABI.
    repairs = {
        'flamingo::Install(flamingo::HookInfo&&)': 'libflamingo.so',
    }
    symbols = sorted(set(re.findall(r'undefined symbol: ([^\\n]+)', output)))
    changed = []
    for symbol in symbols:
        library_name = next((name for needle, name in repairs.items() if needle in symbol), None)
        if not library_name:
            continue
        library = ROOT / 'extern' / 'libs' / library_name
        if not library.is_file() or library.stat().st_size == 0:
            print(f'SYMBOL REPAIR FAILED: required dependency library is missing: {library_name}')
            continue
        ndk = Path(__import__('os').environ.get('ANDROID_NDK_ROOT', ''))
        nm = ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-nm'
        if not nm.is_file():
            continue
        proc = subprocess.run([str(nm), '-D', '--defined-only', str(library)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        demangled = subprocess.run(['c++filt'], input=proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if not any(symbol in line for line in demangled.stdout.splitlines()):
            print(f'SYMBOL REPAIR REFUSED: {library_name} does not export {symbol}')
            continue
        cmake = ROOT / 'CMakeLists.txt'
        data = cmake.read_text()
        anchor = 'include(extern.cmake)'
        if data.count(anchor) != 1:
            print('SYMBOL REPAIR REFUSED: CMake insertion anchor is not unique.')
            continue
        link = 'target_link_libraries(${COMPILE_ID} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/extern/libs/' + library_name + '")'
        if link not in data:
            data = data.replace(anchor, anchor + '\\n\\n# Auto-linked after verifying the exported symbol: ' + symbol + '\\n' + link, 1)
            cmake.write_text(data)
            changed.append('CMakeLists.txt: linked ' + library_name + ' for ' + symbol)
            print('AUTO-LINKED ' + library_name + ': verified export for ' + symbol)
    return changed
def run_build():
    proc = subprocess.run(
        ["cmake", "--build", "build", "--parallel"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print(proc.stdout, flush=True)
    return proc.returncode, proc.stdout

def diagnostic_summary(output):
    patterns = re.compile(r"(?:error:|fatal error:|undefined reference|FAILED:|ninja: build stopped)")
    return [line.strip() for line in output.splitlines() if patterns.search(line)][-100:]

def fingerprint():
    digest = hashlib.sha256()
    for path in sorted([*source_files(), ROOT / 'CMakeLists.txt']):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()

def main():
    seen = set()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== CustomModels local repair/build attempt {attempt}/{MAX_ATTEMPTS} ===", flush=True)
        code, output = run_build()
        if code == 0:
            print("SUCCESS: CustomModels native build passed.")
            return 0

        before = fingerprint()
        fixed = apply_reviewed_source_fixes()
        fixed += repair_unique_missing_headers(output)
        fixed += repair_undefined_symbols(output)
        after = fingerprint()
        if before == after or after in seen:
            print("\nLOCAL REPAIR STOPPED: no new safe patch is available.", file=sys.stderr)
            print("Compiler diagnostics:", file=sys.stderr)
            print("\n".join(diagnostic_summary(output)) or output[-16000:], file=sys.stderr)
            print("No ambiguous or speculative edits were made.", file=sys.stderr)
            return code
        seen.add(after)
        print("\nApplied local repairs:")
        print("\n".join("  - " + item for item in fixed) or "  - dependency header resolution")
        print("Retrying the actual CMake build with the changed source...", flush=True)

    print("\nLOCAL REPAIR STOPPED after the bounded retry limit.", file=sys.stderr)
    print("Inspect the latest compiler diagnostics; the helper will not guess at unknown API changes.", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
