#!/usr/bin/env python3
"""Violet — auto-fix common compile errors after first build attempt."""
import re, os, glob

log = open("build_attempt1.log").read()
fixed = []

# Fix 1: NMMutableArray typo
for f in glob.glob("Violet/**/*.h", recursive=True) + glob.glob("Violet/**/*.m", recursive=True):
    src = open(f).read()
    if "NMMutableArray" in src:
        open(f, "w").write(src.replace("NMMutableArray", "NSMutableArray"))
        fixed.append(f"NMMutableArray fix in {f}")

# Fix 2: implicit function declarations
undecl = set(re.findall(r"implicit declaration of function '(\w+)'", log))
if undecl:
    hdr = "Violet/Core/BQEscape.h"
    src = open(hdr).read() if os.path.exists(hdr) else ""
    for fn in undecl:
        if fn not in src:
            src += f"\nvoid {fn}(void); // auto-injected\n"
            fixed.append(f"extern {fn}")
    open(hdr, "w").write(src)

# Fix 3: missing UniformTypeIdentifiers import
for f in glob.glob("Violet/**/*.m", recursive=True):
    src = open(f).read()
    if "UTType" in src and "UniformTypeIdentifiers" not in src:
        open(f, "w").write(
            "#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>\n" + src)
        fixed.append(f"UTI import in {f}")

print("Fixes applied:" if fixed else "No fixes needed.")
for item in fixed:
    print(f"  {item}")
