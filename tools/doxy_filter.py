"""Doxygen INPUT_FILTER: neutralise the Bitcraze ASCII-art license banner.

Many files start with a "/**" banner whose line
    * | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
ends in a backslash; Doxygen then swallows every declaration in the file.
The banner is license text, not API documentation, so turn its opening
"/**" into a plain "/* " comment. Line numbers are preserved.

Usage (called by Doxygen): python tools/doxy_filter.py <file>
"""
import sys


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        text = f.read()
    head = text[:600]
    start = head.find("/**")
    if start != -1 and head[:start].strip() == "" and "0xBC" in head:
        text = text[:start] + "/* " + text[start + 3:]
    sys.stdout.reconfigure(encoding="utf-8", newline="")
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
