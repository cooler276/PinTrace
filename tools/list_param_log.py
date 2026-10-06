"""List param / log groups and variables defined in the files a platform compiles.

Scans *_GROUP_START(name) ... *_GROUP_STOP(name) blocks and the
PARAM_ADD* / LOG_ADD* entries inside them (text based: #ifdef inside a
group is NOT evaluated, so counts are an upper bound).

Output (stdout, TSV): kind  group  n_vars  n_core  n_persistent  file:line  names

Usage: python tools/list_param_log.py [--platform cf2] [--kind param|log]
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "crazyflie-firmware"

START = re.compile(r"\b(PARAM|LOG)_GROUP_START\s*\(\s*(\w+)\s*\)")
ADD = re.compile(r"\b(PARAM|LOG)_ADD(_CORE|_WITH_CALLBACK|_CORE_WITH_CALLBACK|_BY_FUNCTION|_FULL|_GROUP)?\s*\(([^;]*?)\)\s*$", re.M)
STATS = re.compile(r"\bSTATS_CNT_RATE_LOG_ADD\s*\(\s*(\w+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="cf2")
    ap.add_argument("--kind", choices=["param", "log"])
    a = ap.parse_args()

    files = [f for f in (ROOT / "analysis" / "config" / a.platform / "filelist.txt").read_text().split()
             if f.startswith("src/") and f.endswith(".c")]
    for f in files:
        text = (FW / f).read_text(encoding="utf-8", errors="replace")
        for m in START.finditer(text):
            kind, group = m.group(1).lower(), m.group(2)
            if a.kind and kind != a.kind:
                continue
            stop = re.search(rf"\b{m.group(1)}_GROUP_STOP\s*\(\s*{group}\s*\)", text[m.end():])
            body = text[m.end(): m.end() + (stop.start() if stop else 0)]
            names, core, pers = [], 0, 0
            for e in ADD.finditer(body):
                if e.group(1).lower() != kind:
                    continue
                args = [x.strip() for x in e.group(3).split(",")]
                if len(args) >= 2:
                    names.append(args[1])
                core += "CORE" in (e.group(2) or "")
                pers += "PERSISTENT" in args[0]
            names += STATS.findall(body)
            line = text[:m.start()].count("\n") + 1
            print(f"{kind}\t{group}\t{len(names)}\t{core}\t{pers}\t{f}:{line}\t{' '.join(names)}")


if __name__ == "__main__":
    main()
