#!/usr/bin/env python3
"""Manuscript pipeline for the AAAI-27 workshop note (standard library only).

    uv run python paper/build.py [--profile aaai|journal] [--numbers PATH] [--note PATH] [--build DIR] [--strict]
                                 fill|tex|pdf|all|zip

fill  paper/note.md + numbers JSON -> paper/build/note_filled.md, numbers_used.json, todos.json
tex   note_filled.md -> pandoc -> paper/build/paper.tex, paper/refs.bib, tables.json
pdf   paper.tex -> tectonic -> paper/build/paper.pdf (see PREVIEW NOTE below)
all   fill, tex, pdf
zip   (journal only) make_journal_zip: the upload folder and its zip, compiled alone in a fresh temp dir

PROFILES. --profile aaai (default) is the AAAI-27 workshop build described here. --profile journal is the
Applied Energy build (section JOURNAL PROFILE below): a self-contained elsarticle package in
paper/build_journal/ (or --build), its PDF for reading, the side files in paper/journal/ (title page, cover
letter, highlights, data availability, graphical abstract; with a non-default --build they go to <build>/journal/
instead, and paper/journal/ is left alone) and, with zip or all, paper/build_journal/upload/.

Result numbers: {{key}} prints "value [lo, hi]", {{key|v}} prints the value, {{key|i}} an integer count.
Two decimals, U+2212 for a negative sign in Markdown, $-$ in LaTeX.
[[LAYERS: ...]], [[E3-conditioned check result]] and [[R: ...]] stay visible as TODO boxes.
[[FIG: fig_setting]] on a line of its own places that figure (any id in FIGURES); a figure whose file is
missing shows a red TODO box. fig_layers and fig_e3 keep their automatic places unless marked.
--note and --build redirect the source note and the build folder (default paper/note.md, paper/build).
--strict fails if any TODO, missing figure, missing Table 2 or flagged reference remains.

PREVIEW NOTE. aaai2027.sty stops unless the engine is pdfTeX. Only tectonic (XeTeX) is
installed, so the pdf step compiles a copy of the kit in paper/build/preview/ with the single
line \\RequirePDFTeX commented out. The kit files in paper/kit/ and the submitted paper.tex
are untouched. Page breaks and fonts in the preview approximate the pdfTeX result.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parent
BUILD = PAPER / "build"
KIT = PAPER / "kit"
FIGS = PAPER / "figures"
NOTE = PAPER / "note.md"
DEFAULT_NUMBERS = Path(__file__).resolve().parent.parent / "results" / "paper_numbers.json"
# Post hoc descriptive numbers live in their own files beside the main file and are merged by key.
EXTRA_NUMBERS = ("posthoc_oblivious_share.json", "g2_numbers.json", "posthoc_g3_runs.json", "confirm_paper_numbers.json",
                 "posthoc_applied_energy.json", "posthoc_ranker.json", "posthoc_fla.json",
                 "diag_cellf_delay.json")
BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin"]

MINUS = "\u2212"
PH_RE = re.compile(r"ZZPH(\d+)ZZ")
NUM_REF_RE = re.compile(r"\{\{\s*([^{}|]+?)\s*(?:\|\s*(v|i)\s*)?\}\}")
TODO_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
CITE_RE = re.compile(r"\[([A-Za-z][A-Za-z0-9]*(?:;\s*[A-Za-z][A-Za-z0-9]*)*)\]")
COMMENT_OPEN, COMMENT_CLOSE = "<!--", "-->"

FIGURES = {
    "fig_setting": {
        "file": "fig_setting.pdf",
        "number": 1,
        "caption": "The setting: an operator sends setpoints $x_{it}$ in slot $t$ to participants who share a "
                   "feeder limit. Confirmations $y_{is}$ come back later. Delivered energy is confirmed "
                   "$\\delta$ slots after the setpoint; a stuck participant is seen only where a setpoint "
                   "could have delivered.",
    },
    "fig_window": {
        "file": "fig_window.pdf",
        "number": 2,
        "caption": "Correction by re-dispatch needs $s + \\delta \\le d_i - 1$ (Proposition 2). When the delay "
                   "reaches the remaining window, a failed setpoint can only be hedged in advance.",
    },
    "fig_ladder": {
        "file": "fig_ladder.pdf",
        "number": 4,
        "caption": "Belief by rule at the reference cell ($M = 3$, $\\delta = 2$, $\\rho = 0.95$). Arrows carry the "
                   "gain from one cell to the next in kWh per 100 participants per event with 95\\% paired "
                   "bootstrap intervals. Development seeds, post hoc.",
    },
    "fig_layers": {
        "file": "fig_layers.pdf",
        "number": 3,
        "caption": "Planning, hedging and targeting steps against delay $\\delta$, three prior events. "
                   "One panel per stress level $\\rho$. Mean gain in kWh per 100 participants per event "
                   "with paired bootstrap 95\\% intervals, 100 development seeds. Descriptive, post hoc.",
    },
    "fig_e3": {
        "file": "fig_e3.pdf",
        "number": 5,
        "caption": "Top: Proposition 1 gap against spare cap $c$. Bottom: Proposition 3 recovery against "
                   "prior events $M$ for pooled and per-pair caps. Simultaneous 95\\% intervals; "
                   "validation family, 100 development seeds; $K = 8$.",
    },
}
# A line of exactly "[[FIG: <id>]]" in note.md puts that figure there. Without a marker fig_layers goes
# after the [[LAYERS: ...]] line (or Table 2) and fig_e3 after the paragraph that cites "(Figure <number>)".
FIG_MARK_RE = re.compile(r"\[\[FIG:\s*([A-Za-z0-9_]+)\s*\]\]")


# A line of exactly "[[TABLE: gap]]" or "[[TABLE: factorial]]" places Table 1 or Table 2 there, so the tables do
# not depend on the wording of a prose sentence (the local writer rewrites every sentence). The older sentence
# anchors (GAP_ANCHORS, FACT_ANCHOR) still work when no marker is present.
TABLE_MARK_RE = re.compile(r"\[\[TABLE:\s*(gap|factorial|confirm)\s*\]\]")


def table_marker(line: str):
    """The table id of a marker line (a line that is exactly [[TABLE: gap|factorial]]), else None."""
    m = TABLE_MARK_RE.fullmatch(line.strip())
    return m.group(1) if m else None


def fig_marker(line: str):
    """The figure id of a marker line (a line that is exactly [[FIG: id]]), else None."""
    m = FIG_MARK_RE.fullmatch(line.strip())
    return m.group(1) if m else None


def die(msg: str, code: int = 1):
    print(f"build.py: error: {msg}", file=sys.stderr)
    sys.exit(code)


def tool(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    for d in BIN_DIRS:
        if (Path(d) / name).exists():
            return str(Path(d) / name)
    die(f"{name} not found")


# --------------------------------------------------------------------------- numbers

def load_numbers(path: Path) -> dict:
    if not path.exists():
        die(f"numbers file not found: {path}")
    d = json.loads(path.read_text(encoding="utf-8"))
    numbers = dict(d["numbers"])
    for name in EXTRA_NUMBERS:
        extra = path.parent / name
        if extra.exists():
            e = json.loads(extra.read_text(encoding="utf-8"))["numbers"]
            clash = set(e) & set(numbers)
            if clash:
                die("numbers key collision with " + name + ": " + ", ".join(sorted(clash)))
            numbers.update(e)
    return numbers


def fmt(x: float) -> str:
    """Two decimals, half away from zero, on the value snapped to 9 decimals; U+2212 for a negative; no sign
    on zero. The snap removes float noise, so a mean of 2.125 prints 2.13 whether it is stored as
    2.1249999999999996 or 2.125 (2026-11-18, review plan P4: one cell printed two ways in Tables 1 and 2)."""
    d = Decimal(f"{abs(x):.9f}").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (MINUS if x < 0 and d != 0 else "") + f"{d:.2f}"


def fmt_full(entry: dict) -> str:
    lo, hi = entry.get("ci_lo"), entry.get("ci_hi")
    if lo is None or hi is None:
        return fmt(entry["value"])
    return f"{fmt(entry['value'])} [{fmt(lo)}, {fmt(hi)}]"


def tex_minus(s: str) -> str:
    return s.replace(MINUS, "$-$")


def tie_warnings(entry: dict) -> list[str]:
    out = []
    for name in ("value", "ci_lo", "ci_hi"):
        v = entry.get(name)
        # a tie is a value that is x.xx5 after the 9-decimal snap; fmt rounds it half away from zero
        if v is not None and (Decimal(f"{abs(v):.9f}") * 100) % 1 == Decimal("0.5"):
            out.append(f"{name}={v!r} sits on an exact rounding tie")
    return out


# --------------------------------------------------------------------------- source parsing

def split_front_matter(text: str) -> tuple[dict, list[str]]:
    lines = text.split("\n")
    meta: dict = {}
    if lines and lines[0].strip() == "---":
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        for ln in lines[1:end]:
            m = re.match(r'^(\w+):\s*"(.*)"\s*$', ln)
            if m:
                meta[m.group(1)] = m.group(2)
        return meta, lines[: end + 1]
    return meta, []


def iter_body_lines(lines: list[str], start: int):
    """Yield (index, line, in_comment) for body lines; comment lines are flagged."""
    in_comment = False
    for i in range(start, len(lines)):
        ln = lines[i]
        was = in_comment
        if COMMENT_OPEN in ln and COMMENT_CLOSE not in ln.split(COMMENT_OPEN, 1)[1]:
            in_comment = True
        if in_comment and COMMENT_CLOSE in ln:
            in_comment = False
        yield i, ln, (was or COMMENT_OPEN in ln)


# --------------------------------------------------------------------------- tables

GAP_ANCHORS = ("The per-delay gap table", "Table 1 gives the gap", "Table 2 gives the gap")
GAP_RHOS = ["0.95", "1.15"]
GAP_DELTAS = [0, 1, 2, 4]
GAP_ABS = [("CE-LLF", "ce_llf"), ("Shared-rate MPC", "pop_mpc"), ("Targeted MPC", "guarded_mpc_e1")]
GAP_CAPTION = ("Top block: avoidable residual of three schedulers, lower is better. Middle block: gap, "
                  "best oblivious scheduler minus Targeted MPC, kWh per 100 participants per event, "
                  "$M = 3$, mean [95\\% interval], 100 development seeds. The comparator was fixed on tuning "
                  "seeds: CE-LLF at $\\delta = 0$ and Shared-rate MPC at $\\delta \\ge 1$, so columns "
                  "$\\delta \\ge 1$ repeat the targeting step of the post hoc split. Lower block: the same gap for the oracle.")
GAP_CAPTION_MD = ("Top block: avoidable residual of three schedulers, lower is better. Middle block: gap, "
                     "best oblivious scheduler minus Targeted MPC, kWh per 100 participants per event, "
                     "M = 3, mean [95% interval], 100 development seeds. The comparator was fixed on tuning "
                     "seeds: CE-LLF at δ = 0 and Shared-rate MPC at δ ≥ 1, so columns δ ≥ 1 repeat the "
                     "targeting step of the post hoc split. Lower block: the same gap for the oracle.")


def gap_table_spec(numbers: dict) -> dict:
    blocks = []
    specs = [(label, "abs", lambda rho, d, pol=pol: f"cell/F0R_M3_dA{d}_db0_rho{rho}_r0.3/{pol}/R_avoid_kwh_per100")
             for label, pol in GAP_ABS]
    specs += [("Targeted MPC gap", "gap", lambda rho, d: f"e1/primary/M3_rho{rho}/gap_dA{d}"),
              ("Oracle gap", "oracle", lambda rho, d: f"e1/primary/M3_rho{rho}/oracle_gap_dA{d}")]
    for label, group, keyf in specs:
        rows = []
        for rho in GAP_RHOS:
            cells = []
            for d in GAP_DELTAS:
                key = keyf(rho, d)
                if key not in numbers:
                    die(f"gap table needs missing key {key}")
                cells.append({"key": key, "text": fmt_full(numbers[key])})
            rows.append({"rho": rho, "cells": cells})
        blocks.append({"label": label, "group": group, "rows": rows})
    return {
        "id": "table1", "number": 1, "caption": GAP_CAPTION, "caption_md": GAP_CAPTION_MD,
        "header": ["", "$\\rho$"] + [f"$\\delta = {d}$" for d in GAP_DELTAS],
        "header_md": ["", "ρ"] + [f"δ = {d}" for d in GAP_DELTAS],
        "blocks": blocks,
    }


FACT_ANCHOR = "Table 3 gives the avoidable residual of each belief and rule"
FACT_ROWS = [("Point belief", "llf_ce", "llf"), ("Shared rate", "llf_pop", "llf"), ("Per participant", "llf_e1", "llf"),
             ("Point belief", "greedy_ce", "greedy"), ("Shared rate", "greedy_pop", "greedy"),
             ("Per participant", "greedy_e1", "greedy"),
             ("Point belief", "mpc_ce", "mpc"), ("Shared rate", "mpc_pop", "mpc"), ("Per participant", "mpc_e1", "mpc")]
FACT_GROUPS = {"llf": "LLF rule", "greedy": "Greedy expected-value ranker", "mpc": "MPC planner"}
FACT_CAPTION_MD = ("Belief-by-rule factorial: avoidable residual R_avoid in kWh per 100 participants per event, "
                   "M = 3, mean [95% interval], 100 development seeds, lower is better. Rules: LLF, the greedy "
                   "expected-value ranker and the MPC planner. Beliefs: a point belief (every setpoint delivers), one "
                   "shared failure rate and per-participant reliability. LLF with a point belief is CE-LLF and with "
                   "per-participant reliability LLF-POST. The planner with a point belief is CE-MPC, with the shared "
                   "rate Shared-rate MPC and with per-participant reliability Targeted MPC. Descriptive, post hoc.")
FACT_CAPTION = ("Belief-by-rule factorial: avoidable residual $R_{\\mathrm{avoid}}$ in kWh per 100 participants per "
                "event, $M = 3$, mean [95\\% interval], 100 development seeds, lower is better. Rules: LLF, the greedy "
                "expected-value ranker and the MPC planner. Beliefs: a point belief (every setpoint delivers), one "
                "shared failure rate and per-participant reliability. LLF with a point belief is CE-LLF and with "
                "per-participant reliability LLF-POST. The planner with a point belief is CE-MPC, with the shared "
                "rate Shared-rate MPC and with per-participant reliability Targeted MPC. Descriptive, post hoc.")


def factorial_table_spec(numbers: dict) -> dict:
    """Table 3 (journal; tables are numbered by position): R_avoid of the 3 x 3 factorial (keys factorial3/M3_rho{rho}/dA{d}/{rule}_{belief})."""
    blocks = []
    for label, suffix, rule in FACT_ROWS:
        rows = []
        for rho in GAP_RHOS:
            cells = []
            for d in GAP_DELTAS:
                key = f"factorial3/M3_rho{rho}/dA{d}/{suffix}"
                if key not in numbers:
                    die(f"factorial table needs missing key {key}")
                cells.append({"key": key, "text": fmt_full(numbers[key])})
            rows.append({"rho": rho, "cells": cells})
        blk = {"label": label, "group": rule, "rows": rows}
        if not blocks or blocks[-1]["group"] != rule:
            blk["group_title"] = FACT_GROUPS[rule]
        blocks.append(blk)
    return {
        "id": "table3", "number": 3, "caption": FACT_CAPTION, "caption_md": FACT_CAPTION_MD,
        "header": ["", "$\\rho$"] + [f"$\\delta = {d}$" for d in GAP_DELTAS],
        "header_md": ["", "ρ"] + [f"δ = {d}" for d in GAP_DELTAS],
        "blocks": blocks,
    }


CONF_POLICIES = [("CE-LLF", "ce_llf"), ("CE-MPC", "mpc_ce"), ("Shared-rate MPC", "pop_mpc"),
                 ("Targeted MPC", "guarded_mpc_e1"), ("Oracle", "oracle_mpc")]
CONF_CAPTION_MD = ("Confirmation run, descriptive (not a test): avoidable residual R_avoid of five schedulers in kWh "
                   "per 100 participants per event, M = 3, mean [95% interval], 200 reserved seeds, lower is better. "
                   "Bottom block: gap, best oblivious scheduler fixed on tuning seeds minus Targeted MPC, the quantity "
                   "behind C1 and C2. Per-cell means promised by the frozen protocol.")
CONF_CAPTION = ("Confirmation run, descriptive (not a test): avoidable residual $R_{\\mathrm{avoid}}$ of five schedulers "
                "in kWh per 100 participants per event, $M = 3$, mean [95\\% interval], 200 reserved seeds, lower is "
                "better. Bottom block: gap, best oblivious scheduler fixed on tuning seeds minus Targeted MPC, the "
                "quantity behind C1 and C2. Per-cell means promised by the frozen protocol.")


def confirm_table_spec(numbers: dict) -> dict:
    """Table 2 (it precedes the factorial in the text): per-cell confirmation means (keys confirm_cell/M3_rho{rho}/dA{d}/..., scripts/posthoc_fla_2026_11.py)."""
    specs = [(label, "abs", lambda rho, d, pol=pol: f"confirm_cell/M3_rho{rho}/dA{d}/{pol}/R_avoid_kwh_per100")
             for label, pol in CONF_POLICIES]
    specs.append(("Targeted MPC gap", "gap", lambda rho, d: f"confirm_cell/M3_rho{rho}/dA{d}/gap"))
    blocks = []
    for label, group, keyf in specs:
        rows = []
        for rho in GAP_RHOS:
            cells = []
            for d in GAP_DELTAS:
                key = keyf(rho, d)
                if key not in numbers:
                    die(f"confirmation table needs missing key {key} (run scripts/posthoc_fla_2026_11.py)")
                cells.append({"key": key, "text": fmt_full(numbers[key])})
            rows.append({"rho": rho, "cells": cells})
        blocks.append({"label": label, "group": group, "rows": rows})
    return {
        "id": "table4", "number": 2, "caption": CONF_CAPTION, "caption_md": CONF_CAPTION_MD,
        "header": ["", "$\\rho$"] + [f"$\\delta = {d}$" for d in GAP_DELTAS],
        "header_md": ["", "ρ"] + [f"δ = {d}" for d in GAP_DELTAS],
        "blocks": blocks,
    }


def layers_keys(numbers: dict) -> list[str]:
    return sorted(k for k in numbers if k.startswith("layers/"))


def layers_table_spec(numbers: dict):
    """Table 2: the three-layer decomposition at M = 3 (keys layers/M3_rho{rho}/dA{d}/{layer})."""
    keys = layers_keys(numbers)
    if not keys:
        return None, keys, "no layers/ keys"
    layers = [("planning", "Planning"),
              ("hedging", "Shared-rate hedging"),
              ("targeting", "Targeting"),
              ("total", "Total")]
    rhos, deltas = ["0.95", "1.15"], [0, 1, 2, 4]
    blocks, used = [], []
    for lname, label in layers:
        rows = []
        for r in rhos:
            cells = []
            for d in deltas:
                k = f"layers/M3_rho{r}/dA{d}/{lname}"
                if k not in numbers:
                    return None, keys, f"missing {k}"
                used.append(k)
                cells.append({"key": k, "text": fmt_full(numbers[k])})
            rows.append({"rho": r, "cells": cells})
        blocks.append({"label": label, "rows": rows})
    cap = ("Post hoc three-step path from CE-LLF to the candidate: planning (CE-LLF to MPC-CE), "
           "shared-rate hedging (MPC-CE to population MPC), targeting (population MPC to candidate). "
           "Gain of each step in kWh per 100 participants per event, three prior events, "
           "mean [95% interval], 100 development seeds. The split depends on the order of steps.")
    spec = {
        "id": "table2", "number": 2,
        "caption": cap.replace("%", "\\%"), "caption_md": cap,
        "header": ["", "$\\rho$"] + [f"$\\delta = {d}$" for d in deltas],
        "header_md": ["", "ρ"] + [f"δ = {d}" for d in deltas],
        "blocks": blocks,
    }
    return spec, used, "ok"


def tex_escape_plain(s: str) -> str:
    for a, b in (("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("#", "\\#"),
                 ("_", "\\_"), ("{", "\\{"), ("}", "\\}")):
        s = s.replace(a, b)
    return s


def table_rows_tex(spec: dict) -> list[str]:
    out = []
    for blk in spec["blocks"]:
        for i, row in enumerate(blk["rows"]):
            first = tex_escape_plain(blk["label"]) if i == 0 else ""
            cells = [tex_minus(c["text"]) for c in row["cells"]]
            out.append(" & ".join([first, row["rho"]] + cells) + " \\\\")
    return out


def table_header_tex(spec: dict) -> str:
    return " & ".join(spec["header"]) + " \\\\"


def group_row_tex(title: str, ncols: int) -> str:
    """A group heading row spanning the table (no & in it, so it is not a data row)."""
    return f"\\multicolumn{{{ncols}}}{{l}}{{\\textit{{{tex_escape_plain(title)}}}}} \\\\"


def table_tex(spec: dict) -> str:
    ncols = len(spec["header"])
    colspec = "ll" + "c" * (ncols - 2)
    lines = [f"\\setcounter{{table}}{{{spec['number'] - 1}}}",
             "\\begin{table*}[t]", "\\centering", f"\\begin{{tabular}}{{{colspec}}}", "\\toprule",
             table_header_tex(spec), "\\midrule"]
    rows = table_rows_tex(spec)
    k = 0
    prev = None
    for bi, blk in enumerate(spec["blocks"]):
        grp = blk.get("group", bi)
        if bi > 0 and grp != prev:
            lines.append("\\midrule")
        prev = grp
        if blk.get("group_title"):
            lines.append(group_row_tex(blk["group_title"], ncols))
        for _ in blk["rows"]:
            lines.append(rows[k])
            k += 1
    lines += ["\\bottomrule", "\\end{tabular}", f"\\caption{{{spec['caption']}}}",
              f"\\label{{tab:{spec['id']}}}", "\\end{table*}"]
    return "\n".join(lines)


def table_md(spec: dict) -> str:
    out = [f"<!-- {spec['id']}:begin -->",
           f"**Table {spec['number']}.** {spec['caption_md']}", "",
           "| " + " | ".join(spec["header_md"]) + " |",
           "|" + "|".join(["---"] * len(spec["header_md"])) + "|"]
    for blk in spec["blocks"]:
        if blk.get("group_title"):
            out.append("| *" + blk["group_title"] + "* |" + " |" * (len(spec["header_md"]) - 1))
        for i, row in enumerate(blk["rows"]):
            out.append("| " + " | ".join([blk["label"] if i == 0 else "", row["rho"]]
                                         + [c["text"] for c in row["cells"]]) + " |")
    out += ["", f"<!-- {spec['id']}:end -->"]
    return "\n".join(out)


def spec_keys(spec: dict) -> list[str]:
    return [c["key"] for b in spec["blocks"] for r in b["rows"] for c in r["cells"] if c["key"]]


# --------------------------------------------------------------------------- fill

def stage_fill(numbers_path: Path, strict: bool) -> dict:
    numbers = load_numbers(numbers_path)
    text = NOTE.read_text(encoding="utf-8")
    lines = text.split("\n")
    _, fm = split_front_matter(text)
    used: dict[str, dict] = {}
    missing: list[str] = []
    warnings: list[str] = []

    def use(key: str, mode: str, printed: str):
        e = numbers[key]
        rec = used.setdefault(key, {"value": e["value"], "ci_lo": e.get("ci_lo"), "ci_hi": e.get("ci_hi"),
                                    "uses": []})
        rec["uses"].append({"mode": mode, "text": printed})
        for w in tie_warnings(e):
            warnings.append(f"{key}: {w}")

    tg = gap_table_spec(numbers)
    tf = factorial_table_spec(numbers)
    tc = confirm_table_spec(numbers)
    tl, tl_keys, tl_note = layers_table_spec(numbers)
    tc_done = False
    out = list(fm)
    start = len(fm)
    tg_done = tl_done = tf_done = False
    for i, ln, in_comment in iter_body_lines(lines, start):
        if in_comment:
            out.append(ln)
            continue
        fid = fig_marker(ln)
        if fid is not None and fid not in FIGURES:
            die(f"line {i + 1}: [[FIG: {fid}]] names no figure; known ids: {', '.join(FIGURES)}")
        tid = table_marker(ln)
        if tid == "gap" and not tg_done:
            out.extend(table_md(tg).split("\n") + [""])
            for k in spec_keys(tg):
                use(k, "table", fmt_full(numbers[k]))
            tg_done = True
            continue
        if tid == "factorial" and not tf_done:
            out.extend(table_md(tf).split("\n") + [""])
            for k in spec_keys(tf):
                use(k, "table", fmt_full(numbers[k]))
            tf_done = True
            continue
        if tid == "confirm" and not tc_done:
            out.extend(table_md(tc).split("\n") + [""])
            for k in spec_keys(tc):
                use(k, "table", fmt_full(numbers[k]))
            tc_done = True
            continue
        if ln.startswith(GAP_ANCHORS) and not tg_done:
            out.extend(table_md(tg).split("\n") + [""])
            for k in spec_keys(tg):
                use(k, "table", fmt_full(numbers[k]))
            tg_done = True
        if ln.startswith(FACT_ANCHOR) and not tf_done:
            out.extend(table_md(tf).split("\n") + [""])
            for k in spec_keys(tf):
                use(k, "table", fmt_full(numbers[k]))
            tf_done = True
        if tl is not None and ln.startswith("[[LAYERS:") and ln.rstrip().endswith("]]") and not tl_done:
            out.extend(table_md(tl).split("\n"))
            for k in spec_keys(tl):
                use(k, "table", fmt_full(numbers[k]))
            tl_done = True
            continue

        def sub(m):
            key, v = m.group(1), m.group(2)
            if key not in numbers:
                missing.append(key)
                return m.group(0)
            e = numbers[key]
            if v == "i":
                if abs(e["value"] - round(e["value"])) > 1e-9:
                    die(f"{key} is not an integer: {e['value']}")
                s = str(int(round(e["value"])))
            elif v:
                s = fmt(e["value"])
            else:
                s = fmt_full(e)
                if e.get("ci_lo") is None or e.get("ci_hi") is None:
                    warnings.append(f"{key}: no interval, printed value only")
            use(key, {"i": "i", "v": "v"}.get(v, "full"), s)
            return s

        out.append(NUM_REF_RE.sub(sub, ln))
    if not tf_done:
        die(f"marker paragraph ('{FACT_ANCHOR}') not found in note.md")
    if not tg_done:
        die("marker paragraph ('The per-delay gap table' / 'Table 1 gives the gap' / 'Table 2 gives the gap') not found in note.md")
    if missing:
        die("keys missing from numbers file: " + ", ".join(sorted(set(missing))))
    BUILD.mkdir(parents=True, exist_ok=True)
    filled = "\n".join(out)
    (BUILD / "note_filled.md").write_text(filled, encoding="utf-8")
    (BUILD / "numbers_used.json").write_text(
        json.dumps({"numbers_file": str(numbers_path), "keys": used}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    todos = collect_todos(filled)
    (BUILD / "todos.json").write_text(json.dumps(todos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"fill: {len(used)} keys used, {sum(len(v['uses']) for v in used.values())} placeholders filled")
    print(f"fill: layers/ keys found: {len(tl_keys)}" + (f" -> {tl_keys}" if tl_keys else "")
          + f" ({tl_note})")
    ties = [w for w in warnings if "rounding tie" in w]
    if ties:
        print(f"fill: {len(ties)} printed numbers sit on an exact binary tie (x.xx5); rounded half away from zero")
    for w in warnings:
        if "rounding tie" not in w:
            print(f"fill: warning: {w}")
    print(f"fill: {len(todos)} TODO placeholder(s) remain:")
    for t in todos:
        print(f"   line {t['line']} [{t['section']}] {t['text']}")
    return {"todos": todos, "table1": tl, "layers_note": tl_note}


def collect_todos(filled: str) -> list[dict]:
    lines = filled.split("\n")
    _, fm = split_front_matter(filled)
    section = "(front matter)"
    todos = []
    for i, ln, in_comment in iter_body_lines(lines, len(fm)):
        if in_comment:
            continue
        if ln.startswith("#"):
            section = ln.lstrip("# ").strip()
        if fig_marker(ln) is not None or table_marker(ln) is not None:
            continue
        for m in TODO_RE.finditer(ln):
            todos.append({"line": i + 1, "section": section, "text": m.group(1),
                          "kind": "LAYERS" if m.group(1).startswith("LAYERS") else
                                  "R" if m.group(1).startswith("R:") else "other"})
    return todos


# --------------------------------------------------------------------------- placeholders and math

class Reg:
    def __init__(self):
        self.items: list[str] = []

    def add(self, latex: str) -> str:
        self.items.append(latex)
        return f"ZZPH{len(self.items) - 1}ZZ"

    def expand(self, s: str) -> str:
        prev = None
        while prev != s:
            prev = s
            s = PH_RE.sub(lambda m: self.items[int(m.group(1))], s)
        return s


GREEK = {"δ": "\\delta ", "ρ": "\\rho ", "σ": "\\sigma ", "Σ": "\\Sigma ", "γ": "\\gamma "}
REL = {"≤": "\\le ", "≥": "\\ge ", "∈": "\\in ", "×": "\\times "}
SVARS = set("qrcftsiKMNHI")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019]*")
NUM_RE = re.compile(r"\d+(?:\.\d+)?(?![A-Za-z0-9'\u2019])")
NUMVAR_RE = re.compile(r"(\d+)([A-Za-z])(?![A-Za-z0-9'\u2019])")
SUB_RE = re.compile(r"([A-Za-zδρσΣ])_([A-Za-z0-9]+)(?![A-Za-z0-9_])")
MATH_KINDS = {"sub", "greek", "rel", "dot", "minus", "op", "num", "punc", "caret", "func", "fname",
              "svar", "rstar", "cellip", "ws"}
STRONG = {"sub", "greek", "rel", "dot", "svar", "rstar"}


class Tok:
    __slots__ = ("kind", "text", "latex", "start", "end")

    def __init__(self, kind, text, latex, start, end):
        self.kind, self.text, self.latex, self.start, self.end = kind, text, latex, start, end


def _wordch(c: str) -> bool:
    return c.isalnum() or c in "'\u2019_"


def tokenize(s: str) -> list[Tok]:
    toks: list[Tok] = []
    p, n = 0, len(s)
    while p < n:
        ch = s[p]
        prev = s[p - 1] if p else " "
        m = re.match(r",\s\.\.\.,\s", s[p:])
        if m:
            toks.append(Tok("cellip", m.group(0), ", \\ldots, ", p, p + m.end()))
            p += m.end()
            continue
        if not _wordch(prev):
            m = SUB_RE.match(s, p)
            if m:
                base = GREEK.get(m.group(1), m.group(1))
                sub = m.group(2)
                subl = f"\\mathrm{{{sub}}}" if len(sub) >= 3 else sub
                toks.append(Tok("sub", m.group(0), f"{base}_{{{subl}}}", p, m.end()))
                p = m.end()
                continue
            if s.startswith("R*", p) and not (p + 2 < n and _wordch(s[p + 2])):
                toks.append(Tok("rstar", "R*", "R^{*}", p, p + 2))
                p += 2
                continue
            m = NUMVAR_RE.match(s, p)
            if m and m.group(2) in SVARS:
                toks.append(Tok("num", m.group(1), m.group(1), p, p + len(m.group(1))))
                toks.append(Tok("svar", m.group(2), m.group(2), p + len(m.group(1)), m.end()))
                p = m.end()
                continue
            m = NUM_RE.match(s, p)
            if m:
                toks.append(Tok("num", m.group(0), m.group(0), p, m.end()))
                p = m.end()
                continue
            m = WORD_RE.match(s, p)
            if m:
                w = m.group(0)
                nxt = s[m.end()] if m.end() < n else ""
                if w in ("min", "max"):
                    toks.append(Tok("func", w, f"\\{w} ", p, m.end()))
                elif w == "swap":
                    toks.append(Tok("func", w, "\\mathrm{swap}\\," , p, m.end()))
                elif len(w) == 1 and w in SVARS and nxt not in ("_",):
                    toks.append(Tok("svar", w, w, p, m.end()))
                elif len(w) == 1 and w.isupper() and nxt == "(":
                    toks.append(Tok("fname", w, w, p, m.end()))
                else:
                    toks.append(Tok("word", w, w, p, m.end()))
                p = m.end()
                continue
        if ch in GREEK:
            toks.append(Tok("greek", ch, GREEK[ch], p, p + 1))
        elif ch in REL:
            toks.append(Tok("rel", ch, REL[ch], p, p + 1))
        elif ch == "·":
            toks.append(Tok("dot", ch, "\\cdot ", p, p + 1))
        elif ch == MINUS:
            toks.append(Tok("minus", ch, "-", p, p + 1))
        elif ch in "=+/<>":
            toks.append(Tok("op", ch, ch, p, p + 1))
        elif ch == "^":
            m = re.match(r"\^([A-Za-z0-9]+)", s[p:])
            if m:
                toks.append(Tok("caret", m.group(0), f"^{{{m.group(1)}}}", p, p + m.end()))
                p += m.end()
                continue
            toks.append(Tok("other", ch, ch, p, p + 1))
        elif ch in "(),":
            toks.append(Tok("punc", ch, ch, p, p + 1))
        elif ch == "{" or ch == "}":
            toks.append(Tok("punc", ch, "\\" + ch, p, p + 1))
        elif ch == " " and not (p + 1 < n and s[p + 1] == " "):
            toks.append(Tok("ws", ch, " ", p, p + 1))
        else:
            toks.append(Tok("other", ch, ch, p, p + 1))
        p += 1
    return toks


_PAIR = {"(": ")", "{": "}"}


def _valid_segments(toks: list[Tok]) -> list[list[Tok]]:
    stack: list[tuple[int, str]] = []
    for i, t in enumerate(toks):
        if t.kind != "punc":
            continue
        if t.text in "({":
            stack.append((i, t.text))
        elif t.text in ")}":
            if stack and _PAIR[stack[-1][1]] == t.text:
                stack.pop()
            else:
                return _valid_segments(toks[:i]) + _valid_segments(toks[i + 1:])
        elif t.text == "," and not stack:
            return _valid_segments(toks[:i]) + _valid_segments(toks[i + 1:])
    if stack:
        i = stack[0][0]
        return _valid_segments(toks[:i]) + _valid_segments(toks[i + 1:])
    return [toks]


def mathify(s: str, reg: Reg) -> str:
    """Wrap variable and symbol runs in math, stored in the registry as placeholders."""
    toks = tokenize(s)
    spans: list[tuple[int, int, str]] = []
    i = 0
    while i < len(toks):
        if toks[i].kind not in MATH_KINDS:
            i += 1
            continue
        j = i
        while j < len(toks) and toks[j].kind in MATH_KINDS:
            j += 1
        for seg in _valid_segments(toks[i:j]):
            while seg and seg[0].kind == "ws":
                seg = seg[1:]
            while seg and seg[-1].kind == "ws":
                seg = seg[:-1]
            if any(t.kind in STRONG for t in seg):
                spans.append((seg[0].start, seg[-1].end, "".join(t.latex for t in seg)))
        i = j
    out, pos = [], 0
    for a, b, latex in sorted(spans):
        out.append(s[pos:a])
        out.append(reg.add("$" + re.sub(r"\s+", " ", latex).strip() + "$"))
        pos = b
    out.append(s[pos:])
    return "".join(out)


def latexize_plain(s: str, reg: Reg) -> str:
    """Plain text -> LaTeX (used for TODO boxes and the title): math runs, then escapes."""
    s = mathify(s, reg)
    s = s.replace(MINUS, "-")
    parts = reg.expand(s).split("$")
    for k in range(0, len(parts), 2):
        parts[k] = tex_escape_plain(parts[k])
    return "$".join(parts)


# --------------------------------------------------------------------------- bibliography

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
NAME = (r"(?:[A-Z]\.(?:-?[A-Z]\.)*(?:\s[A-Z]\.)*\s)+(?:(?:van|der|den|de|von|di|da|le|la)\s)*"
        r"[A-Z](?:[^\W\d_]|['\u2019\-])+")
AUTH_RE = re.compile(rf"^({NAME}(?:,\s{NAME})*(?:,?\sand\s{NAME})?)(\set al\.)?\.?\s+")


ACCENTS = {"ć": "{\\'c}", "č": "{\\v{c}}", "é": "{\\'e}", "è": "{\\`e}", "ë": "{\\\"e}", "ü": "{\\\"u}",
           "ö": "{\\\"o}", "ä": "{\\\"a}", "ñ": "{\\~n}", "ç": "{\\c{c}}", "á": "{\\'a}", "í": "{\\'i}",
           "ó": "{\\'o}", "ú": "{\\'u}", "š": "{\\v{s}}", "ž": "{\\v{z}}"}


def bib_escape(s: str) -> str:
    s = s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")
    for a, b in ACCENTS.items():
        s = s.replace(a, b)
    return s


# venue names typeset as journals (volume, optional issue); "Proceedings of the IEEE" is a journal, other
# "Proceedings of ..." venues are conference proceedings
JOURNAL_VENUE_RE = (r"Transactions|Journal|Communications|JSAC|Letters|^Applied Energy\b|^Proceedings of the IEEE\b|"
                    r"^Mathematical Programming\b")


def parse_ref(key: str, text: str) -> dict:
    flags = [m.group(1) for m in TODO_RE.finditer(text)]
    text = re.sub(r"\s*\[\[[^\]]+\]\]", "", text).strip()
    e: dict = {"key": key, "flags": flags, "inferred": []}
    m = re.search(r"\s*\bdoi:(\S+)\s*$", text)
    if m:
        e["doi"] = m.group(1)
        text = text[: m.start()].rstrip()
    m = re.search(r"\.?\s*\barXiv:(\d{4}\.\d{4,5})\.?\s*$", text)
    if m:
        e["eprint"] = m.group(1)
        text = text[: m.start()].rstrip()
    text = text.rstrip(".").strip()
    rest = text
    bm = re.match(r"^\{([^{}]+)\}\.\s+", text)  # "{FNU Ratnavarma}. Title..." -> author printed verbatim
    am = None if bm else AUTH_RE.match(text + " ")
    if bm:
        e["author"] = "{" + bm.group(1) + "}"
        rest = text[bm.end():].strip()
    elif am:
        names = re.split(r",\s*(?:and\s)?|\sand\s", am.group(1))
        e["author"] = " and ".join(n.strip() for n in names if n.strip()) + (" and others" if am.group(2) else "")
        rest = (text + " ")[am.end():].strip()
    sents = re.split(r"(?<=[A-Za-z0-9\)])\.\s+(?=[A-Z])", rest)
    if "author" not in e and len(sents) > 1 and " " not in sents[0]:
        e["author"] = "{" + sents[0] + "}"
        sents = sents[1:]
    title, venue = sents[0], ". ".join(sents[1:])
    ym = None
    if not venue:
        ym = re.search(rf",?\s*(?:({MONTHS})\s+)?((?:19|20)\d\d)$", title)
        if ym:
            title = title[: ym.start()]
            if ym.group(1):
                e["month"] = ym.group(1)
            e["year"] = ym.group(2)
    else:
        am2 = re.match(r"^(.*?),\s*(accessed\s+.*)$", venue)
        if am2:
            venue = am2.group(1)
            e["note"] = am2.group(2)[0].upper() + am2.group(2)[1:]
            yy = re.search(r"((?:19|20)\d\d)$", am2.group(2))
            if yy:
                e["year"] = yy.group(1)
        else:
            ym = re.search(r",?\s*((?:19|20)\d\d)$", venue)
            if ym:
                e["year"] = ym.group(1)
                venue = venue[: ym.start()]
    pm = re.search(r",\s*(?:pp\.\s*(\d+(?:-\d+)?)|article\s+(\d+))$", venue or "")
    if pm:
        e["pages"] = pm.group(1) or pm.group(2)
        e["article_number"] = bool(pm.group(2))
        venue = venue[: pm.start()]
    for tag in ("software", "dataset"):
        if title.rstrip().endswith(f"({tag})"):
            e["tag"] = tag
    if "year" not in e:
        km = re.search(r"((?:19|20)\d\d)", key)
        if km:
            e["year"] = km.group(1)
            e["inferred"].append("year taken from the citation key")
    em = re.search(r",\s*(\d+(?:st|nd|rd|th))\s+edition$", title.strip())
    if em:  # "Title, 3rd edition" -> edition field
        e["edition"] = em.group(1)
        title = title.strip()[: em.start()]
    e["title"] = title.strip()
    journalish = bool(re.search(JOURNAL_VENUE_RE, venue or ""))
    jm = re.match(r"^(.*?)\s+(\d+)\((\d+)\)$", venue)
    jv = re.match(r"^(.*?)\s+(\d+)$", venue) if journalish and not jm else None  # volume without an issue
    if jm:
        e["journal"], e["volume"], e["number"] = jm.group(1), jm.group(2), jm.group(3)
    elif jv:
        e["journal"], e["volume"] = jv.group(1), jv.group(2)
    elif venue:
        e["venue"] = venue
    if re.search(r"\bPress$", venue or "") and "eprint" not in e:
        e["type"] = "book"
        e["publisher"] = venue
        return e
    if "eprint" in e or not journalish:
        e["type"] = "misc"
        if venue:
            e["howpublished"] = venue
    else:
        e["type"] = "article"
        e.setdefault("journal", venue)
    return e


def bib_entry(e: dict) -> str:
    f = []
    if "author" in e:
        f.append(("author", e["author"] if e["author"].startswith("{") else bib_escape(e["author"])))
    else:
        # no author in the source line: give BibTeX a sort and label key from the title head
        f.append(("key", bib_escape(e["title"].split(":")[0])))
    f.append(("title", bib_escape(e["title"])))
    if e["type"] == "article":
        f.append(("journal", bib_escape(e["journal"])))
        if "volume" in e:
            f.append(("volume", e["volume"]))
        if "number" in e:
            f.append(("number", e["number"]))
    elif e["type"] == "book":
        f.append(("publisher", bib_escape(e["publisher"])))
        if "edition" in e:
            f.append(("edition", e["edition"]))
    elif "howpublished" in e:
        f.append(("howpublished", bib_escape(e["howpublished"])))
    f.append(("year", e["year"]))
    if "month" in e:
        f.append(("month", e["month"]))
    if "eprint" in e:
        f += [("eprint", e["eprint"]), ("archivePrefix", "arXiv")]
    if "doi" in e:
        f.append(("doi", e["doi"]))
    note = bib_escape(e["note"]) if "note" in e else ""
    if e["flags"]:
        todo = "".join(f"\\todoinline{{{tex_escape_plain(x)}}}" for x in e["flags"])
        note = (note + " " if note else "") + todo
    if note:
        f.append(("note", "{" + note + "}"))
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f)
    return f"@{e['type']}{{{e['key']},\n{body}\n}}\n"


def read_refs(filled_or_note: list[str]) -> list[dict]:
    in_refs, entries = False, []
    for ln in filled_or_note:
        if ln.startswith("# "):
            in_refs = ln.strip() == "# References"
            continue
        if in_refs:
            m = re.match(r"^- \[([^\]]+)\]\s+(.*)$", ln)
            if m:
                entries.append(parse_ref(m.group(1), m.group(2)))
    return entries


# --------------------------------------------------------------------------- tex

def run_pandoc(md: str) -> str:
    cmd = [tool("pandoc"), "-f", "markdown-auto_identifiers+smart-raw_tex-tex_math_dollars-citations-raw_html",
           "-t", "latex", "--wrap=none"]
    r = subprocess.run(cmd, input=md, capture_output=True, text=True)
    if r.returncode != 0:
        die("pandoc failed: " + r.stderr)
    return r.stdout


def preprocess(md: str, reg: Reg, bibkeys: set[str]) -> str:
    """Markdown with Unicode -> Markdown where every special piece is a placeholder."""
    out = []
    for ln in md.split("\n"):
        if ln.startswith("```"):
            out.append(ln)
            continue
        if re.fullmatch(r"\[\[LAYERS:[^\]]*\]\]", ln.strip()):
            inner = latexize_plain(ln.strip()[2:-2], reg)
            box = ("\\par\\noindent\\fbox{\\parbox{0.92\\columnwidth}{\\textbf{\\textcolor{red}{TODO [" + inner
                   + "]}}}}\\par")
            out.append(reg.add(box))
            continue

        def cite(m):
            ks = [k.strip() for k in m.group(1).split(";")]
            unknown = [k for k in ks if k not in bibkeys]
            if unknown:
                if any(re.search(r"\d{4}", k) for k in unknown):
                    die(f"citation key {unknown} has no entry in the reference list")
                return m.group(0)
            return reg.add("\\cite{" + ",".join(ks) + "}")

        ln = CITE_RE.sub(cite, ln)
        ln = TODO_RE.sub(lambda m: reg.add("\\todoinline{" + latexize_plain(m.group(1), reg) + "}"), ln)
        ln = mathify(ln, reg)
        ln = re.sub(MINUS, lambda m: reg.add("$-$"), ln)
        out.append(ln)
    return "\n".join(out)


def post_tex(tex: str, reg: Reg) -> str:
    tex = re.sub(r"\\tightlist\n?", "", tex)
    tex = re.sub(r"\\label\{[^}]*\}", "", tex)
    tex = re.sub(r"\\hypertarget\{[^}]*\}\{%?\n?", "", tex)
    tex = reg.expand(tex)
    for a, b in (("\u2013", "--"), ("\u2019", "'"), ("\u2018", "`"), ("\u201c", "``"), ("\u201d", "''"),
                 ("\u00a0", "~")):
        tex = tex.replace(a, b)
    tex = re.sub(r"\n{3,}", "\n\n", tex)
    return tex.strip() + "\n"


def figure_block(fig: dict, present: bool) -> str:
    lines = [f"\\setcounter{{figure}}{{{fig['number'] - 1}}}", "\\begin{figure}[t]", "\\centering"]
    if present:
        lines.append(f"\\includegraphics[width=0.9\\columnwidth]{{{fig['file']}}}")
    else:
        name = fig["file"].replace("_", "\\_")
        lines.append("\\fbox{\\parbox[c][1.5in][c]{0.8\\columnwidth}{\\centering\\textbf{\\textcolor{red}{"
                     f"TODO figure {name} not built yet}}}}}}}}")
    lines += [f"\\caption{{{fig['caption']}}}", f"\\label{{fig:{fig['file'][:-4]}}}", "\\end{figure}"]
    return "\n".join(lines)


def template_preamble() -> str:
    tpl = (KIT / "AnonymousSubmission2027.tex").read_text(encoding="utf-8").split("\n")
    keep = [ln for ln in tpl[:13] if "DO NOT CHANGE" in ln]
    if len(keep) != 9:
        die(f"expected 9 DO NOT CHANGE lines in the template preamble, found {len(keep)}")
    pdfinfo_i = next(i for i, ln in enumerate(tpl) if ln.startswith("\\pdfinfo"))
    pdfinfo = tpl[pdfinfo_i: pdfinfo_i + 3]
    return "\n".join(keep[:2] + [
        "% Fonts are loaded by aaai2027.sty. No font package is added here.",
    ] + keep[2:] + ["", "% Recommended for better-looking tables", "\\usepackage{booktabs}", ""]
        + ["% Keep the \\pdfinfo as in the template."] + pdfinfo + [
        "", "\\setcounter{secnumdepth}{0}",
        "",
        "% Draft aids. They appear only while a placeholder remains (build.py --strict refuses these).",
        "\\newcommand{\\todoinline}[1]{\\fbox{\\textbf{\\textcolor{red}{TODO [#1]}}}}",
    ])


def place_figures(main: str, has_fig: dict) -> tuple[str, list[str], list[str]]:
    """Put a ZZBLOCKF<number>ZZ tag where each figure goes. Returns (text, ids in text order, ids not placed).

    A [[FIG: id]] line wins. Otherwise fig_layers follows Table 2 (or the [[LAYERS: ...]] line) and
    fig_e3 follows the first paragraph containing "(Figure <number>)". Any other figure needs a marker.
    """
    tag = lambda fid: f"ZZBLOCKF{FIGURES[fid]['number']}ZZ"
    marked: dict[str, int] = {}
    for k, ln in enumerate(main.split("\n")):
        fid = fig_marker(ln)
        if fid is None:
            continue
        if fid not in FIGURES:
            die(f"[[FIG: {fid}]] names no figure; known ids: {', '.join(FIGURES)}")
        if fid in marked:
            die(f"[[FIG: {fid}]] appears twice in note.md")
        marked[fid] = k
    cite = f"(Figure {FIGURES['fig_e3']['number']})"
    out: list[str] = []
    done = set(marked)
    for ln in main.split("\n"):
        fid = fig_marker(ln)
        if fid is not None:
            out += ["", tag(fid), ""]
            continue
        out.append(ln)
        if "fig_layers" not in done and (ln.strip() == "ZZBLOCKLAYZZ" or ln.startswith("[[LAYERS:")):
            out += ["", tag("fig_layers"), ""]
            done.add("fig_layers")
        if "fig_e3" not in done and cite in ln:
            out += ["", tag("fig_e3"), ""]
            done.add("fig_e3")
    for fid, why in (("fig_layers", "no [[LAYERS: ...]] line, no Table 2 block"),
                     ("fig_e3", f"no paragraph cites '{cite}'")):
        if fid not in done:
            die(f"{fid} (Figure {FIGURES[fid]['number']}, {FIGURES[fid]['file']}) has no place: {why} "
                f"and no [[FIG: {fid}]] marker")
    text = "\n".join(out)
    order = sorted(done, key=lambda f: text.index(tag(f)))
    return text, order, [f for f in FIGURES if f not in done]


def stage_tex(numbers_path: Path, strict: bool) -> dict:
    numbers = load_numbers(numbers_path)
    if not (BUILD / "note_filled.md").exists():
        stage_fill(numbers_path, strict)
    filled = (BUILD / "note_filled.md").read_text(encoding="utf-8")
    meta, fm = split_front_matter(filled)
    lines = filled.split("\n")[len(fm):]
    refs = read_refs(lines)
    bibkeys = {r["key"] for r in refs}
    # sections
    sec_idx = [i for i, ln in enumerate(lines) if ln.startswith("# ")]
    titles = {lines[i].strip()[2:]: i for i in sec_idx}
    for need in ("Abstract", "References"):
        if need not in titles:
            die(f"section '# {need}' missing in note")
    bounds = sec_idx + [len(lines)]
    abstract_lines = lines[titles["Abstract"] + 1: bounds[bounds.index(titles["Abstract"]) + 1]]
    main_lines: list[str] = []
    for a, b in zip(bounds, bounds[1:]):
        if lines[a].strip() in ("# Abstract", "# References"):
            continue
        main_lines.extend(lines[a:b])
    # table and figure blocks
    reg = Reg()
    tg = gap_table_spec(numbers)
    tl, tl_keys, tl_note = layers_table_spec(numbers)
    has_fig = {k: (FIGS / v["file"]).exists() for k, v in FIGURES.items()}
    figs_missing = [v["file"] for k, v in FIGURES.items() if not has_fig[k]]
    main = "\n".join(main_lines)
    main = re.sub(r"<!-- table1:begin -->.*?<!-- table1:end -->",
                  lambda m: "ZZBLOCKGAPZZ", main, flags=re.S)
    main = re.sub(r"<!-- table3:begin -->.*?<!-- table3:end -->",
                  lambda m: "ZZBLOCKFACZZ", main, flags=re.S)
    main = re.sub(r"<!-- table4:begin -->.*?<!-- table4:end -->",
                  lambda m: "ZZBLOCKCONZZ", main, flags=re.S)
    layers_placed = "<!-- table2:begin -->" in main
    main = re.sub(r"<!-- table2:begin -->.*?<!-- table2:end -->",
                  lambda m: "ZZBLOCKLAYZZ", main, flags=re.S)
    main = re.sub(r"<!--.*?-->\n?", "", main, flags=re.S)
    main, fig_order, figs_unplaced = place_figures(main, has_fig)
    tf = factorial_table_spec(numbers)
    tc = confirm_table_spec(numbers)
    blocks = {"ZZBLOCKGAPZZ": table_tex(tg), "ZZBLOCKFACZZ": table_tex(tf), "ZZBLOCKCONZZ": table_tex(tc)}
    for fid, fig in FIGURES.items():
        blocks[f"ZZBLOCKF{fig['number']}ZZ"] = figure_block(fig, has_fig[fid])
    layers_todo = tl is None
    if tl is not None:
        blocks["ZZBLOCKLAYZZ"] = table_tex(tl)
    for tag, latex in blocks.items():
        main = main.replace(tag, reg.add(latex))
    abstract_md = "\n".join(abstract_lines).strip()
    pre_abs = preprocess(abstract_md, reg, bibkeys)
    pre_main = preprocess(main, reg, bibkeys)
    abstract_tex = post_tex(run_pandoc(pre_abs), reg)
    main_tex = post_tex(run_pandoc(pre_main), reg)
    title = meta["title"].rstrip(":") + ": " + meta["subtitle"] if meta.get("subtitle") else meta["title"]
    title_tex = latexize_plain(title, reg)
    tex = "\n".join([
        template_preamble(), "",
        f"\\title{{{title_tex}}}",
        "\\author{Anonymous Submission}",
        "\\affiliations{ }",
        "", "\\begin{document}", "", "\\maketitle", "",
        "\\begin{abstract}", abstract_tex.strip(), "\\end{abstract}", "",
        main_tex.strip(), "",
        "% References and End of Paper",
        "% These lines must be placed at the end of your paper",
        "\\bibliography{refs}", "", "\\end{document}", ""])
    bad = sorted({c for c in tex if ord(c) > 127})
    if bad:
        die("non-ASCII characters left in paper.tex: " + ", ".join(f"U+{ord(c):04X}" for c in bad))
    if "ZZPH" in tex or "ZZBLOCK" in tex:
        die("unexpanded placeholder in paper.tex")
    BUILD.mkdir(parents=True, exist_ok=True)
    # keep numeric intervals on one line: "{[}a, b{]}" -> "{[}a,~b{]}" (pandoc renders brackets as {[} {]})
    tex = re.sub(r"(\{\[\}(?:\$-\$)?\d+\.\d+),\s+((?:\$-\$)?\d+\.\d+\{\]\})", r"\1,~\2", tex)
    # and keep a value attached to its interval: "1.23 {[}" -> "1.23~{[}"
    tex = re.sub(r"(\d) \{\[\}((?:\$-\$)?\d+\.\d+,~)", r"\1~{[}\2", tex)
    (BUILD / "paper.tex").write_text(tex, encoding="utf-8")
    bib = "".join(bib_entry(e) + "\n" for e in refs)
    # --build keeps every output in that folder; only the default build refreshes the tracked paper/refs.bib
    bib_out = PAPER / "refs.bib" if BUILD == (PAPER / "build").resolve() else BUILD / "refs.bib"
    if bib_out != BUILD / "refs.bib":
        bib_out.write_text(bib, encoding="utf-8")
    (BUILD / "refs.bib").write_text(bib, encoding="utf-8")
    t_out = {"table1": {"keys": spec_keys(tg), "header": table_header_tex(tg), "rows": table_rows_tex(tg),
                        "caption": tg["caption"]}}
    t_out["table3"] = {"keys": spec_keys(tf), "header": table_header_tex(tf), "rows": table_rows_tex(tf),
                       "caption": tf["caption"]}
    t_out["table4"] = {"keys": spec_keys(tc), "header": table_header_tex(tc), "rows": table_rows_tex(tc),
                       "caption": tc["caption"]}
    if tl is not None and layers_placed:
        t_out["table2"] = {"keys": spec_keys(tl), "header": table_header_tex(tl), "rows": table_rows_tex(tl),
                           "caption": tl["caption"]}
    (BUILD / "tables.json").write_text(json.dumps(t_out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    ref_flags = [{"key": e["key"], "flags": e["flags"], "inferred": e["inferred"]} for e in refs
                 if e["flags"] or e["inferred"]]
    print(f"tex: wrote {BUILD / 'paper.tex'} and {bib_out} ({len(refs)} entries)")
    print(f"tex: figures placed (in text order): {fig_order or 'none'}; not placed: {figs_unplaced or 'none'}")
    if fig_order != sorted(fig_order, key=lambda f: FIGURES[f]["number"]):
        print("tex: warning: figures appear out of number order: "
              + ", ".join(f"{f} (Figure {FIGURES[f]['number']})" for f in fig_order))
    print(f"tex: figures missing: {figs_missing or 'none'}; Table 2 {'TODO box' if layers_todo else ('generated' if layers_placed else 'not placed (dropped on purpose)')}"
          f" (layers/ keys: {tl_keys or 'none'}; {tl_note})")
    for r in ref_flags:
        print(f"tex: reference {r['key']}: flags={r['flags']} inferred={r['inferred']}")
    return {"figs_missing": figs_missing, "figs_unplaced": figs_unplaced, "layers_todo": layers_todo,
            "ref_flags": ref_flags}


# --------------------------------------------------------------------------- pdf

def stage_pdf_pdflatex(tex: Path) -> dict:
    """The submission build: the unmodified AAAI-27 kit with pdflatex, bibtex, pdflatex, pdflatex."""
    sub = BUILD / "pdflatex"
    if sub.exists():
        shutil.rmtree(sub)
    sub.mkdir(parents=True)
    shutil.copy(KIT / "aaai2027.sty", sub)
    shutil.copy(KIT / "aaai2027.bst", sub)
    shutil.copy(tex, sub / "paper.tex")
    shutil.copy(BUILD / "refs.bib", sub / "refs.bib")
    for f in FIGURES.values():
        if (FIGS / f["file"]).exists():
            shutil.copy(FIGS / f["file"], sub / f["file"])
    log = []
    for cmd in (["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                ["bibtex", "paper"],
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"]):
        r = subprocess.run(cmd, cwd=sub, capture_output=True, text=True, errors="replace")  # bibtex echoes Latin-1 bytes
        log.append(" ".join(cmd) + "\n" + r.stdout[-4000:] + r.stderr[-2000:])
        if r.returncode != 0:
            (BUILD / "pdflatex_stdout.txt").write_text("\n\n".join(log), encoding="utf-8")
            print(log[-1][-3000:])
            die(f"{cmd[0]} failed")
    (BUILD / "pdflatex_stdout.txt").write_text("\n\n".join(log), encoding="utf-8")
    shutil.copy(sub / "paper.pdf", BUILD / "paper.pdf")
    for ext in ("log", "blg"):
        if (sub / f"paper.{ext}").exists():
            shutil.copy(sub / f"paper.{ext}", BUILD / f"paper.{ext}")
    print(f"pdf: wrote {BUILD / 'paper.pdf'} (pdflatex + bibtex, unmodified AAAI-27 kit)")
    return {}


def stage_pdf() -> dict:
    tex = BUILD / "paper.tex"
    if not tex.exists():
        die("paper.tex missing; run the tex stage first")
    if shutil.which("pdflatex") and shutil.which("bibtex"):
        return stage_pdf_pdflatex(tex)
    prev = BUILD / "preview"
    if prev.exists():
        shutil.rmtree(prev)
    prev.mkdir(parents=True)
    sty = (KIT / "aaai2027.sty").read_text(encoding="utf-8")
    patched, n = re.subn(r"^\\RequirePDFTeX", r"%\\RequirePDFTeX", sty, flags=re.M)
    if n != 1:
        print("pdf: warning: engine guard line not found in aaai2027.sty")
    (prev / "aaai2027.sty").write_text(patched, encoding="utf-8")
    shutil.copy(KIT / "aaai2027.bst", prev)
    shutil.copy(tex, prev / "paper.tex")
    shutil.copy(BUILD / "refs.bib", prev / "refs.bib")
    for f in FIGURES.values():
        if (FIGS / f["file"]).exists():
            shutil.copy(FIGS / f["file"], prev / f["file"])
    r = subprocess.run([tool("tectonic"), "-X", "compile", "--keep-logs", "paper.tex"], cwd=prev,
                       capture_output=True, text=True)
    (BUILD / "tectonic_stdout.txt").write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
    if r.returncode != 0 or not (prev / "paper.pdf").exists():
        print((r.stdout + r.stderr)[-3000:])
        die("tectonic failed")
    shutil.copy(prev / "paper.pdf", BUILD / "paper.pdf")
    if (prev / "paper.log").exists():
        shutil.copy(prev / "paper.log", BUILD / "paper.log")
    print(f"pdf: wrote {BUILD / 'paper.pdf'} (preview engine: tectonic/XeTeX with the pdfTeX guard commented out"
          " in a copy of the kit)")
    return {}


# --------------------------------------------------------------------------- JOURNAL PROFILE
# Applied Energy (Elsevier) build, added 2026-11-02. Same fill stage and numbers as the AAAI build. Differences:
# elsarticle (preprint, review, 12pt, single column, line numbers), numbered sections 1, 1.1, 1.1.1, numbered
# references in order of first citation (elsarticle-num) with shortened last pages and at most six authors,
# table captions below tables, figures as separate vector files Figure_<n>.pdf, appendices after the main text,
# then the declarations (CRediT, competing interest, funding, data availability, generative AI) directly before
# the references. The data availability text is the note's "Data and code" section; the other declarations come
# from paper/journal/*.md. The author block comes from paper/journal/front.json (never from note.md, so the AAAI
# build stays anonymous). The title is the single front-matter field "title" of note.md.

JOURNAL = PAPER / "journal"
JOURNAL_BUILD = PAPER / "build_journal"
SIDE = JOURNAL  # where the generated side files go: paper/journal/ for the default build, <build>/journal/ otherwise
FRONT = JOURNAL / "front.json"
JOURNAL_TEMPLATES = JOURNAL / "templates"
DECLARATIONS = [  # (source, fallback title); data availability comes from the note's "Data and code" section
    ("credit.md", "CRediT authorship contribution statement"),
    ("competing_interests.md", "Declaration of competing interest"),
    ("funding.md", "Funding"),
    ("@data", "Data availability"),
    ("genai_declaration.md",
     "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process"),
]
RED_DECLARATIONS = ()  # 2026-11-18: data and AI statements in red; 2026-11-24: AI and data statements approved, red removed
UPLOAD_ZIP = "paperE_applied_energy_latex.zip"
JOURNAL_FIG_WIDTH = "0.62\\textwidth"
MAX_BIB_AUTHORS = 6


def journal_fig_name(fid: str) -> str:
    return f"Figure_{FIGURES[fid]['number']}.pdf"


def shorten_pages(p: str) -> str:
    """'2209-2217' -> '2209--17' (Elsevier: shortened last page, e.g. 51-9); single pages unchanged."""
    if "-" not in p:
        return p
    a, b = p.split("-", 1)
    if len(a) == len(b):
        i = 0
        while i < len(b) - 1 and a[i] == b[i]:
            i += 1
        b = b[i:]
    return f"{a}--{b}"


def protect_case(title: str) -> str:
    """Brace every word with a capital that is not just the first letter of the title, so the bst keeps it
    (EV2Gym, V2G, EV, QoS, MPC)."""
    words = title.split(" ")
    out = []
    for i, w in enumerate(words):
        core = w.strip(":,.;()")
        caps = sum(c.isupper() for c in core)
        if core and (caps > 1 or (caps == 1 and (i > 0 or not core[0].isupper()))) and "\\" not in core:
            w = w.replace(core, "{" + core + "}", 1)
        out.append(w)
    return " ".join(out)


def journal_bib_entry(e: dict) -> str:
    f = []
    title = re.sub(r"\s*\((software|dataset)\)\s*$", "", e["title"]).strip()
    if "author" in e:
        if e["author"].startswith("{"):
            f.append(("author", e["author"]))
        else:
            names = [n for n in e["author"].split(" and ") if n != "others"]
            more = "others" in e["author"].split(" and ") or len(names) > MAX_BIB_AUTHORS
            names = names[:MAX_BIB_AUTHORS]
            f.append(("author", bib_escape(" and ".join(names + (["others"] if more else [])))))
    else:
        f.append(("key", bib_escape(title.split(":")[0])))
    f.append(("title", protect_case(bib_escape(title))))
    venue = e.get("journal") or e.get("venue") or e.get("howpublished") or ""
    url = None
    m = re.search(r",?\s*(https?://[^\s,]+?)(?=[.,]?(?:,|\s|$))", venue)
    if m:
        url = m.group(1)
        venue = (venue[: m.start()] + venue[m.end():]).strip().strip(",").strip()
    if e["type"] == "article":
        etype = "article"
        f.append(("journal", bib_escape(e["journal"])))
        if "volume" in e:
            f.append(("volume", e["volume"]))
        if "number" in e:
            f.append(("number", e["number"]))
    elif e["type"] == "book":
        etype = "book"
        f.append(("publisher", bib_escape(e["publisher"])))
        if "edition" in e:
            f.append(("edition", e["edition"]))
    elif "doi" in e or "pages" in e:
        etype = "inproceedings"
        f.append(("booktitle", bib_escape(venue)))
    else:
        etype = "misc"
        if venue:
            f.append(("howpublished", bib_escape(venue)))
    if "pages" in e:
        f.append(("pages", shorten_pages(e["pages"])))
    f.append(("year", e["year"]))
    if "doi" in e:
        f.append(("doi", e["doi"]))
    if url:
        f.append(("url", url))
    if "note" in e:
        f.append(("note", "{" + bib_escape(e["note"]) + "}"))
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f)
    return f"@{etype}{{{e['key']},\n{body}\n}}\n"


def load_front() -> dict:
    if not FRONT.exists():
        die(f"author block missing: {FRONT}")
    return json.loads(FRONT.read_text(encoding="utf-8"))


def tex_text(s: str) -> str:
    """Plain front-matter text (title, names, keywords) to LaTeX, ASCII only."""
    reg = Reg()
    out = latexize_plain(s, reg)
    for a, b in (("\u2013", "--"), ("\u2019", "'"), ("\u00a0", "~")):
        out = out.replace(a, b)
    return out


def section_bodies(lines: list[str]) -> tuple[dict, list[tuple[int, int]]]:
    sec_idx = [i for i, ln in enumerate(lines) if ln.startswith("# ")]
    bounds = list(zip(sec_idx, sec_idx[1:] + [len(lines)]))
    titles = {lines[a].strip()[2:]: (a, b) for a, b in bounds}
    return titles, bounds


def md_to_tex(md: str, reg: Reg, bibkeys: set[str]) -> str:
    return post_tex(run_pandoc(preprocess(md, reg, bibkeys)), reg).strip()


def journal_appendix_md(main: str, reg: Reg) -> str:
    """'# Appendix A. Title' -> \\appendix + numbered section; '## A.1 Title' -> '## Title' (the class numbers them)."""
    out, first = [], True
    for ln in main.split("\n"):
        m = re.match(r"^# Appendix ([A-Z])\.\s+(.*)$", ln)
        if m:
            latex = ("\\appendix\n" if first else "") + "\\section{" + latexize_plain(m.group(2), reg) + "}"
            first = False
            out += ["", reg.add(latex), ""]
            continue
        m = re.match(r"^(#{2,3})\s+[A-Z]\.\d+(?:\.\d+)?\s+(.*)$", ln)
        if m:
            out.append(f"{m.group(1)} {m.group(2)}")
            continue
        out.append(ln)
    return "\n".join(out)


def journal_table_tex(spec: dict) -> str:
    ncols = len(spec["header"])
    colspec = "ll" + "c" * (ncols - 2)
    lines = ["\\begin{table}[H]", "\\centering", "\\scriptsize", "\\setlength{\\tabcolsep}{2.5pt}",
             f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", table_header_tex(spec), "\\midrule"]
    rows = table_rows_tex(spec)
    k, prev = 0, None
    for bi, blk in enumerate(spec["blocks"]):
        grp = blk.get("group", bi)
        if bi > 0 and grp != prev:
            lines.append("\\midrule")
        prev = grp
        if blk.get("group_title"):
            lines.append(group_row_tex(blk["group_title"], ncols))
        for _ in blk["rows"]:
            lines.append(rows[k])
            k += 1
    # caption below the table (the author's Applied Energy rule, 2026-11-18), at normal size
    lines += ["\\bottomrule", "\\end{tabular}", "\\normalsize", f"\\caption{{{spec['caption']}}}",
              f"\\label{{tab:{spec['id']}}}", "\\end{table}"]
    return "\n".join(lines)


def journal_figure_block(fid: str) -> str:
    fig = FIGURES[fid]
    stem = journal_fig_name(fid)[:-4]
    return "\n".join(["\\begin{figure}[H]", "\\centering",
                      f"\\includegraphics[width={JOURNAL_FIG_WIDTH}]{{{stem}}}",
                      f"\\caption{{{fig['caption']}}}", f"\\label{{fig:{fid}}}", "\\end{figure}"])


def journal_preamble() -> str:
    return "\n".join([
        "\\documentclass[preprint,review,12pt]{elsarticle}",
        "% Elsevier elsarticle, single column. 'review' sets 1.5 line spacing; lineno numbers the lines for review.",
        "\\usepackage{amsmath,amssymb}",
        "\\usepackage{graphicx}",
        "\\usepackage{booktabs}",
        "\\usepackage{lineno}",
        "\\usepackage{xurl}",
        "\\usepackage[hidelinks]{hyperref}",
        "\\usepackage{xcolor}",
        "\\usepackage{float}  % [H]: every table and figure sits where the text cites it (the author, 2026-11-18)",
        "\\setcounter{secnumdepth}{3}",
        "% Floats near the text that cites them: allow large floats in text pages, few float-only pages.",
        "\\renewcommand{\\topfraction}{0.9}",
        "\\renewcommand{\\bottomfraction}{0.8}",
        "\\renewcommand{\\textfraction}{0.07}",
        "\\renewcommand{\\floatpagefraction}{0.85}",
        "\\setcounter{totalnumber}{4}",
        "% Intervals are kept on one line (value~[lo,~hi]); a generous emergency stretch and a raised tolerance let",
        "% justified lines absorb them instead of overfilling the margin. Layout only; no wording changes.",
        "\\setlength{\\emergencystretch}{8em}",
        "\\tolerance=2000",
        "\\journal{Applied Energy}",
        "\\newcommand{\\todoinline}[1]{\\fbox{\\textbf{TODO [#1]}}}",
    ])


def stage_tex_journal(numbers_path: Path, strict: bool) -> dict:
    numbers = load_numbers(numbers_path)
    if not (BUILD / "note_filled.md").exists():
        stage_fill(numbers_path, strict)
    filled = (BUILD / "note_filled.md").read_text(encoding="utf-8")
    meta, fm = split_front_matter(filled)
    if "subtitle" in meta:
        die("the journal title is the single front-matter field 'title'; remove 'subtitle' from note.md")
    for need in ("title", "keywords"):
        if not meta.get(need):
            die(f"front-matter field '{need}' missing in note.md")
    front = load_front()
    lines = filled.split("\n")[len(fm):]
    refs = read_refs(lines)
    bibkeys = {r["key"] for r in refs}
    titles, bounds = section_bodies(lines)
    for need in ("Abstract", "References", "Data and code"):
        if need not in titles:
            die(f"section '# {need}' missing in note")
    a, b = titles["Abstract"]
    abstract_md = "\n".join(lines[a + 1: b]).strip()
    a, b = titles["Data and code"]
    data_md = re.sub(r"<!--.*?-->\n?", "", "\n".join(lines[a + 1: b]), flags=re.S).strip()
    main_lines: list[str] = []
    for a, b in bounds:
        if lines[a].strip() in ("# Abstract", "# References", "# Data and code"):
            continue
        main_lines.extend(lines[a:b])
    reg = Reg()
    tg, tf = gap_table_spec(numbers), factorial_table_spec(numbers)
    main = "\n".join(main_lines)
    main = re.sub(r"<!-- table1:begin -->.*?<!-- table1:end -->", lambda m: "ZZBLOCKGAPZZ", main, flags=re.S)
    main = re.sub(r"<!-- table3:begin -->.*?<!-- table3:end -->", lambda m: "ZZBLOCKFACZZ", main, flags=re.S)
    main = re.sub(r"<!-- table4:begin -->.*?<!-- table4:end -->", lambda m: "ZZBLOCKCONZZ", main, flags=re.S)
    main = re.sub(r"<!-- table2:begin -->.*?<!-- table2:end -->", "", main, flags=re.S)
    main = re.sub(r"<!--.*?-->\n?", "", main, flags=re.S)
    has_fig = {k: (FIGS / v["file"]).exists() for k, v in FIGURES.items()}
    if not all(has_fig.values()):
        die("journal build needs every figure file: " + ", ".join(k for k, v in has_fig.items() if not v))
    main, fig_order, figs_unplaced = place_figures(main, has_fig)
    if fig_order != sorted(fig_order, key=lambda f: FIGURES[f]["number"]):
        die("figures must appear in number order in the journal build: " + ", ".join(fig_order))
    tc = confirm_table_spec(numbers)
    blocks = {"ZZBLOCKGAPZZ": journal_table_tex(tg), "ZZBLOCKFACZZ": journal_table_tex(tf),
              "ZZBLOCKCONZZ": journal_table_tex(tc)}
    for fid, fig in FIGURES.items():
        blocks[f"ZZBLOCKF{fig['number']}ZZ"] = journal_figure_block(fid)
    for tag, latex in blocks.items():
        if tag not in main:
            die(f"journal build: block {tag} has no place in the text")
        main = main.replace(tag, reg.add(latex))
    main = journal_appendix_md(main, reg)
    abstract_tex = md_to_tex(abstract_md, reg, bibkeys)
    main_tex = md_to_tex(main, reg, bibkeys)
    decl_tex, decl_titles = [], []
    for src, fallback in DECLARATIONS:
        if src == "@data":
            title, body = fallback, data_md
        else:
            path = JOURNAL / src
            if not path.exists():
                die(f"declaration source missing: {path}")
            t = path.read_text(encoding="utf-8").strip().split("\n")
            title = t[0][2:].strip() if t and t[0].startswith("# ") else fallback
            body = "\n".join(t[1:] if t and t[0].startswith("# ") else t).strip()
        decl_titles.append(title)
        sec = [f"\\section*{{{tex_text(title)}}}", md_to_tex(body, reg, bibkeys)]
        if src in RED_DECLARATIONS:  # printed in red so the author can find and reword them before submission
            sec = ["{\\color{red}% RED: author rewords before submission"] + sec + ["}% end RED"]
        decl_tex += sec + [""]
    af = front["affiliation"]
    kv = ", ".join(f"{k}={{{tex_text(af[k])}}}" for k in ("organization", "addressline", "city", "state", "country")
                   if af.get(k))
    keywords = [k.strip() for k in meta["keywords"].split(";") if k.strip()]
    tex = "\n".join([
        journal_preamble(), "",
        "\\begin{document}", "",
        "\\begin{frontmatter}",
        f"\\title{{{tex_text(meta['title'])}}}",
        f"\\author[a]{{{tex_text(front['author'])}}}",
        "\\cortext[cor1]{Corresponding author.}",
        f"\\ead{{{front['email']}}}",
        f"\\affiliation[a]{{{kv}}}",
        "\\begin{abstract}", abstract_tex, "\\end{abstract}",
        "\\begin{keyword}", " \\sep ".join(tex_text(k) for k in keywords), "\\end{keyword}",
        "\\end{frontmatter}", "",
        "\\linenumbers", "",
        main_tex, "",
        "% Declarations, directly before the references (Applied Energy guide for authors)",
        "\n".join(decl_tex),
        "\\bibliographystyle{elsarticle-num}",
        "\\bibliography{refs}", "", "\\end{document}", ""])
    tex = tex.replace("\\author[a]{", "\\author[a]{", 1)
    # mark the corresponding author
    tex = re.sub(r"\\author\[a\]\{(.*?)\}\n\\cortext", lambda m: "\\author[a]{" + m.group(1) + "\\corref{cor1}}\n\\cortext",
                 tex, count=1)
    bad = sorted({c for c in tex if ord(c) > 127})
    if bad:
        die("non-ASCII characters left in the journal paper.tex: " + ", ".join(f"U+{ord(c):04X}" for c in bad))
    if "ZZPH" in tex or "ZZBLOCK" in tex:
        die("unexpanded placeholder in the journal paper.tex")
    tex = re.sub(r"(\{\[\}(?:\$-\$)?\d+\.\d+),\s+((?:\$-\$)?\d+\.\d+\{\]\})", r"\1,~\2", tex)
    tex = re.sub(r"(\d) \{\[\}((?:\$-\$)?\d+\.\d+,~)", r"\1~{[}\2", tex)
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "paper.tex").write_text(tex, encoding="utf-8")
    (BUILD / "refs.bib").write_text("".join(journal_bib_entry(e) + "\n" for e in refs), encoding="utf-8")
    for fid in FIGURES:
        shutil.copy(FIGS / FIGURES[fid]["file"], BUILD / journal_fig_name(fid))
    t_out = {name: {"keys": spec_keys(sp), "header": table_header_tex(sp), "rows": table_rows_tex(sp),
                    "caption": sp["caption"]} for name, sp in (("table1", tg), ("table3", tf), ("table4", tc))}
    (BUILD / "tables.json").write_text(json.dumps(t_out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    jmeta = {"title": meta["title"], "keywords": keywords, "declarations": decl_titles,
             "figures": {fid: journal_fig_name(fid) for fid in FIGURES}, "abstract_md": abstract_md,
             "references": [r["key"] for r in refs], "tags": {r["key"]: r["tag"] for r in refs if r.get("tag")}}
    (BUILD / "journal_meta.json").write_text(json.dumps(jmeta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"tex (journal): wrote {BUILD / 'paper.tex'} and {BUILD / 'refs.bib'} ({len(refs)} entries); "
          f"figures {', '.join(journal_fig_name(f) for f in fig_order)}; declarations: {', '.join(decl_titles)}")
    return {"figs_missing": [], "figs_unplaced": figs_unplaced, "layers_todo": False,
            "ref_flags": [{"key": e["key"], "flags": e["flags"], "inferred": e["inferred"]} for e in refs
                          if e["flags"] or e["inferred"]]}


def tag_bbl(bbl: str, tags: dict) -> str:
    """Elsevier tags datasets and software: '[dataset]' or '[software]' at the start of the reference."""
    for key, tag in tags.items():
        bbl, n = re.subn(r"(\\bibitem\{" + re.escape(key) + r"\}\n)", lambda m: m.group(1) + f"[{tag}] ", bbl)
        if n != 1:
            die(f"bibitem {key} not found once in paper.bbl (found {n})")
    return bbl


def run_latex(cwd: Path, steps: list[list[str]], log_name: str) -> None:
    log = []
    for cmd in steps:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        log.append(" ".join(cmd) + "\n" + r.stdout[-4000:] + r.stderr[-2000:])
        if r.returncode != 0:
            (BUILD / log_name).write_text("\n\n".join(log), encoding="utf-8")
            print(log[-1][-3000:])
            die(f"{cmd[0]} failed in {cwd}")
    (BUILD / log_name).write_text("\n\n".join(log), encoding="utf-8")


def stage_pdf_journal() -> dict:
    tex = BUILD / "paper.tex"
    if not tex.exists():
        die("paper.tex missing; run the tex stage first")
    jmeta = json.loads((BUILD / "journal_meta.json").read_text(encoding="utf-8"))
    sub = BUILD / "latex"
    sub.mkdir(parents=True, exist_ok=True)
    for f in [tex, BUILD / "refs.bib"] + [BUILD / n for n in jmeta["figures"].values()]:
        shutil.copy(f, sub / f.name)
    pdfl = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"]
    run_latex(sub, [pdfl, ["bibtex", "paper"]], "pdflatex_stdout.txt")
    bbl = sub / "paper.bbl"
    bbl.write_text(tag_bbl(bbl.read_text(encoding="utf-8"), jmeta["tags"]), encoding="utf-8")
    run_latex(sub, [pdfl, pdfl, pdfl], "pdflatex_stdout_2.txt")
    for ext in ("pdf", "log", "bbl", "blg"):
        shutil.copy(sub / f"paper.{ext}", BUILD / f"paper.{ext}")
    print(f"pdf (journal): wrote {BUILD / 'paper.pdf'} (elsarticle, pdflatex + bibtex elsarticle-num, tagged bbl)")
    return {}


def fill_template(text: str, numbers: dict, subs: dict, uses: list, name: str) -> str:
    for k, v in subs.items():
        text = text.replace(f"%%{k}%%", v)
    left = re.findall(r"%%[A-Z_]+%%", text)
    if left:
        die(f"{name}: unknown template fields {left}")

    def sub(m):
        key, mode = m.group(1), m.group(2)
        if key not in numbers:
            die(f"{name}: key {key} missing from the numbers files")
        e = numbers[key]
        s = str(int(round(e["value"]))) if mode == "i" else fmt(e["value"]) if mode == "v" else fmt_full(e)
        uses.append({"file": name, "key": key, "mode": {"i": "i", "v": "v"}.get(mode, "full"), "text": s})
        return s

    return NUM_REF_RE.sub(sub, text)


def fill_side_files(numbers_path: Path) -> dict:
    """Title page, cover letter, highlights (txt and docx), data availability and graphical abstract in SIDE."""
    SIDE.mkdir(parents=True, exist_ok=True)
    numbers = load_numbers(numbers_path)
    filled = (BUILD / "note_filled.md").read_text(encoding="utf-8")
    meta, fm = split_front_matter(filled)
    front = load_front()
    af = front["affiliation"]
    subs = {"TITLE": meta["title"], "KEYWORDS": "; ".join(k.strip() for k in meta["keywords"].split(";") if k.strip()),
            "AUTHOR": front["author"], "EMAIL": front["email"], "EMAIL_STATUS": front.get("email_status", ""),
            "ORGANIZATION": af["organization"], "ADDRESSLINE": af.get("addressline", ""), "CITY": af.get("city", ""),
            "STATE": af.get("state", ""), "COUNTRY": af.get("country", "")}
    uses: list = []
    written = []
    for src, out in (("title_page.md", "title_page.md"), ("cover_letter.md", "cover_letter.md"),
                     ("highlights.md", "highlights.txt")):
        text = fill_template((JOURNAL_TEMPLATES / src).read_text(encoding="utf-8"), numbers, subs, uses, out)
        (SIDE / out).write_text(text, encoding="utf-8")
        written.append(out)
    lines = filled.split("\n")[len(fm):]
    titles, _ = section_bodies(lines)
    a, b = titles["Data and code"]
    body = re.sub(r"<!--.*?-->\n?", "", "\n".join(lines[a + 1: b]), flags=re.S).strip()
    body = CITE_RE.sub("", body).replace(" .", ".")
    (SIDE / "data_availability.md").write_text(
        "# Data availability\n\n<!-- Generated by paper/build.py --profile journal from the 'Data and code' section of "
        "paper/note.md. Edit note.md, not this file. -->\n\n" + body + "\n", encoding="utf-8")
    written.append("data_availability.md")
    pandoc = shutil.which("pandoc") or next((str(Path(d) / "pandoc") for d in BIN_DIRS if (Path(d) / "pandoc").exists()), None)
    if pandoc:
        hl = (SIDE / "highlights.txt").read_text(encoding="utf-8").strip().split("\n")
        md = "# Highlights\n\n" + "\n".join(f"- {h}" for h in hl) + "\n"
        r = subprocess.run([pandoc, "-f", "markdown", "-o", str(SIDE / "highlights.docx")], input=md, text=True,
                           capture_output=True)
        if r.returncode == 0:
            written.append("highlights.docx")
    (BUILD / "side_numbers_used.json").write_text(json.dumps({"uses": uses}, indent=1, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    ga = Path(__file__).resolve().parent.parent / "scripts" / "make_graphical_abstract.py"
    r = subprocess.run([sys.executable, str(ga), "--out", str(SIDE)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        die("graphical abstract script failed")
    written += ["graphical_abstract.pdf", "graphical_abstract.png"]
    print(f"side files: wrote {', '.join(written)} in {SIDE}; {len(uses)} numbers filled")
    return {"written": written}


def make_journal_zip() -> dict:
    """paper/build_journal/upload/: exactly the LaTeX files to upload (tex, bbl, figures) and a zip of them beside
    it; then compile the zip's content alone in a fresh temp dir (pdflatex twice, the bbl already holds the
    references)."""
    import tempfile
    import zipfile
    jmeta = json.loads((BUILD / "journal_meta.json").read_text(encoding="utf-8"))
    files = ["paper.tex", "paper.bbl"] + sorted(jmeta["figures"].values())
    up = BUILD / "upload"
    up.mkdir(parents=True, exist_ok=True)
    stale = sorted(p.name for p in up.iterdir() if p.name not in files)
    if stale:
        die(f"upload folder holds files that are not part of the package: {stale}; move them out first")
    for f in files:
        shutil.copy(BUILD / f, up / f)
    zpath = BUILD / UPLOAD_ZIP
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(up / f, arcname=f)
    tmp = Path(tempfile.mkdtemp(prefix="paperE_upload_check_"))
    with zipfile.ZipFile(zpath) as z:
        z.extractall(tmp)
    log = []
    ok = True
    for _ in range(2):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"], cwd=tmp,
                           capture_output=True, text=True)
        log.append(r.stdout[-2000:])
        ok = ok and r.returncode == 0
    lg = (tmp / "paper.log").read_text(encoding="utf-8", errors="replace") if (tmp / "paper.log").exists() else ""
    undefined = re.findall(r"(?:Citation|Reference) `[^']*' .*undefined", lg)
    missing_files = re.findall(r"File `([^']*)' not found", lg)
    pages = None
    if shutil.which("pdfinfo") and (tmp / "paper.pdf").exists():
        info = subprocess.run(["pdfinfo", str(tmp / "paper.pdf")], capture_output=True, text=True).stdout
        m = re.search(r"^Pages:\s+(\d+)", info, re.M)
        pages = int(m.group(1)) if m else None
    res = {"files": files, "zip": str(zpath), "temp_dir": str(tmp), "compiled": ok and (tmp / "paper.pdf").exists(),
           "undefined": undefined, "missing_files": missing_files, "pages": pages,
           "zip_sha256": __import__("hashlib").sha256(zpath.read_bytes()).hexdigest()}
    (BUILD / "upload_check.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(f"zip: {len(files)} files in {up}, zip {zpath.name}; compiled alone in {tmp}: "
          f"{'ok' if res['compiled'] and not undefined and not missing_files else 'FAILED'} ({pages} pages)")
    if not res["compiled"] or undefined or missing_files:
        die("the upload package does not compile alone: " + "; ".join(undefined + missing_files))
    return res


# --------------------------------------------------------------------------- main

def strict_failures(fill_info: dict | None, tex_info: dict | None) -> list[str]:
    out = []
    if fill_info:
        out += [f"TODO line {t['line']}: {t['text']}" for t in fill_info["todos"]]
    if tex_info:
        out += [f"figure missing: {f}" for f in tex_info["figs_missing"]]
        out += [f"figure not placed in the text: {f}" for f in tex_info["figs_unplaced"]]
        if tex_info["layers_todo"]:
            out.append("Table 2 not generated (no usable layers/ keys)")
        out += [f"reference {r['key']}: {r['flags']}" for r in tex_info["ref_flags"] if r["flags"]]
    return out


def main(argv=None):
    global NOTE, BUILD, SIDE
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--numbers", type=Path, default=argparse.SUPPRESS,
                        help=f"numbers JSON (default {DEFAULT_NUMBERS})")
    common.add_argument("--note", type=Path, default=argparse.SUPPRESS,
                        help=f"source note (default {NOTE})")
    common.add_argument("--build", type=Path, default=argparse.SUPPRESS,
                        help=f"build folder (default {BUILD})")
    common.add_argument("--strict", action="store_true", default=argparse.SUPPRESS,
                        help="fail if any TODO, missing figure, missing Table 2 or flagged reference remains")
    common.add_argument("--profile", choices=("aaai", "journal"), default=argparse.SUPPRESS,
                        help="aaai (default): the AAAI-27 workshop build; journal: the Applied Energy elsarticle package")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fill", "tex", "pdf", "all", "zip"):
        sub.add_parser(name, parents=[common])
    args = ap.parse_args(argv)
    profile = getattr(args, "profile", "aaai")
    NOTE = getattr(args, "note", NOTE).resolve()
    BUILD = getattr(args, "build", JOURNAL_BUILD if profile == "journal" else BUILD).resolve()
    if profile == "journal":
        SIDE = JOURNAL if BUILD == JOURNAL_BUILD.resolve() else BUILD / "journal"
    numbers_path = getattr(args, "numbers", DEFAULT_NUMBERS)
    strict = getattr(args, "strict", False)
    fill_info = tex_info = None
    if profile == "journal":
        if args.cmd in ("fill", "all"):
            fill_info = stage_fill(numbers_path, strict)
        if args.cmd in ("tex", "all"):
            tex_info = stage_tex_journal(numbers_path, strict)
            fill_side_files(numbers_path)
            if fill_info is None:
                fill_info = {"todos": json.loads((BUILD / "todos.json").read_text(encoding="utf-8"))}
        if args.cmd in ("pdf", "all"):
            stage_pdf_journal()
        if args.cmd in ("zip", "all"):
            make_journal_zip()
        if strict:
            fails = strict_failures(fill_info, tex_info)
            if fails:
                print(f"--strict: {len(fails)} unresolved item(s):", file=sys.stderr)
                for f in fails:
                    print("   " + f, file=sys.stderr)
                sys.exit(2)
            print("--strict: nothing unresolved")
        return
    if args.cmd == "zip":
        die("zip is a journal step: use --profile journal")
    if args.cmd in ("fill", "all"):
        fill_info = stage_fill(numbers_path, strict)
    if args.cmd in ("tex", "all"):
        tex_info = stage_tex(numbers_path, strict)
        if fill_info is None:
            fill_info = {"todos": json.loads((BUILD / "todos.json").read_text(encoding="utf-8"))}
    if args.cmd in ("pdf", "all"):
        stage_pdf()
    if strict:
        fails = strict_failures(fill_info, tex_info)
        if fails:
            print(f"--strict: {len(fails)} unresolved item(s):", file=sys.stderr)
            for f in fails:
                print("   " + f, file=sys.stderr)
            sys.exit(2)
        print("--strict: nothing unresolved")


if __name__ == "__main__":
    main()
