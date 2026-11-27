#!/usr/bin/env python3
"""Bounded, diagnostics-driven compatibility fixer for CustomModels on BS 1.45.3.

Only applies reviewed, semantics-preserving include-path corrections. Unknown
compiler errors are reported verbatim and are never rewritten speculatively.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()
SOURCE_DIRS = (ROOT / "include", ROOT / "src")
RULES = {
    '"metacorebs/shared/input.hpp"': '"metacore-bs/shared/input.hpp"',
    '"metacore/shared/input.hpp"': '"metacore-bs/shared/input.hpp"',
    '"beatsaber-hook/shared/utils/hooking.hpp"': '"beatsaber-hook/shared/hooking.hpp"',
    '"beatsaber-hook/shared/utils/logging.hpp"': '"beatsaber-hook/shared/utils.hpp"',
}
MAX_ATTEMPTS = 3

def source_files():
    for directory in SOURCE_DIRS:
        if directory.exists():
            yield from (p for p in directory.rglob("*")
                        if p.is_file() and p.suffix in {".h", ".hpp", ".cpp"})

def apply_reviewed_fixes():
    changed = []
    for path in source_files():
        before = path.read_text()
        after = before
        for old, new in RULES.items():
            after = after.replace(old, new)
        if after != before:
            path.write_text(after)
            changed.append(str(path.relative_to(ROOT)))
    return changed

def run_build():
    proc = subprocess.run(
        ["cmake", "--build", "build", "--parallel"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print(proc.stdout, flush=True)
    return proc.returncode, proc.stdout

def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== CustomModels build attempt {attempt}/{MAX_ATTEMPTS} ===", flush=True)
        code, output = run_build()
        if code == 0:
            print("CustomModels native build passed.")
            return 0
        fixed = apply_reviewed_fixes()
        if fixed:
            print("Applied reviewed compatibility fixes:")
            print("\n".join(f"  - {name}" for name in fixed))
            continue
        missing = re.findall(r"fatal error: ['<]([^'>]+)['>] file not found", output)
        print("\nAUTO-FIX STOPPED: no reviewed safe fix matches this compiler failure.", file=sys.stderr)
        if missing:
            print("Missing headers: " + ", ".join(sorted(set(missing))), file=sys.stderr)
        errors = [line for line in output.splitlines()
                  if re.search(r"(?:error:|fatal error:|undefined reference|FAILED:|ninja: build stopped)", line)]
        print("Compiler diagnostics:", file=sys.stderr)
        print("\n".join(errors[-100:]) or output[-12000:], file=sys.stderr)
        print("No speculative source edits were made.", file=sys.stderr)
        return code
    print("AUTO-FIX STOPPED after the bounded retry limit; inspect remaining diagnostics.", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
