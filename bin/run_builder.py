#!/usr/bin/env python3
"""Run one outside builder per docs/outside-builders.md, with its timeout.

Usage:
    python3 bin/run_builder.py --cwd <project-root> --timeout-minutes <n> \
        --command '<command>' <brief-file> <handback-file>

Runs `<command> <brief-file> <handback-file>` through sh, from the project root,
in its own process group. When it has not exited within the timeout, the whole
process group is killed (TERM, then KILL after 10 seconds).

Prints one last line, `builder exit: <n>` or `builder exit: timeout`, and exits
with the builder's own exit code, or 124 on a timeout (failed, per the
protocol). Exit 2: usage error. Standard library only.
"""

import argparse
import os
import signal
import subprocess
import sys


def kill_group(proc):
    for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cwd", required=True, help="the project root")
    ap.add_argument("--timeout-minutes", type=float, required=True)
    ap.add_argument("--command", required=True, help="the builder's command from the profile")
    ap.add_argument("brief")
    ap.add_argument("handback")
    args = ap.parse_args()
    if args.timeout_minutes <= 0 or not os.path.isdir(args.cwd):
        print("run_builder.py: timeout must be above 0 and --cwd a directory", file=sys.stderr)
        return 2
    cmd = ["sh", "-c", args.command + ' "$1" "$2"', "sh", args.brief, args.handback]
    proc = subprocess.Popen(cmd, cwd=args.cwd, start_new_session=True, stdin=subprocess.DEVNULL)
    try:
        code = proc.wait(timeout=args.timeout_minutes * 60)
    except subprocess.TimeoutExpired:
        kill_group(proc)
        print("builder exit: timeout", flush=True)
        return 124
    if code < 0:  # killed by a signal
        code = 128 - code
    print(f"builder exit: {code}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
