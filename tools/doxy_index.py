"""Query the Doxygen XML (analysis/doxygen/<platform>/xml) for functions.

  python tools/doxy_index.py enclosing <file> <line> [...]   # function containing a line
  python tools/doxy_index.py callers <func> [...]            # who calls func (referencedby)
  python tools/doxy_index.py callees <func> [...]            # what func calls (references)
  python tools/doxy_index.py chain <func> [--depth N]        # caller chain upward (default 6)

Options: --platform cf2

Function names match by exact name; static functions with the same name in
different files are listed separately as name@file.
Note: calls through function pointers are NOT visible here.
"""
import argparse
import collections
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=None)
def load(platform):
    xml_dir = ROOT / "analysis" / "doxygen" / platform / "xml"
    funcs = {}  # id -> dict
    canon = {}  # (name, file, line) -> id: the same body can appear under two ids
    alias = {}  # duplicate id -> canonical id
    # functions declared in a header are emitted in the header's XML
    # (with bodyfile pointing at the .c), so read both
    for f in list(xml_dir.glob("*_8c.xml")) + list(xml_dir.glob("*_8h.xml")):
        for md in ET.parse(f).getroot().iter("memberdef"):
            fid = md.get("id")
            if md.get("kind") != "function" or fid in funcs or fid in alias:
                continue
            loc = md.find("location")
            if loc is None or loc.get("bodystart") is None:
                continue
            key = (md.findtext("name"), loc.get("bodyfile"), loc.get("bodystart"))
            refs = [r.get("refid") for r in md.findall("references")]
            by = [r.get("refid") for r in md.findall("referencedby")]
            if key in canon:
                alias[fid] = canon[key]
                funcs[canon[key]]["refs"] += refs
                funcs[canon[key]]["by"] += by
                continue
            canon[key] = fid
            funcs[fid] = {
                "name": md.findtext("name"),
                "file": loc.get("bodyfile") or loc.get("file"),
                "start": int(loc.get("bodystart")),
                "end": int(loc.get("bodyend") or loc.get("bodystart")),
                "refs": refs,
                "by": by,
            }
    for fn in funcs.values():
        for k in ("refs", "by"):
            fn[k] = list(dict.fromkeys(alias.get(r, r) for r in fn[k]))
    by_name = collections.defaultdict(list)
    for fid, fn in funcs.items():
        by_name[fn["name"]].append(fid)
    return funcs, by_name


def label(fn):
    return f"{fn['name']}  ({fn['file']}:{fn['start']})"


def resolve(platform, name):
    funcs, by_name = load(platform)
    name, _, file_hint = name.partition("@")
    ids = by_name.get(name, [])
    if file_hint:
        ids = [i for i in ids if file_hint in funcs[i]["file"]]
    return ids


def cmd_enclosing(platform, args):
    funcs, _ = load(platform)
    for file, line in zip(args[0::2], args[1::2]):
        line = int(line)
        hits = [fn for fn in funcs.values()
                if fn["file"].endswith(file.replace("\\", "/")) and fn["start"] <= line <= fn["end"]]
        print(f"{file}:{line} -> " + (", ".join(label(h) for h in hits) or "(none)"))


def cmd_rel(platform, names, key):
    funcs, _ = load(platform)
    for name in names:
        for fid in resolve(platform, name):
            print(label(funcs[fid]))
            for rid in funcs[fid][key]:
                if rid in funcs:
                    print("   ", label(funcs[rid]))
        print()


def cmd_chain(platform, name, depth):
    funcs, _ = load(platform)

    def walk(fid, level, seen):
        print("  " * level + label(funcs[fid]))
        if level >= depth:
            return
        for rid in funcs[fid]["by"]:
            if rid in funcs and rid not in seen:
                walk(rid, level + 1, seen | {rid})

    for fid in resolve(platform, name):
        walk(fid, 0, {fid})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["enclosing", "callers", "callees", "chain"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--platform", default="cf2")
    ap.add_argument("--depth", type=int, default=6)
    a = ap.parse_args()
    if a.cmd == "enclosing":
        cmd_enclosing(a.platform, a.args)
    elif a.cmd == "callers":
        cmd_rel(a.platform, a.args, "by")
    elif a.cmd == "callees":
        cmd_rel(a.platform, a.args, "refs")
    else:
        for n in a.args:
            cmd_chain(a.platform, n, a.depth)


if __name__ == "__main__":
    main()
