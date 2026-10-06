"""Collect the "未解決事項" section of every design document into
design/99_appendix/open_issues.md (regenerate after editing any document).

The part of open_issues.md above the AUTO-GENERATED marker is kept as is,
so hand-written summaries survive regeneration.

Usage: python tools/collect_open_issues.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "design"
OUT = DESIGN / "99_appendix" / "open_issues.md"
MARKER = "<!-- AUTO-GENERATED BELOW: python tools/collect_open_issues.py -->"
SECTION = re.compile(r"^## 未解決事項\s*$(.*?)(?=^## |\Z)", re.M | re.S)


def main():
    head = OUT.read_text(encoding="utf-8").split(MARKER)[0] if OUT.exists() else "# 未解決事項\n\n"
    parts, total = [], 0
    for md in sorted(DESIGN.rglob("*.md")):
        if md == OUT or md.name in ("README.md", "_template.md"):
            continue
        m = SECTION.search(md.read_text(encoding="utf-8"))
        if not m:
            continue
        items = [l for l in m.group(1).strip().splitlines() if l.startswith("- ")]
        if not items:
            continue
        total += len(items)
        rel = md.relative_to(DESIGN).as_posix()
        title = md.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        # links inside items are relative to the source document; point them from 99_appendix
        fixed = [re.sub(r"\]\((?!http)([^)]+)\)",
                        lambda x: "](" + Path("..", md.parent.relative_to(DESIGN), x.group(1)).as_posix() + ")", i)
                 for i in items]
        parts.append(f"### [{title}](../{rel})\n\n" + "\n".join(fixed) + "\n")
    body = f"{MARKER}\n\n## 文書ごとの未解決事項（{total} 件）\n\n" + "\n".join(parts)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(head.rstrip() + "\n\n" + body, encoding="utf-8")
    print(f"{total} items from {len(parts)} documents -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
