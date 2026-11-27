#!/usr/bin/env python3
"""Bounded, local-only recovery wrapper for every Operation Beat Saver shell stage.

Retries only failures classified as transient. Deterministic source/config/API errors
are reported with full diagnostics; project-specific repair remains in the port and
CustomModels compiler repair helpers.
"""
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys
import time

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
LOG_DIR = ROOT / "reports" / "stage-logs"
MAX_ATTEMPTS = 3

TRANSIENT = (
    re.compile(r"could not resolve host|temporary failure in name resolution|connection timed out|connection reset|TLS handshake timeout|remote end hung up", re.I),
    re.compile(r"429 too many requests|HTTP 5\d\d|502 bad gateway|503 service unavailable|504 gateway timeout", re.I),
    re.compile(r"Could not get lock .*apt|Could not open lock file|dpkg frontend lock", re.I),
    re.compile(r"unexpected eof|early eof|fetch-pack: invalid index-pack output|curl .*error 56", re.I),
)

def is_transient(output):
    return any(pattern.search(output) for pattern in TRANSIENT)

def repair_transient(stage, output):
    """Perform only narrow, safe repairs for known runner/transient failures."""
    changed = False
    if re.search(r"Could not get lock .*apt|Could not open lock file|dpkg frontend lock", output, re.I):
        print("AUTO-REPAIR: waiting for apt/dpkg locks and completing interrupted package configuration.", flush=True)
        time.sleep(12)
        p = subprocess.run(["sudo", "dpkg", "--configure", "-a"], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(p.stdout[-5000:], flush=True)
        changed = p.returncode == 0
    if stage.startswith("clone-pinned-custommodels") and is_transient(output):
        target = ROOT / "CustomModels"
        if target.exists() and not (target / ".git").exists():
            import shutil
            print("AUTO-REPAIR: removing incomplete CustomModels clone before retry.", flush=True)
            shutil.rmtree(target)
            changed = True
    if re.search(r"Could not resolve host|Temporary failure in name resolution|connection timed out|TLS handshake timeout", output, re.I):
        print("AUTO-REPAIR: transient network failure detected; waiting before bounded retry.", flush=True)
        time.sleep(15)
        changed = True
    if re.search(r"429 too many requests|HTTP 5\d\d|502 bad gateway|503 service unavailable|504 gateway timeout", output, re.I):
        print("AUTO-REPAIR: upstream rate-limit/server response detected; backing off before retry.", flush=True)
        time.sleep(20)
        changed = True
    if re.search(r"unexpected eof|early eof|fetch-pack: invalid index-pack output|curl .*error 56", output, re.I):
        print("AUTO-REPAIR: incomplete network transfer detected; retrying the idempotent stage.", flush=True)
        time.sleep(8)
        changed = True
    return changed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--script", required=True)
    args = parser.parse_args()

    script = Path(args.script)
    if not script.is_file():
        raise SystemExit(f"Stage script is missing: {script}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{args.stage}.log"

    last_code = 1
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== AUTO-FIX STAGE: {args.stage} ({attempt}/{MAX_ATTEMPTS}) ===", flush=True)
        proc = subprocess.run(["bash", "--noprofile", "--norc", str(script)],
                              cwd=Path.cwd(), text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=os.environ.copy())
        output = proc.stdout or ""
        print(output[-30000:], flush=True)
        log_path.write_text(output)
        last_code = proc.returncode
        if last_code == 0:
            print(f"AUTO-FIX STAGE PASS: {args.stage}", flush=True)
            return 0
        if attempt == MAX_ATTEMPTS or not is_transient(output):
            break
        if not repair_transient(args.stage, output):
            break
        print("AUTO-RETRY: rerunning the failed stage after safe recovery.", flush=True)

    print(f"\nAUTO-FIX STAGE FAILED: {args.stage}; exit={last_code}", file=sys.stderr)
    print(f"Full stage log: {log_path}", file=sys.stderr)
    print("The failure was not safely auto-repairable; no speculative source edits were made.", file=sys.stderr)
    return last_code or 1

if __name__ == "__main__":
    raise SystemExit(main())
