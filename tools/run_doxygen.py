"""Run Doxygen over the files one platform compiles.

Inputs : analysis/config/<platform>/{filelist.txt,predefined.txt}
         (run gen_config.py and gen_filelist.py first)
Outputs: analysis/doxygen/<platform>/Doxyfile
         analysis/doxygen/<platform>/html/index.html  (browse: call/caller graphs)
         analysis/doxygen/<platform>/xml/             (for scripted extraction)

Vendor code (CMSIS, FreeRTOS, libdw1000) is on the include path but is not
documented itself: calls into it show up as external references.

Usage: python tools/run_doxygen.py [platform]   (default: cf2)
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "crazyflie-firmware"
DOT_PATH = Path(r"C:\Program Files\Graphviz\bin")

# Makefile ARCH_CFLAGS defines that affect #if evaluation
ARCH_DEFINES = [
    "STM32F4XX", "STM32F40_41xxx", "HSE_VALUE=8000000",
    "USE_STDPERIPH_DRIVER", "ARM_MATH_CM4", "__FPU_PRESENT=1",
]
# GCC extensions the Doxygen C parser mistakes for function definitions
# (e.g. NO_DMA_CCM_SAFE_ZERO_INIT -> __attribute__((section(".ccmbss"))))
PARSER_DEFINES = ["__attribute__(x)=", "__asm__(x)=", "__asm(x)=",
                  # static allocation macros swallow the function that follows them
                  "STATIC_MEM_QUEUE_ALLOC(a,b,c)=",
                  "STATIC_MEM_TASK_ALLOC(a,b)=",
                  "STATIC_MEM_TASK_ALLOC_STACK_NO_DMA_CCM_SAFE(a,b)="]


def quote(p):
    return '"' + str(p).replace("\\", "/") + '"'


def main():
    platform = sys.argv[1] if len(sys.argv) > 1 else "cf2"
    cfg_dir = ROOT / "analysis" / "config" / platform
    out_dir = ROOT / "analysis" / "doxygen" / platform
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        FW / f for f in (cfg_dir / "filelist.txt").read_text().split()
        if not f.startswith("vendor/")
    ]
    headers = sorted({h for d in (FW / "src").rglob("interface") if d.is_dir()
                      for h in d.rglob("*.h")})
    include_dirs = sorted({h.parent for h in headers}) + [
        FW / "src" / "config",
        FW / "vendor" / "FreeRTOS" / "include",
        FW / "vendor" / "CMSIS" / "CMSIS" / "Core" / "Include",
        FW / "vendor" / "CMSIS" / "CMSIS" / "DSP" / "Include",
        FW / "vendor" / "libdw1000" / "inc",
    ]
    predefined = (cfg_dir / "predefined.txt").read_text().split("\n")
    predefined = [p for p in predefined if p] + ARCH_DEFINES + PARSER_DEFINES

    settings = {
        "PROJECT_NAME": f'"crazyflie-firmware ({platform})"',
        "OUTPUT_DIRECTORY": quote(out_dir),
        "STRIP_FROM_PATH": quote(FW),
        "INPUT": " \\\n    ".join(quote(p) for p in sources + headers),
        "FILE_PATTERNS": "*.c *.h",
        "INPUT_FILTER": quote(f"{sys.executable} {ROOT / 'tools' / 'doxy_filter.py'}"),
        "FILTER_SOURCE_FILES": "YES",
        "INCLUDE_PATH": " \\\n    ".join(quote(p) for p in include_dirs),
        "PREDEFINED": " \\\n    ".join(
            '"' + p.replace('"', '\\"') + '"' for p in predefined),
        "OPTIMIZE_OUTPUT_FOR_C": "YES",
        "EXTRACT_ALL": "YES",
        "EXTRACT_STATIC": "YES",
        "EXTRACT_LOCAL_CLASSES": "YES",
        "SOURCE_BROWSER": "YES",
        "INLINE_SOURCES": "NO",
        "REFERENCED_BY_RELATION": "YES",
        "REFERENCES_RELATION": "YES",
        "ENABLE_PREPROCESSING": "YES",
        "MACRO_EXPANSION": "YES",
        "SEARCH_INCLUDES": "YES",
        "SKIP_FUNCTION_MACROS": "NO",
        "GENERATE_HTML": "YES",
        "GENERATE_XML": "YES",
        "XML_PROGRAMLISTING": "NO",
        "GENERATE_LATEX": "NO",
        "HAVE_DOT": "YES",
        "DOT_PATH": quote(DOT_PATH),
        "DOT_IMAGE_FORMAT": "svg",
        "INTERACTIVE_SVG": "YES",
        "CALL_GRAPH": "YES",
        "CALLER_GRAPH": "YES",
        "INCLUDE_GRAPH": "YES",
        "INCLUDED_BY_GRAPH": "YES",
        "DIRECTORY_GRAPH": "YES",
        "DOT_GRAPH_MAX_NODES": "100",
        "MAX_DOT_GRAPH_DEPTH": "3",
        "DOT_NUM_THREADS": "0",
        "NUM_PROC_THREADS": "0",
        "QUIET": "YES",
        "WARNINGS": "NO",
        "WARN_LOGFILE": quote(out_dir / "warnings.log"),
    }
    doxyfile = out_dir / "Doxyfile"
    doxyfile.write_text("".join(f"{k} = {v}\n" for k, v in settings.items()))

    for sub in ("html", "xml"):
        shutil.rmtree(out_dir / sub, ignore_errors=True)
    print(f"doxygen: {len(sources)} sources, {len(headers)} headers ...")
    subprocess.run(["doxygen", str(doxyfile)], check=True)
    print(f"done -> {out_dir / 'html' / 'index.html'}")


if __name__ == "__main__":
    main()
