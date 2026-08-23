"""Assemble the self-contained runtime inside dist/Shivakshi/runtime.

Copies Python, Node, the mdtopdf converter (with node_modules), and the
exact puppeteer Chromium build the engine needs, so Shivakshi works on any
Windows PC with zero installs. Run from the shivakshi folder.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

DST = Path("dist/Shivakshi/runtime")

SRC_PY = Path(r"C:\Python314")
SRC_NODE = Path(r"C:\Program Files\nodejs")
SRC_MDTOPDF = Path(r"G:\minakshi\mdtopdf")
SRC_PUPPETEER_CACHE = Path.home() / ".cache" / "puppeteer"
CHROME_VER = "win64-148.0.7778.97"

PY_SKIP = {
    "test", "tests", "__pycache__", "Doc", "Tools", "include",
    "share", "tcl", "Scripts", "Lib/test",
}


def _ignore_py(directory, names):
    base = Path(directory)
    if base.name == "Lib":
        return {"test", "__pycache__"}
    kept = set()
    for n in names:
        p = base / n
        if p.is_dir() and (p.name in PY_SKIP or p.name.startswith("test")):
            kept.add(n)
        elif p.is_file() and p.name.endswith(".pyc"):
            kept.add(n)
    return kept


def _ignore_mdtopdf(directory, names):
    kept = set()
    for n in names:
        low = n.lower()
        if low in (".git", ".markmap_cache", "node_modules/.cache"):
            kept.add(n)
        elif n.lower().endswith((".pdf", ".svg", ".pyc")):
            kept.add(n)
    return kept


def _force_clear(path: Path) -> None:
    if not path.exists():
        return
    for f in path.rglob("*"):
        if f.is_file():
            try:
                f.chmod(f.stat().st_mode | 0o200)
            except Exception:
                pass
    shutil.rmtree(path, ignore_errors=True)


def copytree(src: Path, dst: Path, ignore=None) -> None:
    _force_clear(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"copying {src.name} ...")
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True,
                    ignore_dangling_symlinks=True)


def main() -> None:
    if not (SRC_PY / "python.exe").is_file():
        sys.exit(f"python not found at {SRC_PY}")
    if not (SRC_NODE / "node.exe").is_file():
        sys.exit(f"node not found at {SRC_NODE}")
    if not (SRC_MDTOPDF / "markmap_to_pdf.py").is_file():
        sys.exit(f"converter not found at {SRC_MDTOPDF}")
    chrome_src = SRC_PUPPETEER_CACHE / "chrome" / CHROME_VER
    if not (chrome_src / "chrome-win64" / "chrome.exe").is_file():
        sys.exit(f"chromium not found at {chrome_src}")

    copytree(SRC_PY, DST / "python", ignore=_ignore_py)
    copytree(SRC_NODE, DST / "node")
    copytree(SRC_MDTOPDF, DST / "mdtopdf", ignore=_ignore_mdtopdf)
    copytree(chrome_src, DST / "puppeteer_cache" / "chrome" / CHROME_VER)

    size = sum(f.stat().st_size for f in DST.rglob("*") if f.is_file())
    print(f"runtime ready at {DST}  ({size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()