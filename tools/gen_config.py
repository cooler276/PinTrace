"""Resolve the firmware Kconfig for one platform without the ARM toolchain.

Outputs (under analysis/config/<platform>/):
  .config          resolved Kconfig values
  autoconf.h       C header, same as Kbuild's include/generated/autoconf.h
  predefined.txt   Doxygen PREDEFINED list (one "NAME=VALUE" per line)

Usage: python tools/gen_config.py [platform]   (default: cf2)
"""
import os
import sys
from pathlib import Path

import kconfiglib

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "crazyflie-firmware"


def main():
    platform = sys.argv[1] if len(sys.argv) > 1 else "cf2"
    defconfig = FW / "configs" / f"{platform}_defconfig"
    out = ROOT / "analysis" / "config" / platform
    out.mkdir(parents=True, exist_ok=True)

    os.environ["srctree"] = str(FW)
    os.chdir(FW)  # Kconfig "source" paths are relative to the firmware root
    kconf = kconfiglib.Kconfig("Kconfig", warn_to_stderr=False)
    kconf.load_config(str(defconfig))
    kconf.write_config(str(out / ".config"))
    kconf.write_autoconf(str(out / "autoconf.h"))

    lines = []
    for line in (out / "autoconf.h").read_text().splitlines():
        if line.startswith("#define "):
            _, name, value = line.split(" ", 2)
            lines.append(f"{name}={value}")
    (out / "predefined.txt").write_text("\n".join(lines) + "\n")
    print(f"{platform}: {len(lines)} config symbols -> {out}")


if __name__ == "__main__":
    main()
