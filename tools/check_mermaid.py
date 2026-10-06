"""Validate every ```mermaid block under design/ by rendering it with mmdc.

Rendered SVGs go to analysis/mermaid/ (throwaway, for visual checks).
Exit code 1 if any diagram fails to parse.

Usage: python tools/check_mermaid.py [path ...]   (default: design/)
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "mermaid"
BLOCK_RE = re.compile(r"^```mermaid\s*\n(.*?)^```", re.M | re.S)


def main():
    targets = [Path(p) for p in sys.argv[1:]] or [ROOT / "design"]
    files = []
    for t in targets:
        files += sorted(t.rglob("*.md")) if t.is_dir() else [t]

    mmdc = shutil.which("mmdc") or shutil.which("mmdc.cmd")
    if not mmdc:
        sys.exit("mmdc not found: npm install -g @mermaid-js/mermaid-cli")

    OUT.mkdir(parents=True, exist_ok=True)
    failed = total = 0
    for md in files:
        text = md.read_text(encoding="utf-8")
        for i, m in enumerate(BLOCK_RE.finditer(text), 1):
            total += 1
            line = text[:m.start()].count("\n") + 1
            name = f"{md.stem}_{i}"
            src = OUT / f"{name}.mmd"
            src.write_text(m.group(1), encoding="utf-8")
            r = subprocess.run([mmdc, "-q", "-i", str(src), "-o", str(OUT / f"{name}.svg")],
                               capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 0:
                failed += 1
                err = (r.stderr or r.stdout).strip().splitlines()
                print(f"NG {md.relative_to(ROOT)}:{line}  {err[0] if err else ''}")
    print(f"{total - failed}/{total} mermaid diagrams OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
