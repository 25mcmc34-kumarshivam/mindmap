"""Shivakshi - Markdown mind-map PDF converter.

A simple Windows desktop front-end for markmap_to_pdf.py.
Drag & drop or browse up to 10 Markdown files, pick an output style,
and generate beautiful mind-map PDFs -- no terminal required.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) \
    else Path(__file__).resolve().parent
RUNTIME = APP_DIR / "runtime"
APP_NAME = "Shivakshi"
MAX_FILES = 10


def config_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    d = Path(base) / "Shivakshi"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        return APP_DIR / "shivakshi_config.json"
    return d / "config.json"

FORMATS = ["Simple PDF", "2x Zoom PDF", "4x Zoom PDF"]
ZOOM_BY_FORMAT = {"Simple PDF": None, "2x Zoom PDF": 2, "4x Zoom PDF": 4}
SPACING_MODES = ["Compact", "Normal", "Roomy"]
SPACING_VALUES = {"Compact": "16", "Normal": None, "Roomy": "42"}

ACCENT = "#8b5cf6"
ACCENT_HOVER = "#7a4df0"
CARD = "#1c1926"
CARD_2 = "#241f31"
FG_DIM = "#9a94ab"

try:
    import customtkinter as ctk
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    err = APP_DIR / "shivakshi_error.txt"
    err.write_text(
        "Missing UI packages.\nRun:\n    pip install customtkinter tkinterdnd2\n",
        encoding="utf-8",
    )
    try:
        _r = __import__("tkinter").Tk()
        _r.withdraw()
        messagebox.showerror(APP_NAME, f"Missing packages.\n\nSee {err}")
    except Exception:
        pass
    sys.exit(1)


def load_config() -> dict:
    try:
        import json
        return json.loads(config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    import json
    try:
        config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass


def default_save_dir() -> str:
    d = Path.home() / "Downloads"
    return str(d if d.is_dir() else Path.home())


def find_engine(cfg: dict):
    cand = cfg.get("engine")
    if cand and Path(cand).is_file():
        return Path(cand)
    bundled = RUNTIME / "mdtopdf" / "markmap_to_pdf.py"
    if bundled.is_file():
        return bundled
    probing = [Path(APP_DIR)]
    for _ in range(3):
        probing.append(probing[-1].parent)
    for base in probing:
        for sub in ("markmap_to_pdf.py", "mdtopdf/markmap_to_pdf.py",
                    "minakshi/mdtopdf/markmap_to_pdf.py"):
            p = base / sub
            if p.is_file():
                return p
    for extra in (
        Path.home() / "minakshi" / "mdtopdf" / "markmap_to_pdf.py",
        Path("G:/minakshi/mdtopdf/markmap_to_pdf.py"),
        Path("G:/mdtopdf/markmap_to_pdf.py"),
        Path("C:/minakshi/mdtopdf/markmap_to_pdf.py"),
        Path("D:/minakshi/mdtopdf/markmap_to_pdf.py"),
    ):
        if extra.is_file():
            return extra
    return None


def clean_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]+', "_", name).strip().strip(".")
    return name or "mindmap"


def python_executable() -> str:
    if getattr(sys, "frozen", False):
        bundled = RUNTIME / "python" / "python.exe"
        if bundled.is_file():
            return str(bundled)
        for cand in ("python", "python3", "py"):
            p = shutil.which(cand)
            if p:
                return p
        raise RuntimeError("Python not found on PATH. Please install Python.")
    return sys.executable


def build_command(job: dict) -> list[str]:
    cmd = [
        python_executable(),
        str(job["engine"]),
        str(job["md"]),
        "--output",
        str(job["pdf_out"]),
        "--quiet",
    ]
    if job.get("zoom"):
        cmd += ["--zoom", str(job["zoom"])]
    if job.get("svg_out"):
        cmd += ["--svg", "--svg-output", str(job["svg_out"])]
    if job.get("spacing_v"):
        cmd += ["--spacing-vertical", job["spacing_v"]]
    return cmd


def run_job(job: dict) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            build_command(job),
            cwd=str(Path(job["engine"]).parent),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=1200,
        )
    except subprocess.TimeoutExpired:
        return False, "timed out after 20 minutes"
    except Exception as exc:
        return False, str(exc)
    if proc.returncode != 0 or not Path(job["pdf_out"]).is_file():
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-4:]
        detail = "\n".join(tail) if tail else f"exit code {proc.returncode}"
        return False, detail
    ok_msg = str(job["pdf_out"].name)
    if job.get("svg_out") and Path(job["svg_out"]).is_file():
        ok_msg += f"  (+ {Path(job['svg_out']).name})"
    return True, ok_msg


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        cfg = load_config()
        self.cfg = cfg
        self.engine = find_engine(cfg)
        if self.engine:
            cfg["engine"] = str(self.engine)
            save_config(cfg)
        self.files: list[dict] = []
        self.running = False

        self.save_dir = ctk.StringVar(value=cfg.get("save_dir") or default_save_dir())
        self.same_for_all = ctk.BooleanVar(value=True)
        self.fmt_var = ctk.StringVar(value=cfg.get("fmt") or "Simple PDF")
        self.spacing_var = ctk.StringVar(value=cfg.get("spacing") or "Normal")
        self.svg_var = ctk.BooleanVar(value=bool(cfg.get("export_svg")))
        self.open_var = ctk.BooleanVar(value=bool(cfg.get("open_after")))

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(APP_NAME)
        self.geometry("920x800")
        self.minsize(860, 700)
        self.configure(fg_color="#12101a")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.drop_target_register(DND_FILES)
        self.bind("<<Drop>>", self.on_drop)

        self.build_header()
        self.build_dropzone()
        self.build_file_list()
        self.build_settings()
        self.build_actions()

        if not self.engine:
            self.after(400, self.locate_engine)

    # ---------- UI sections ----------

    def build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=28, pady=(20, 4))
        ctk.CTkLabel(
            top,
            text="SHIVAKSHI",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left")
        ctk.CTkLabel(
            top,
            text="Markdown  →  Mind-map PDF",
            font=ctk.CTkFont(size=13),
            text_color=FG_DIM,
        ).pack(side="left", padx=14, pady=(12, 0))
        self.engine_lbl = ctk.CTkLabel(
            top,
            text=self.engine_status_text(),
            font=ctk.CTkFont(size=11),
            text_color="#7ee787" if self.engine else "#ff7b72",
        )
        self.engine_lbl.pack(side="right", pady=(12, 0))

    def engine_status_text(self) -> str:
        return f"engine ✔ {self.engine.name}" if self.engine else "converter not found ✖"

    def build_dropzone(self):
        zone = ctk.CTkFrame(
            self,
            fg_color=CARD,
            border_width=2,
            border_color=ACCENT,
            corner_radius=16,
        )
        zone.pack(fill="x", padx=28, pady=(10, 6))
        inner = ctk.CTkFrame(zone, fg_color="transparent")
        inner.pack(pady=22)
        ctk.CTkLabel(
            inner,
            text="⇩  Drag & drop .md files here   (max 10)",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack()
        ctk.CTkLabel(
            inner, text="or", font=ctk.CTkFont(size=12), text_color=FG_DIM
        ).pack(pady=4)
        ctk.CTkButton(
            inner,
            text="＋  Add Files",
            width=170,
            height=36,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.add_files_dialog,
        ).pack()
        for w in (zone, inner):
            w.drop_target_register(DND_FILES)
            w.bind("<<Drop>>", self.on_drop)

    def build_file_list(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(6, 0))
        self.count_lbl = ctk.CTkLabel(
            head,
            text="Files  0/10",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.count_lbl.pack(side="left")
        self.clear_btn = ctk.CTkButton(
            head,
            text="Clear all",
            width=90,
            height=26,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color="#443e56",
            hover_color=CARD_2,
            text_color=FG_DIM,
            command=self.clear_files,
        )
        self.clear_btn.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self, height=190, fg_color=CARD, corner_radius=14
        )
        self.list_frame.pack(fill="x", padx=28, pady=6)
        self.empty_lbl = ctk.CTkLabel(
            self.list_frame,
            text="No files yet — drop some above ☝",
            text_color=FG_DIM,
            font=ctk.CTkFont(size=13),
        )
        self.empty_lbl.pack(pady=30)

    def build_settings(self):
        s = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        s.pack(fill="both", expand=True, padx=28, pady=6)

        row1 = ctk.CTkFrame(s, fg_color="transparent")
        row1.pack(fill="x", padx=18, pady=(14, 2))
        ctk.CTkLabel(row1, text="Save to:", font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkEntry(
            row1, textvariable=self.save_dir, width=430, height=30, corner_radius=8
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            row1,
            text="Browse…",
            width=92,
            height=30,
            corner_radius=8,
            fg_color=CARD_2,
            hover_color="#2f2940",
            command=self.choose_dir,
        ).pack(side="left")

        row2 = ctk.CTkFrame(s, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=(8, 2))
        ctk.CTkSwitch(
            row2,
            text="Apply these settings to ALL files",
            variable=self.same_for_all,
            command=self.rebuild_rows,
            progress_color=ACCENT,
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        row3 = ctk.CTkFrame(s, fg_color="transparent")
        row3.pack(fill="x", padx=18, pady=(6, 2))
        ctk.CTkLabel(
            row3, text="Output type:", font=ctk.CTkFont(size=13)
        ).pack(side="left")
        for f in FORMATS:
            ctk.CTkRadioButton(
                row3,
                text=f,
                value=f,
                variable=self.fmt_var,
                command=self.sync_fmt_to_all,
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER,
                font=ctk.CTkFont(size=13),
            ).pack(side="left", padx=(14, 0))

        row4 = ctk.CTkFrame(s, fg_color="transparent")
        row4.pack(fill="x", padx=18, pady=(6, 2))
        ctk.CTkLabel(row4, text="Spacing:", font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkOptionMenu(
            row4,
            values=SPACING_MODES,
            variable=self.spacing_var,
            width=110,
            height=28,
            fg_color=CARD_2,
            button_color="#372f4d",
            button_hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 24))
        ctk.CTkCheckBox(
            row4,
            text="Also export SVG",
            variable=self.svg_var,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13),
        ).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(
            row4,
            text="Open PDF when done",
            variable=self.open_var,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

    def build_actions(self):
        a = ctk.CTkFrame(self, fg_color="transparent")
        a.pack(fill="x", padx=28, pady=(8, 2))
        self.convert_btn = ctk.CTkButton(
            a,
            text="▶   Convert",
            width=220,
            height=46,
            corner_radius=12,
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.start_convert,
        )
        self.convert_btn.pack(side="left")

        self.progress = ctk.CTkProgressBar(
            a, height=10, corner_radius=6, progress_color=ACCENT, fg_color=CARD_2
        )
        self.progress.set(0)
        self.progress.pack(side="left", fill="x", expand=True, padx=(18, 0))

        log_wrap = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        log_wrap.pack(fill="both", expand=False, padx=28, pady=(6, 16))
        self.log_tb = ctk.CTkTextbox(
            log_wrap,
            height=110,
            fg_color="#161320",
            text_color="#c9c4d8",
            font=ctk.CTkFont(size=12, family="Consolas"),
        )
        self.log_tb.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_tb.tag_config("ok", foreground="#7ee787")
        self.log_tb.tag_config("bad", foreground="#ff7b72")
        self.log_tb.tag_config("dim", foreground=FG_DIM)
        self.log_tb.insert("end", "Ready.\n", "dim")
        self.log_tb.configure(state="disabled")

    # ---------- file list ----------

    def add_files(self, paths) -> None:
        if self.running:
            return
        added = skipped = 0
        for p in paths:
            p = Path(p)
            if len(self.files) >= MAX_FILES:
                skipped += 1
                continue
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".md", ".markdown"):
                skipped += 1
                continue
            if any(f["path"] == p for f in self.files):
                continue
            stem = clean_name(p.stem)
            self.files.append(
                {"path": p, "out": ctk.StringVar(value=stem + ".pdf"), "fmt": self.fmt_var.get()}
            )
            added += 1
        self.rebuild_rows()
        if skipped:
            self.log(
                f"{skipped} file(s) skipped (limit {MAX_FILES}, duplicates, "
                "or not .md)",
                "dim",
            )

    def add_files_dialog(self) -> None:
        paths = filedialog.askopenfilenames(
            parent=self,
            title="Choose Markdown files",
            filetypes=[("Markdown", "*.md *.markdown"), ("All files", "*.*")],
        )
        self.add_files(paths)

    def on_drop(self, event) -> None:
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        self.add_files(paths)

    def clear_files(self) -> None:
        if self.running:
            return
        self.files.clear()
        self.rebuild_rows()

    def remove_row(self, idx: int) -> None:
        if self.running:
            return
        del self.files[idx]
        self.rebuild_rows()

    def rebuild_rows(self) -> None:
        for w in self.list_frame.winfo_children():
            w.destroy()
        same = self.same_for_all.get()
        for i, item in enumerate(self.files):
            row = ctk.CTkFrame(self.list_frame, fg_color=CARD_2, corner_radius=10)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(
                row,
                text=f"{i+1}",
                width=26,
                text_color=ACCENT,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(side="left", padx=(10, 2))
            name = item["path"].name
            shown = name if len(name) <= 34 else name[:16] + "…" + name[-14:]
            ctk.CTkLabel(
                row, text=shown, width=250, anchor="w", font=ctk.CTkFont(size=12)
            ).pack(side="left")
            ctk.CTkLabel(row, text="→ save as", text_color=FG_DIM).pack(side="left", padx=6)
            ctk.CTkEntry(
                row,
                textvariable=item["out"],
                width=210,
                height=27,
                corner_radius=8,
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 10))
            if not same:
                combo = ctk.CTkOptionMenu(
                    row,
                    values=FORMATS,
                    width=118,
                    height=27,
                    fg_color="#372f4d",
                    button_color="#453b60",
                    button_hover_color=ACCENT_HOVER,
                    font=ctk.CTkFont(size=12),
                    command=lambda v, it=item: it.__setitem__("fmt", v),
                )
                combo.set(item.get("fmt", self.fmt_var.get()))
                combo.pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                row,
                text="✕",
                width=30,
                height=27,
                corner_radius=8,
                fg_color="transparent",
                border_width=1,
                border_color="#443e56",
                hover_color="#3a2530",
                text_color="#ff7b72",
                command=lambda ix=i: self.remove_row(ix),
            ).pack(side="right", padx=8)
        n = len(self.files)
        self.count_lbl.configure(text=f"Files  {n}/{MAX_FILES}")
        if n == 0:
            self.empty_lbl = ctk.CTkLabel(
                self.list_frame,
                text="No files yet — drop some above ☝",
                text_color=FG_DIM,
                font=ctk.CTkFont(size=13),
            )
            self.empty_lbl.pack(pady=30)

    # ---------- settings actions ----------

    def choose_dir(self) -> None:
        d = filedialog.askdirectory(parent=self, initialdir=self.save_dir.get())
        if d:
            self.save_dir.set(d.replace("/", "\\"))

    def sync_fmt_to_all(self) -> None:
        if self.same_for_all.get():
            for item in self.files:
                item["fmt"] = self.fmt_var.get()

    def locate_engine(self) -> None:
        messagebox.showinfo(
            APP_NAME,
            "Converter 'markmap_to_pdf.py' was not found automatically.\n"
            "Please locate it (it lives in your mdtopdf folder).",
        )
        p = filedialog.askopenfilename(
            parent=self,
            title="Select markmap_to_pdf.py",
            filetypes=[("Python", "*.py")],
        )
        if p and Path(p).name == "markmap_to_pdf.py":
            self.engine = Path(p)
            self.cfg["engine"] = str(self.engine)
            self.engine_lbl.configure(
                text=self.engine_status_text(), text_color="#7ee787"
            )
        elif not self.engine:
            self.engine_lbl.configure(text="converter not found ✖", text_color="#ff7b72")

    # ---------- conversion ----------

    def start_convert(self) -> None:
        if self.running:
            return
        if not self.engine or not Path(self.engine).is_file():
            messagebox.showerror(APP_NAME, "Converter script not found.")
            return
        if not self.files:
            messagebox.showwarning(APP_NAME, "Add at least one .md file first.")
            return
        out_dir = Path(self.save_dir.get())
        if not out_dir.is_dir():
            messagebox.showerror(APP_NAME, f"Save folder does not exist:\n{out_dir}")
            return

        if getattr(sys, "frozen", False):
            node_dir = RUNTIME / "node"
            if node_dir.is_dir():
                os.environ["PATH"] = str(node_dir) + os.pathsep + os.environ.get("PATH", "")
            pcache = RUNTIME / "puppeteer_cache"
            if pcache.is_dir():
                os.environ["PUPPETEER_CACHE_DIR"] = str(pcache)

        jobs = []
        seen_names = set()
        for item in self.files:
            raw = clean_name(item["out"].get())
            if not raw.lower().endswith(".pdf"):
                raw += ".pdf"
            if raw.lower() in seen_names:
                base = raw[:-4]
                i = 2
                while f"{base}_{i}.pdf".lower() in seen_names:
                    i += 1
                raw = f"{base}_{i}.pdf"
            seen_names.add(raw.lower())
            fmt = self.fmt_var.get() if self.same_for_all.get() else item.get("fmt", self.fmt_var.get())
            svg_name = raw[:-4] + ".svg" if self.svg_var.get() else None
            jobs.append(
                {
                    "md": item["path"],
                    "pdf_out": out_dir / raw,
                    "svg_out": out_dir / svg_name if svg_name else None,
                    "zoom": ZOOM_BY_FORMAT[fmt],
                    "spacing_v": SPACING_VALUES[self.spacing_var.get()],
                    "engine": self.engine,
                }
            )

        self.running = True
        self.convert_btn.configure(state="disabled", text="Converting…")
        self.progress.set(0)
        self.log_set("")
        threading.Thread(target=self.worker, args=(jobs,), daemon=True).start()

    def worker(self, jobs: list[dict]) -> None:
        total = len(jobs)
        done_ok = 0
        failures = []
        for i, job in enumerate(jobs, 1):
            self.ui(
                lambda i=i, j=job: self.log(f"[{i}/{total}] {j['md'].name} … ", "dim")
            )
            ok, msg = run_job(job)
            if ok:
                done_ok += 1
                self.ui(lambda m=msg: self.log(f"done ✔  {m}\n", "ok"))
                if self.open_var.get():
                    try:
                        os.startfile(str(job["pdf_out"]))
                    except Exception:
                        pass
            else:
                failures.append((job["md"].name, msg))
                self.ui(lambda m=msg: self.log(f"FAILED ✖\n      {m}\n", "bad"))
            frac = i / total
            self.ui(lambda f=frac: self.progress.set(f))
        summary = f"All {done_ok}/{total} converted ✔"
        if failures:
            summary = f"{done_ok}/{total} succeeded; {len(failures)} failed ✖"
        self.ui(lambda: self.log(summary + "\n", "ok" if not failures else "bad"))
        self.ui(lambda: self.finish(summary, bool(failures)))

    def finish(self, summary: str, had_failures: bool) -> None:
        self.running = False
        self.convert_btn.configure(state="normal", text="▶   Convert")
        if had_failures:
            messagebox.showwarning(APP_NAME, summary)
        else:
            messagebox.showinfo(APP_NAME, f"{summary}\nSaved in:\n{self.save_dir.get()}")

    # ---------- helpers ----------

    def ui(self, fn) -> None:
        self.after(0, fn)

    def log_set(self, text: str) -> None:
        self.log_tb.configure(state="normal")
        self.log_tb.delete("1.0", "end")
        self.log_tb.insert("end", text)
        self.log_tb.configure(state="disabled")

    def log(self, text: str, tag: str | None = None) -> None:
        self.log_tb.configure(state="normal")
        self.log_tb.insert("end", text, tag or ())
        self.log_tb.see("end")
        self.log_tb.configure(state="disabled")

    def on_close(self) -> None:
        self.cfg.update(
            {
                "save_dir": self.save_dir.get(),
                "fmt": self.fmt_var.get(),
                "spacing": self.spacing_var.get(),
                "export_svg": bool(self.svg_var.get()),
                "open_after": bool(self.open_var.get()),
            }
        )
        save_config(self.cfg)
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
