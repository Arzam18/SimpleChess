#!/usr/bin/env python3
"""UCI smoke test for a built engine, native or under an emulator.

    python3 -u tools/ci/uci_smoke.py ./simplechess
    python3 -u tools/ci/uci_smoke.py qemu-aarch64-static /abs/path/simplechess --depth 12

Starts the engine, requires `uciok`, `readyok` and the "NNUE loaded" info string (the engine
does not run without its net, so a build whose net is missing or unreadable fails here), then
searches a fixed set of positions to --depth at 1 thread and prints, per position, the final
`info` line and the `bestmove`. Two builds of the same source can be compared by diffing that
output: at 1 thread the search is deterministic, so identical node counts mean the same engine.

Exit status is 0 only when every expected line arrived in time. stdout is read until the
`bestmove` line BEFORE `quit` is sent: a `quit` right after `go` aborts the search and returns
the first legal move, which would let a broken build pass. Every result line is flushed as it
completes so a log shows progress in real time.
"""

import argparse
import queue
import subprocess
import sys
import threading
import time

POSITIONS = [
    ("startpos", "position startpos"),
    ("italian", "position fen r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"),
    ("kpk-r50", "position fen 8/8/4k3/8/2K5/8/4P3/8 w - - 60 90"),
    ("tactic", "position fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
]


class Engine:
    def __init__(self, cmd):
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line.rstrip("\n"))
        self.lines.put(None)

    def send(self, s):
        self.proc.stdin.write(s + "\n")
        self.proc.stdin.flush()

    def read_until(self, pred, timeout):
        """Collect lines until pred(line) is true; returns (matched_line, all_lines) or (None, all)."""
        deadline = time.monotonic() + timeout
        got = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, got
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                return None, got
            if line is None:
                return None, got
            got.append(line)
            if pred(line):
                return line, got


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="+", help="engine command (an emulator prefix is fine)")
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--hash", type=int, default=16, help="Hash MB (set before isready)")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=600.0, help="seconds per search")
    ap.add_argument("--evalfile", default=None, help="setoption EvalFile (default: engine's own discovery)")
    args = ap.parse_args()

    def out(s):
        print(s, flush=True)

    eng = Engine(args.cmd)
    ok = True

    # The engine loads its net at startup, before any command, so the "NNUE loaded" line can
    # arrive ahead of `uciok` or (with EvalFile) ahead of `readyok`: look in both phases.
    eng.send("uci")
    line, got = eng.read_until(lambda l: l == "uciok", 60)
    ident = [l for l in got if l.startswith("id name")]
    out(f"id:      {ident[0][8:] if ident else '<no id name line>'}")
    if line is None:
        out("FAIL: no uciok")
        for l in got:
            out("  | " + l)
        return 1
    seen = list(got)

    eng.send(f"setoption name Hash value {args.hash}")
    eng.send(f"setoption name Threads value {args.threads}")
    if args.evalfile:
        eng.send(f"setoption name EvalFile value {args.evalfile}")
    eng.send("isready")
    line, got = eng.read_until(lambda l: l == "readyok", 120)
    seen += got
    for l in seen:
        if l.startswith("info string") or l.startswith("FATAL"):
            out("engine:  " + l)
    if line is None:
        out("FAIL: no readyok")
        return 1
    if not any("NNUE loaded" in l for l in seen):
        out("FAIL: net did not load (no 'NNUE loaded' info string)")
        ok = False

    for name, cmd in POSITIONS:
        eng.send("ucinewgame")
        eng.send(cmd)
        t0 = time.monotonic()
        eng.send(f"go depth {args.depth}")
        bm, got = eng.read_until(lambda l: l.startswith("bestmove"), args.timeout)
        dt = time.monotonic() - t0
        infos = [l for l in got if l.startswith("info depth")]
        last = infos[-1] if infos else "<no info line>"
        if bm is None:
            out(f"FAIL {name}: no bestmove within {args.timeout:.0f}s; last: {last}")
            ok = False
            break
        # Keep the comparable fields (depth/score/nodes) and drop the timing ones.
        toks = last.split()
        keep = {}
        for i, t in enumerate(toks):
            if t in ("depth", "nodes", "cp", "mate") and i + 1 < len(toks):
                keep[t] = toks[i + 1]
        score = f"cp {keep['cp']}" if "cp" in keep else (f"mate {keep['mate']}" if "mate" in keep else "?")
        out(f"{name:9} depth {keep.get('depth', '?'):>2}  score {score:>9}  nodes {keep.get('nodes', '?'):>9}  "
            f"{bm}  ({dt:.1f}s)")
        if keep.get("depth") != str(args.depth):
            out(f"FAIL {name}: reached depth {keep.get('depth')} not {args.depth}")
            ok = False

    eng.send("quit")
    try:
        eng.proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        eng.proc.kill()
        out("FAIL: engine did not exit on quit")
        ok = False
    out("SMOKE " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
