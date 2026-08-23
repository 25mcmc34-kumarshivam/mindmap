# markmap-pdf · Shivakshi

Turn any **Markdown** file into a complete, beautifully laid-out **mind map PDF** —
rendered with [Markmap](https://markmap.js.org/) in headless Chromium, kept fully
**vector**, and paginated to the exact size of the map. No cropping, no manual
layout, no image blur.

Includes **Shivakshi** — a drag-and-drop Windows desktop app for the same engine,
so you never need a terminal.

![Pipeline](https://img.shields.io/badge/Markdown-%E2%9E%94%20PDF-8b5cf6)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What it does

```
Markdown file
      │
      ▼
 markmap-lib  ──►  markmap-view + d3  ──►  headless Chromium
      │                                              │
      │                     complete SVG (native <text>,
      │                     nothing cropped)          │
      ▼                                              ▼
            print-to-PDF  (vector, auto-size)   ===>  mindmap.pdf
```

Two layouts:

- **`markmap`** (default) — the classic right-growing Markmap tree, with roomy
  spacing between every branch.
- **`butterfly`** — a topic-centred design: the root sits in the middle, major
  sections fan out as pastel rounded cards in four quadrants, details hang below
  in plain text.

## Features

- Complete vector map on one auto-sized page — zoom in as deep as you like, it
  never pixelates (`--zoom 4` / `--zoom 10` for a larger canvas).
- Optional **SVG export** with text converted to native `<text>` so it opens
  correctly in any browser/editor (`--svg`).
- Roomier-by-default branch spacing (`--spacing-vertical`, `--spacing-horizontal`).
- Reads from a file or **stdin** (`cat notes.md | markmap_to_pdf.py -`).
- Fallback PDF engines (`chrome`, `cairosvg`, `svglib`, `raster`) when Chromium
  is unavailable.
- **Shivakshi** GUI: drag & drop up to 10 files, choose Simple / 2× / 4× zoom,
  pick a save folder, convert with one click.

## Requirements

- **Python 3.10+**
- **Node.js 18+** (for the Markmap renderer; the script installs its own
  `node_modules` and Chromium on first run — or you can install it yourself:
  `npm install`)

## Installation

```bash
# 1. Python side (optional; only needed for fallback engines / page fitting)
pip install -r requirements.txt

# 2. Node side (the default pipeline)
npm install        # fetches markmap-lib, markmap-view, d3, puppeteer
```

On first render, `markmap_to_pdf.py` downloads headless Chromium if needed
(disable with `--no-install`, run fully offline with `--no-assets`).

## Quick start (CLI)

```bash
python markmap_to_pdf.py notes.md
python markmap_to_pdf.py notes.md --zoom 4            # bigger, deeper-zoomable page
python markmap_to_pdf.py notes.md --svg               # also save the SVG
python markmap_to_pdf.py notes.md --output mymap.pdf
python markmap_to_pdf.py notes.md --layout butterfly  # centred butterfly design
cat notes.md | python markmap_to_pdf.py -
```

### Options

| Option | Meaning |
| --- | --- |
| `input` | Markdown file to convert, or `-` for stdin |
| `--output, -o` | PDF output path (default: `<input>.pdf`) |
| `--svg` | also export the complete SVG |
| `--svg-output` | SVG output path (implies `--svg`) |
| `--svg-mode` | `portable` (native `<text>`, default) or `native` (raw markmap SVG) |
| `--scale` | raster-fallback resolution multiplier (default: 4) |
| `--zoom` | enlarge the vector page by a factor, e.g. 4 or 10 (default: 1) |
| `--padding` | padding around the map, in SVG units (default: 40) |
| `--page` | `auto` (map's own size, default) or `a4` (fit on A4) |
| `--engine` | `auto` (default), `chrome`, `cairosvg`, `svglib`, `raster` |
| `--layout` | `markmap` (default) or `butterfly` |
| `--max-width` | wrap node text wider than N px (0 = never wrap) |
| `--spacing-vertical` | vertical gap between branches in px (default: 28, roomy) |
| `--spacing-horizontal` | horizontal gap between levels in px (default: 80) |
| `--background` | page background colour (default: `#ffffff`) |
| `--timeout` | rendering timeout in seconds (default: 300) |
| `--no-assets` | skip KaTeX / highlight.js downloads (fully offline) |
| `--no-install` | never run `npm install` automatically |
| `--open` | open the PDF when ready |
| `--quiet, -q` | only report errors |
| `--version` | print version |

## Shivakshi — desktop GUI

`shivakshi.pyw` is a small **CustomTkinter** app that wraps the same engine with a
clean, dark interface:

- Drag & drop **or** browse to add Markdown files (up to 10).
- Per-file output names (default = same as the input).
- Output type per batch: **Simple PDF**, **2× Zoom**, **4× Zoom**.
- "Apply to all files" switch, or a per-file dropdown.
- Spacing presets: Compact / Normal / Roomy.
- Save folder remembered between sessions (defaults to Downloads).
- Optional SVG export and auto-open.

```bash
pip install customtkinter tkinterdnd2
python shivakshi.pyw
```

### Building Shivakshi.exe

```bash
pip install pyinstaller
python -m PyInstaller --noconsole --name Shivakshi --clean -y \
    --collect-data customtkinter --collect-data tkinterdnd2 \
    --icon icon.ico shivakshi.pyw
```

The exe auto-detects `markmap_to_pdf.py` next to it (or one folder up) and uses
your installed Node/Chromium. For a **fully self-contained portable build** that
needs zero installs on any Windows PC, run `build_portable.py` (bundles Python,
Node, the converter and Chromium into `dist/Shivakshi/runtime`).

## Try it

A tiny sample is included — convert it right after install:

```bash
python markmap_to_pdf.py sample.md --svg --open
```

## License

[MIT](LICENSE)