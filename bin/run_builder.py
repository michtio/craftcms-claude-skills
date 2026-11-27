#!/usr/bin/env python3
"""Run one outside builder per docs/outside-builders.md, with its timeout.

Usage:
    python3 bin/run_builder.py --cwd <project-root> --timeout-minutes <n> \
        --command '<command>' [--log <file>] <brief-file> <handback-file>

Runs `<command> <brief-file> <handback-file>` through sh, from the project root,
in its own process group. The brief and hand-back paths are made absolute first.
The builder's stdout and stderr go to --log when given (for example
<work>/log-<name>.txt), otherwise to this script's own output.

When the builder has not exited within the timeout, the whole process group is
killed: SIGTERM, up to 10 seconds of polling, then SIGKILL to the group even when
the leader has already exited (a child that ignores SIGTERM dies too). When this
script itself gets SIGTERM, SIGINT or SIGHUP, it kills the group the same way and
exits 128 + the signal number.

Prints one last line, `builder exit: <n>` or `builder exit: timeout`.
Exit codes:
    the builder's own exit code (128 + n when a signal killed it)
    124  timeout (failed, per the protocol)
    64   usage error in this script (bad arguments, missing --cwd directory,
         unwritable --log); never a builder result
Standard library only.
"""

import argparse
import os
import signal
import subprocess
import sys
import time

USAGE_ERROR = 64


class Usage(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"run_builder.py: {message}", file=sys.stderr)
        sys.exit(USAGE_ERROR)


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def kill_group(pgid, proc):
    """TERM the group, poll up to 10 seconds, then always KILL the group."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        proc.poll()
        if not group_alive(pgid):
            break
        time.sleep(0.1)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def main():
    ap = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cwd", required=True, help="the project root")
    ap.add_argument("--timeout-minutes", type=float, required=True)
    ap.add_argument("--command", required=True, help="the builder's command from the profile")
    ap.add_argument("--log", help="file for the builder's stdout and stderr")
    ap.add_argument("brief")
    ap.add_argument("handback")
    args = ap.parse_args()
    if not args.timeout_minutes > 0 or not os.path.isdir(args.cwd):
        ap.error("--timeout-minutes must be above 0 and --cwd a directory")
    brief, handback = os.path.abspath(args.brief), os.path.abspath(args.handback)
    out = None
    if args.log:
        try:
            out = open(os.path.abspath(args.log), "ab")
        except OSError as err:
            ap.error(f"cannot open --log: {err}")

    cmd = ["sh", "-c", args.command + ' "$1" "$2"', "sh", brief, handback]
    proc = subprocess.Popen(cmd, cwd=args.cwd, start_new_session=True, stdin=subprocess.DEVNULL,
                            stdout=out, stderr=subprocess.STDOUT if out else None)
    pgid = proc.pid  # start_new_session: the leader's pid is the group id

    def on_signal(signum, _frame):
        kill_group(pgid, proc)
        print(f"builder exit: interrupted (signal {signum})", flush=True)
        sys.exit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, on_signal)

    try:
        code = proc.wait(timeout=args.timeout_minutes * 60)
    except subprocess.TimeoutExpired:
        kill_group(pgid, proc)
        print("builder exit: timeout", flush=True)
        return 124
    if group_alive(pgid):
        # The leader exited but left children behind in its group: clean them up.
        kill_group(pgid, proc)
    if code < 0:  # killed by a signal
        code = 128 - code
    print(f"builder exit: {code}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
