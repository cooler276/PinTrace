"""List the source files Kbuild compiles for one platform.

Walks the Kbuild tree from the firmware root (src, vendor, app_api) and
evaluates obj-y / obj-$(CONFIG_X) against analysis/config/<platform>/.config
(run gen_config.py first).

Outputs (under analysis/config/<platform>/):
  filelist.txt     compiled .c/.S files, relative to the firmware root
  excluded.txt     .c files under src/ that this platform does NOT compile

Usage: python tools/gen_filelist.py [platform]   (default: cf2)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "crazyflie-firmware"

OBJ_RE = re.compile(r"^\s*obj-(y|\$\((CONFIG_\w+)\))\s*\+?=\s*(.*)$")
COND_RE = re.compile(r"^\s*(ifeq|ifneq)\s*\(\$\((CONFIG_\w+)\),\s*(.*?)\)\s*$")


def load_config(path):
    cfg = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^(CONFIG_\w+)=(.*)$", line)
        if m:
            cfg[m.group(1)] = m.group(2)
    return cfg


def walk(directory, cfg, out, unresolved):
    kbuild = directory / "Kbuild"
    if not kbuild.exists():
        unresolved.append(f"no Kbuild: {directory.relative_to(FW)}")
        return
    stack = []  # nesting of ifeq/ifneq results
    for raw in kbuild.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        m = COND_RE.match(line)
        if m:
            kind, sym, expected = m.groups()
            equal = cfg.get(sym, "") == expected.strip()
            stack.append(equal if kind == "ifeq" else not equal)
            continue
        if line.strip() == "else":
            stack[-1] = not stack[-1]
            continue
        if line.strip() == "endif":
            stack.pop()
            continue
        if not all(stack):
            continue
        m = OBJ_RE.match(line)
        if not m:
            continue
        _, sym, items = m.groups()
        if sym and cfg.get(sym) != "y":
            continue
        for item in items.split():
            if item.endswith("/"):
                walk(directory / item, cfg, out, unresolved)
            elif item.endswith(".o"):
                stem = directory / item[:-2]
                for ext in (".c", ".S", ".s"):
                    if stem.with_suffix(ext).exists():
                        out.append(stem.with_suffix(ext))
                        break
                else:
                    unresolved.append(f"no source: {(directory / item).relative_to(FW)}")


def main():
    platform = sys.argv[1] if len(sys.argv) > 1 else "cf2"
    out_dir = ROOT / "analysis" / "config" / platform
    cfg = load_config(out_dir / ".config")

    files, unresolved = [], []
    for top in ("src", "vendor", "app_api"):
        if (FW / top).is_dir():
            walk(FW / top, cfg, files, unresolved)

    rel = sorted({f.relative_to(FW).as_posix() for f in files})
    (out_dir / "filelist.txt").write_text("\n".join(rel) + "\n")

    all_src = {p.relative_to(FW).as_posix() for p in (FW / "src").rglob("*.c")}
    excluded = sorted(all_src - set(rel))
    (out_dir / "excluded.txt").write_text("\n".join(excluded) + "\n")

    print(f"{platform}: {len(rel)} compiled, {len(excluded)} src/*.c not compiled")
    for u in unresolved:
        print("  note:", u)


if __name__ == "__main__":
    main()
