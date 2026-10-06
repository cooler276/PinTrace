"""Aggregate #include dependencies between firmware components.

A component is the directory path under src/ truncated to --depth levels
(depth 1: modules, hal, drivers ...; depth 2: modules/src, deck/drivers ...).
The interface/ and src/ levels are folded so a header in modules/interface
and a source in modules/src belong to the same component.

Only files compiled for the platform (analysis/config/<platform>/filelist.txt)
and the headers they reach are counted. Headers from vendor/ are reported as
"vendor:<name>".

Output: TSV lines "from<TAB>to<TAB>count" (sorted by count), to stdout.

Usage: python tools/include_deps.py [--platform cf2] [--depth 1] [--file-level]
  --file-level  print "src_file<TAB>header_file" pairs instead of the matrix
"""
import argparse
import collections
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "crazyflie-firmware"
INC_RE = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]', re.M)
FOLD = {"interface", "src"}


def component(rel, depth):
    parts = rel.split("/")
    if parts[0] == "vendor":
        return "vendor:" + parts[1]
    parts = [p for p in parts[1:-1] if p not in FOLD]  # drop "src/" root and file name
    return "/".join(parts[:depth]) or "(root)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="cf2")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--file-level", action="store_true")
    args = ap.parse_args()

    # header basename -> firmware-relative paths (src and vendor)
    headers = collections.defaultdict(list)
    for top in ("src", "vendor/FreeRTOS/include", "vendor/CMSIS/CMSIS",
                "vendor/libdw1000/inc"):
        for h in (FW / top).rglob("*.h"):
            headers[h.name].append(h.relative_to(FW).as_posix())

    filelist = (ROOT / "analysis" / "config" / args.platform / "filelist.txt").read_text().split()
    sources = [f for f in filelist if f.startswith("src/")]

    pairs = set()
    seen, todo = set(), list(sources)
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        text = (FW / f).read_text(encoding="utf-8", errors="replace")
        for inc in INC_RE.findall(text):
            cands = headers.get(Path(inc).name, [])
            if not cands:
                continue  # libc / generated headers
            # prefer a header in the same directory, then under src/
            same = [c for c in cands if Path(c).parent == Path(f).parent]
            pick = (same or [c for c in cands if c.startswith("src/")] or cands)[0]
            pairs.add((f, pick))
            if pick.startswith("src/"):
                todo.append(pick)

    if args.file_level:
        for a, b in sorted(pairs):
            print(f"{a}\t{b}")
        return

    counts = collections.Counter()
    for a, b in pairs:
        ca, cb = component(a, args.depth), component(b, args.depth)
        if ca != cb:
            counts[(ca, cb)] += 1
    for (a, b), n in counts.most_common():
        print(f"{a}\t{b}\t{n}")


if __name__ == "__main__":
    main()
