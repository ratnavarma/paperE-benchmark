#!/usr/bin/env python3
"""Checks for the built manuscript (standard library only).

    uv run python paper/check.py [--numbers PATH] [--note PATH] [--build DIR] [--limit 7] [--strict]

Written independently of build.py: number formatting and the table cells are recomputed here
from the numbers JSON, then compared with what build.py wrote.

(a) filled numbers round-trip against the JSON and numbers_used.json
(b) table rows in paper.tex come verbatim from the generator and match an independent recomputation
(c) every filled number string appears in the PDF text
(d) page count and pages before the References heading
(e) no identity strings in PDF text, tex, bib or metadata
(f) no em dash in note_filled.md, paper.tex or refs.bib
(g) kit rules: DO NOT CHANGE lines, banned packages and commands, no Type 3 fonts, LaTeX log
(h) leftover TODO placeholders and missing figures (a failure only with --strict)
(i) the five figures: files present, vector with embedded non-Type-3 fonts, no remote links or identity
    strings, each placed once in paper.tex in number order, each cited in the text (placement and
    citation gaps fail only with --strict)

Optional --note PATH and --build DIR check a scratch note and build folder instead of the real ones.

--profile journal checks the Applied Energy package (paper/build_journal) instead: a to c as above plus the
factorial table (b2); d page count reported, no limit; e employer and client strings only (the journal review is
single-anonymized); f em dash in every journal file; g fonts embedded, LaTeX errors, overfull boxes fail;
h placeholders (TO FILL marks warn, fail with --strict); i figures as separate vector files; j abstract at most
250 words without citations; k 1 to 7 keywords without 'and'/'of'; l highlights 3 to 5 lines of at most 85
characters; m references resolved, in order of first citation, shortened last pages, at most six authors;
n numbered sections, appendices, declarations before the references; o SI units; p upload package compiles
alone; q side files equal an independent fill and carry the one title; r graphical abstract size and fonts.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

PAPER = Path(__file__).resolve().parent
BUILD = PAPER / "build"
KIT = PAPER / "kit"
DEFAULT_NUMBERS = Path(__file__).resolve().parent.parent / "results" / "paper_numbers.json"
EXTRA_NUMBERS = ("posthoc_oblivious_share.json", "g2_numbers.json", "posthoc_g3_runs.json", "confirm_paper_numbers.json",
                 "posthoc_applied_energy.json", "posthoc_ranker.json", "posthoc_fla.json",
                 "diag_cellf_delay.json")
LEAK = ["Ratnavarma", "Varma", "ratnavarma", "/Users/", "paperE-benchmark", "@gmail"]
EMPLOYER_CLIENT: list = []
# Further identity strings load from paper/identity_private.txt (git-ignored, one per line, blank lines and
# "#" comments ignored). A line starting with "employer:" is also checked as an employer or client string.
# Trailing spaces on a line are kept, so a string such as "ABC " can match a whole word.
PRIVATE_IDENTITY = Path(__file__).resolve().parent / "identity_private.txt"
HAVE_PRIVATE_IDENTITY = PRIVATE_IDENTITY.exists()
if HAVE_PRIVATE_IDENTITY:
    for _ln in PRIVATE_IDENTITY.read_text(encoding="utf-8").split("\n"):
        _ln = _ln.rstrip("\r")
        if not _ln.strip() or _ln.lstrip().startswith("#"):
            continue
        if _ln.startswith("employer:"):
            _ln = _ln[len("employer:"):]
            if _ln not in EMPLOYER_CLIENT:
                EMPLOYER_CLIENT.append(_ln)
        if _ln not in LEAK:
            LEAK.append(_ln)
# Applied Energy review is single-anonymized (PGAI4E, the double-blind target, was dropped 2026-11-02), so the
# public code repository may be named. Only this exact URL is exempt from the identity check; any other
# occurrence of a LEAK string still fails. Whitespace or a line-break hyphen inside the URL (PDF text) is allowed.
PUBLIC_URLS = ["https://github.com/ratnavarma/paperE-benchmark"]
# In two-column PDF text a line break inside the URL can put text from the other column between its halves,
# so the part after the last hyphen ("benchmark") may be missing from the match.
def _url_pattern(u: str) -> re.Pattern:
    head, _, tail = u.rpartition("-")
    body = "".join(re.escape(c) + (r"\s*" if c in "/.:-" else "") for c in head)
    return re.compile(body + r"-?(?:\s*" + re.escape(tail) + ")?")


ALLOWED_PUBLIC = [_url_pattern(u) for u in PUBLIC_URLS]
EM = "\u2014"
# figure id -> (file, number), as in build.py FIGURES; kept here so the check is independent of build.py
FIGURES = {"fig_setting": ("fig_setting.pdf", 1), "fig_window": ("fig_window.pdf", 2),
           "fig_ladder": ("fig_ladder.pdf", 4), "fig_layers": ("fig_layers.pdf", 3),
           "fig_e3": ("fig_e3.pdf", 5)}
NOTE = PAPER / "note.md"


def refs_bib() -> Path:
    """The bib build.py wrote: the build folder's copy (a --build folder has no other), else paper/refs.bib."""
    return BUILD / "refs.bib" if (BUILD / "refs.bib").exists() else PAPER / "refs.bib"


results: list[tuple[str, str, str]] = []


def rec(status: str, name: str, detail: str = ""):
    results.append((status, name, detail))
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))


def bin_path(name: str) -> str | None:
    p = shutil.which(name)
    if p:
        return p
    for d in ("/opt/homebrew/bin", "/usr/local/bin"):
        if (Path(d) / name).exists():
            return str(Path(d) / name)
    return None


# ----------------------------------------------------------------------------- independent formatting

def two_dp(x: float) -> str:
    """Snap to 9 decimals (removes float noise), then round once, half away from zero (Fraction arithmetic),
    U+2212 for a negative. Same rule as build.py fmt, written independently."""
    cents = math.floor(Fraction(round(Fraction(abs(x)), 9)) * 100 + Fraction(1, 2))
    s = f"{cents // 100}.{cents % 100:02d}"
    return ("\u2212" if x < 0 and cents else "") + s


def printed(e: dict, value_only: bool) -> str:
    if value_only or e.get("ci_lo") is None or e.get("ci_hi") is None:
        return two_dp(e["value"])
    return f"{two_dp(e['value'])} [{two_dp(e['ci_lo'])}, {two_dp(e['ci_hi'])}]"


def norm(s: str) -> str:
    s = s.replace("\u2212", "-").replace("\u2013", "-").replace("\u00ad", "")
    return re.sub(r"\s+", " ", s)


# ----------------------------------------------------------------------------- note parsing

NUM_REF = re.compile(r"\{\{\s*([^{}|]+?)\s*(?:\|\s*(v|i)\s*)?\}\}")


def body_lines(lines: list[str]):
    """Yield (i, line, skip) with skip True for front matter and HTML comment lines."""
    i = 0
    if lines and lines[0].strip() == "---":
        j = next(k for k in range(1, len(lines)) if lines[k].strip() == "---")
        for k in range(0, j + 1):
            yield k, lines[k], True
        i = j + 1
    in_c = False
    for k in range(i, len(lines)):
        ln = lines[k]
        starts = "<!--" in ln
        if starts and "-->" not in ln.split("<!--", 1)[1]:
            in_c = True
        skip = in_c or starts
        if in_c and "-->" in ln:
            in_c = False
        yield k, ln, skip


def expected_fill(note_text: str, numbers: dict):
    out, uses = [], {}
    for _, ln, skip in body_lines(note_text.split("\n")):
        if skip:
            out.append(ln)
            continue

        def sub(m):
            k, mode = m.group(1), m.group(2)
            if k not in numbers:
                raise KeyError(k)
            if mode == "i":
                s = str(int(round(numbers[k]["value"])))
            else:
                s = printed(numbers[k], bool(mode))
            uses.setdefault(k, []).append(({"i": "i", "v": "v"}.get(mode, "full"), s))
            return s

        out.append(NUM_REF.sub(sub, ln))
    return out, uses


def gap_expected(numbers: dict):
    rows, cells = [], []
    blocks = [(lab, lambda rho, d, pol=pol: f"cell/F0R_M3_dA{d}_db0_rho{rho}_r0.3/{pol}/R_avoid_kwh_per100")
              for lab, pol in (("CE-LLF", "ce_llf"), ("Shared-rate MPC", "pop_mpc"),
                               ("Targeted MPC", "guarded_mpc_e1"))]
    blocks += [("Targeted MPC gap", lambda rho, d: f"e1/primary/M3_rho{rho}/gap_dA{d}"),
               ("Oracle gap", lambda rho, d: f"e1/primary/M3_rho{rho}/oracle_gap_dA{d}")]
    for label, keyf in blocks:
        for i, rho in enumerate(("0.95", "1.15")):
            cs = []
            for d in (0, 1, 2, 4):
                k = keyf(rho, d)
                cs.append(printed(numbers[k], False))
                cells.append((k, cs[-1]))
            rows.append((label if i == 0 else "", rho, cs))
    tex_rows = [" & ".join([a, b] + [c.replace("\u2212", "$-$") for c in cs]) + " \\\\" for a, b, cs in rows]
    md_rows = ["| " + " | ".join([a, b] + cs) + " |" for a, b, cs in rows]
    return tex_rows, md_rows, cells


def layers_expected(numbers: dict):
    """Table 2 (layers, M = 3, delta in 0, 1, 2, 4), recomputed from layers/M3_rho{rho}/dA{d}/{step}."""
    rows, cells = [], []
    for step, label in (("planning", "Planning"), ("hedging", "Shared-rate hedging"),
                        ("targeting", "Targeting"), ("total", "Total")):
        for i, rho in enumerate(("0.95", "1.15")):
            cs = []
            for d in (0, 1, 2, 4):
                k = f"layers/M3_rho{rho}/dA{d}/{step}"
                if k not in numbers:
                    return None
                cs.append(printed(numbers[k], False))
                cells.append((k, cs[-1]))
            rows.append((label if i == 0 else "", rho, cs))
    tex_rows = [" & ".join([a, b] + [c.replace("\u2212", "$-$") for c in cs]) + " \\\\" for a, b, cs in rows]
    md_rows = ["| " + " | ".join([a, b] + cs) + " |" for a, b, cs in rows]
    return tex_rows, md_rows, cells


# ----------------------------------------------------------------------------- checks

def check_a(numbers: dict, note_text: str):
    filled_path = BUILD / "note_filled.md"
    used_path = BUILD / "numbers_used.json"
    if not filled_path.exists() or not used_path.exists():
        rec("FAIL", "a. fill round-trip", "note_filled.md or numbers_used.json missing")
        return None
    filled = filled_path.read_text(encoding="utf-8")
    used = json.loads(used_path.read_text(encoding="utf-8"))["keys"]
    exp_lines, exp_uses = expected_fill(note_text, numbers)
    # drop generated table blocks from the filled text
    stripped = re.sub(r"<!-- (table\d):begin -->.*?<!-- \1:end -->\n?", "", filled, flags=re.S)
    has_t1 = "<!-- table2:begin -->" in filled
    got = stripped.split("\n")
    if has_t1:
        exp_lines = [ln for ln in exp_lines if not ln.startswith("[[LAYERS:")]
    # [[TABLE: gap|factorial]] marker lines are consumed by the build (replaced by the table block)
    exp_lines = [ln for ln in exp_lines if not re.fullmatch(r"\[\[TABLE:\s*(gap|factorial|confirm)\s*\]\]", ln.strip())]
    # the generator puts blank lines around its blocks; compare with runs of blank lines collapsed
    def canon(t: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", t)

    exp_text, got_text = canon("\n".join(exp_lines)), canon("\n".join(got))
    if got_text != exp_text:
        a, b = got_text.split("\n"), exp_text.split("\n")
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                rec("FAIL", "a. fill round-trip", f"line {i + 1} differs\n  got: {x[:160]}\n  exp: {y[:160]}")
                break
        else:
            rec("FAIL", "a. fill round-trip", f"line counts differ {len(a)} vs {len(b)}")
        return used
    bad = []
    for k, ex in exp_uses.items():
        rec_k = used.get(k)
        if not rec_k:
            bad.append(f"{k} not in numbers_used.json")
            continue
        e = numbers[k]
        for f in ("value", "ci_lo", "ci_hi"):
            if rec_k[f] != e.get(f):
                bad.append(f"{k}.{f} differs from JSON")
        have = [(u["mode"], u["text"]) for u in rec_k["uses"] if u["mode"] != "table"]
        if sorted(have) != sorted(ex):
            bad.append(f"{k} uses differ")
    t2_tex, t2_md, t2_cells = gap_expected(numbers)
    lay = layers_expected(numbers) if has_t1 else None
    lay_cells = lay[2] if lay else []
    if has_t1 and lay is None:
        bad.append("layers table present but a layers/ key it needs is missing from the JSON")
    for k, txt in t2_cells + lay_cells:
        if k not in used or ("table", txt) not in [(u["mode"], u["text"]) for u in used[k]["uses"]]:
            bad.append(f"table cell {k} missing or different in numbers_used.json")
    for r in t2_md:
        if r not in filled:
            bad.append(f"table 1 (gap) row not in note_filled.md: {r[:80]}")
    for r in (lay[1] if lay else []):
        if r not in filled:
            bad.append(f"table 2 (layers) row not in note_filled.md: {r[:80]}")
    for _, ln, skip in body_lines(filled.split("\n")):
        if not skip and "{{" in ln:
            bad.append(f"unfilled placeholder: {ln[:80]}")
    n_uses = sum(len(v) for v in exp_uses.values())
    if bad:
        rec("FAIL", "a. fill round-trip", "; ".join(bad[:6]))
    else:
        rec("PASS", "a. fill round-trip",
            f"{n_uses} placeholders and {len(t2_cells)} gap-table and {len(lay_cells)} layers-table cells recomputed from the JSON match note_filled.md; "
            f"{len(used)} keys match numbers_used.json")
    return used


def check_b(numbers: dict):
    tex_path, tj_path = BUILD / "paper.tex", BUILD / "tables.json"
    if not tex_path.exists() or not tj_path.exists():
        rec("FAIL", "b. table rows", "paper.tex or tables.json missing")
        return
    tex = tex_path.read_text(encoding="utf-8")
    tj = json.loads(tj_path.read_text(encoding="utf-8"))
    gen_rows = {r for t in tj.values() for r in t["rows"]} | {t["header"] for t in tj.values()}
    tex_lines = set(tex.split("\n"))
    problems = []
    for name, t in tj.items():
        for r in t["rows"] + [t["header"]]:
            if r not in tex_lines:
                problems.append(f"{name}: row not found verbatim in paper.tex: {r[:70]}")
    in_tab, tab_rows = False, []
    for ln in tex.split("\n"):
        if ln.startswith("\\begin{tabular}"):
            in_tab = True
        elif ln.startswith("\\end{tabular}"):
            in_tab = False
        elif in_tab and "&" in ln:
            tab_rows.append(ln)
    for r in tab_rows:
        if r not in gen_rows:
            problems.append(f"tabular row not from the generator: {r[:70]}")
    exp_tex, _, _ = gap_expected(numbers)
    if tj["table1"]["rows"] != exp_tex:
        problems.append("table 1 (gap) rows differ from the independent recomputation")
    lay = layers_expected(numbers)
    if "table2" in tj:
        if lay is None:
            problems.append("table 2 (layers) generated but a layers/ key is missing from the JSON")
        elif tj["table2"]["rows"] != lay[0]:
            problems.append("table 2 (layers) rows differ from the independent recomputation")
    # no table2 entry: Table 2 is not placed in note.md (Figure 3 plots the same split), so nothing to check
    if problems:
        rec("FAIL", "b. table rows", "; ".join(problems[:5]))
    else:
        rec("PASS", "b. table rows",
            f"{len(tab_rows)} tabular rows in paper.tex all from the generator; table 1 (and table 2 when placed) equal an independent recomputation")


def pdf_text(pdf: Path):
    exe = bin_path("pdftotext")
    if not exe:
        return None, None
    raw = subprocess.run([exe, str(pdf), "-"], capture_output=True, text=True).stdout.replace("\u00a0", " ")
    lay = subprocess.run([exe, "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.replace("\u00a0", " ")
    return raw, lay


def check_c(used, raw, lay):
    if used is None or raw is None:
        rec("FAIL", "c. numbers in PDF text", "no PDF text or no numbers_used.json")
        return
    hay_raw, hay_lay = norm(raw), norm(lay)
    missing, weak = [], 0
    total = 0
    for k, r in used.items():
        for u in r["uses"]:
            total += 1
            s = norm(u["text"])
            pat = re.compile(r"(?<![\d.])" + re.escape(s) + r"(?!\d)")
            if pat.search(hay_raw) or pat.search(hay_lay):
                continue
            nums = re.findall(r"-?\d+\.\d\d", s)
            if u["mode"] == "table" and all(re.search(r"(?<![\d.])" + re.escape(n) + r"(?!\d)", hay_lay) for n in nums):
                weak += 1
                continue
            missing.append(f"{k} [{u['mode']}] {u['text']}")
    if missing:
        rec("FAIL", "c. numbers in PDF text", f"{len(missing)} of {total} not found: " + "; ".join(missing[:5]))
    else:
        rec("PASS", "c. numbers in PDF text",
            f"all {total} filled strings found in the PDF text" + (f" ({weak} table cells matched number by number)" if weak else ""))


def check_d(pdf: Path, limit: int):
    exe = bin_path("pdfinfo")
    if not exe:
        rec("FAIL", "d. page count", "pdfinfo not available")
        return
    info = subprocess.run([exe, str(pdf)], capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    txt = bin_path("pdftotext")
    ref_page, body_pages = None, None
    for p in range(1, pages + 1):
        t = subprocess.run([txt, "-f", str(p), "-l", str(p), str(pdf), "-"], capture_output=True, text=True).stdout
        lines = [x.strip() for x in t.split("\n")]
        if "References" in lines:
            ref_page = p
            before = [x for x in lines[: lines.index("References")] if x]
            body_pages = p if before else p - 1
            break
    detail = f"{pages} pages in total"
    if ref_page is None:
        rec("FAIL", "d. page count", detail + "; no References heading found")
        return
    detail += f"; References heading on page {ref_page}; body occupies {body_pages} page(s) (limit {limit})"
    rec("PASS" if body_pages <= limit else "FAIL", "d. page count", detail)


def check_e(raw, lay, pdf: Path):
    targets = {"PDF text": (raw or "") + "\n" + (lay or ""), "paper.tex": (BUILD / "paper.tex").read_text(encoding="utf-8"),
               "refs.bib": refs_bib().read_text(encoding="utf-8"),
               "note_filled.md": (BUILD / "note_filled.md").read_text(encoding="utf-8")}
    hits = []
    allowed_n = 0
    for name, text in list(targets.items()):
        for pat in ALLOWED_PUBLIC:
            text, n = pat.subn("<public repository>", text)
            allowed_n += n
        targets[name] = text
    for name, text in targets.items():
        flat = re.sub(r"\s+", " ", text)
        for s in LEAK:
            if s in text or s in flat:
                hits.append(f"{s!r} in {name}")
    meta = ""
    exe = bin_path("pdfinfo")
    if exe:
        meta = subprocess.run([exe, "-meta", str(pdf)], capture_output=True, text=True).stdout
        info = subprocess.run([exe, str(pdf)], capture_output=True, text=True).stdout
        for s in LEAK:
            if s in meta or s in info:
                hits.append(f"{s!r} in PDF metadata")
        for field in ("Author", "Title", "Subject", "Keywords"):
            m = re.search(rf"^{field}:\s*(.+)$", info, re.M)
            if m and m.group(1).strip():
                hits.append(f"PDF metadata {field} is set: {m.group(1).strip()[:60]}")
    if hits:
        rec("FAIL", "e. identity leakage", "; ".join(hits))
    else:
        rec("PASS", "e. identity leakage",
            f"none of {len(LEAK)} strings in PDF text, tex, bib or note_filled.md "
            f"(public repository URL exempt, {allowed_n} occurrence(s)); "
            + ("PDF metadata has no Author, Title, Subject or Keywords" if exe else "pdfinfo unavailable"))


def check_f():
    hits = []
    for name, p in (("note_filled.md", BUILD / "note_filled.md"), ("paper.tex", BUILD / "paper.tex"),
                    ("refs.bib", refs_bib())):
        t = p.read_text(encoding="utf-8")
        if EM in t:
            hits.append(f"U+2014 in {name} (line {t[:t.index(EM)].count(chr(10)) + 1})")
    tex = (BUILD / "paper.tex").read_text(encoding="utf-8")
    if "\\textemdash" in tex or re.search(r"(?<!-)---(?!-)", tex):
        hits.append("LaTeX em dash (--- or \\textemdash) in paper.tex")
    note = NOTE.read_text(encoding="utf-8")
    if EM in note:
        hits.append("U+2014 in note.md itself")
    rec("FAIL" if hits else "PASS", "f. em dash", "; ".join(hits) if hits else "none in note_filled.md, paper.tex, refs.bib or note.md")


BANNED_PKGS = ["authblk", "balance", "CJK", "float", "flushend", "fullpage", "geometry", "hyperref", "navigator",
               "indentfirst", "layout", "multicol", "nameref", "savetrees", "setspace", "stfloats", "tabu",
               "titlesec", "tocbibind", "ulem", "wrapfig", "babel", "epsf", "epsfig", "euler", "lmodern",
               "pdfcomment", "pgfplots", "psfig", "pstricks", "t1enc", "times", "bbm"]
BANNED_CMDS = [r"\\nocopyright", r"\\addtolength", r"\\balance", r"\\baselinestretch", r"\\clearpage", r"\\columnsep",
               r"\\newpage", r"\\pagebreak", r"\\pagestyle", r"\\tiny", r"\\vspace\s*\{\s*-", r"\\vskip\s*-",
               r"\\vskip\s*\{\s*-", r"\\linespread", r"\\topmargin", r"\\textheight", r"\\textwidth", r"\\resizebox",
               r"\\abovecaption", r"\\belowcaption", r"\\clip", r"\\trim", r"\\break\b", r"\\float\b"]


def check_g(pdf: Path, strict: bool):
    tex = (BUILD / "paper.tex").read_text(encoding="utf-8")
    tpl = (KIT / "AnonymousSubmission2027.tex").read_text(encoding="utf-8").split("\n")
    keep = [ln for ln in tpl[:13] if "DO NOT CHANGE" in ln]
    missing = [ln for ln in keep if ln not in tex.split("\n")]
    rec("FAIL" if missing else "PASS", "g1. template DO NOT CHANGE lines",
        f"missing: {missing}" if missing else f"all {len(keep)} lines present verbatim")
    bad = [p for p in BANNED_PKGS if re.search(r"\\usepackage(\[[^\]]*\])?\{[^}]*\b" + re.escape(p) + r"\b[^}]*\}", tex)]
    bad += [c for c in BANNED_CMDS if re.search(c, tex)]
    for m in re.finditer(r"\\setlength\{([^}]*)\}", tex):
        if m.group(1) != "\\tabcolsep":
            bad.append("\\setlength" + m.group(0))
    rec("FAIL" if bad else "PASS", "g2. banned packages and commands", ", ".join(bad) if bad else "none found in paper.tex")
    fonts = bin_path("pdffonts")
    if fonts:
        out = subprocess.run([fonts, str(pdf)], capture_output=True, text=True).stdout
        t3 = [ln for ln in out.split("\n") if "Type 3" in ln]
        rec("FAIL" if t3 else "PASS", "g3. Type 3 fonts", f"{len(t3)} Type 3 font(s)" if t3 else
            "none; all fonts embedded" if not re.search(r"\bno\b\s+(no|yes)\s", out) else "none, but some fonts are not embedded")
    else:
        rec("WARN", "g3. Type 3 fonts", "pdffonts not available")
    log = BUILD / "paper.log"
    if not log.exists():
        rec("FAIL", "g4. LaTeX log", "paper.log missing")
        return
    lg = log.read_text(encoding="utf-8", errors="replace")
    errors = re.findall(r"^! .*$", lg, re.M)
    undefined = re.findall(r"(?:Citation|Reference) `[^']*' .*undefined.*", lg)
    overfull = re.findall(r"Overfull \\[hv]box.*?lines? (\d+)(?:--(\d+))?", lg)
    rec("FAIL" if errors or undefined else "PASS", "g4. LaTeX errors and undefined references",
        f"{len(errors)} error(s), {len(undefined)} undefined: " + "; ".join((errors + undefined)[:4]) if errors or undefined
        else "0 errors, 0 undefined citations or references")
    if overfull:
        lines = ", ".join(a + (f"--{b}" if b else "") for a, b in overfull)
        rec("FAIL" if strict else "WARN", "g5. overfull boxes", f"{len(overfull)} at tex lines {lines}")
    else:
        rec("PASS", "g5. overfull boxes", "0 overfull hbox or vbox warnings")
    blg = BUILD / "preview" / "paper.blg"
    if blg.exists():
        w = re.findall(r"^Warning--.*$", blg.read_text(encoding="utf-8", errors="replace"), re.M)
        rec("WARN" if w else "PASS", "g6. BibTeX warnings", "; ".join(w[:4]) if w else "none")


def check_h(strict: bool):
    todos = json.loads((BUILD / "todos.json").read_text(encoding="utf-8")) if (BUILD / "todos.json").exists() else []
    figs = [f for f, _ in FIGURES.values() if not (PAPER / "figures" / f).exists()]
    refs = refs_bib().read_text(encoding="utf-8").count("\\todoinline")
    tj = json.loads((BUILD / "tables.json").read_text(encoding="utf-8")) if (BUILD / "tables.json").exists() else {}
    t1 = "table2" not in tj  # Table 2 was dropped on purpose; absence is not an unresolved placeholder
    n = len(todos) + len(figs) + refs
    detail = (f"{len(todos)} placeholder(s) in note.md {[t['text'][:40] for t in todos]}; missing figures {figs}; "
              f"{refs} flagged bib entr{'y' if refs == 1 else 'ies'}; Table 2 {'not placed (dropped on purpose)' if t1 else 'generated'}")
    rec(("FAIL" if strict else "WARN") if n else "PASS", "h. unresolved placeholders", detail)


def check_i(strict: bool):
    figdir = PAPER / "figures"
    tex = (BUILD / "paper.tex").read_text(encoding="utf-8")
    problems, warns, notes = [], [], []
    # files: present, vector, fonts, no remote links, no identity strings
    fonts, info = bin_path("pdffonts"), bin_path("pdfinfo")
    for fid, (fname, num) in FIGURES.items():
        path = figdir / fname
        if not path.exists():
            warns.append(f"{fname} missing")
            continue
        raw = path.read_bytes()
        if b"/Subtype /Image" in raw or b"/Subtype/Image" in raw:
            problems.append(f"{fname} holds a raster image (not vector)")
        if re.search(rb"/URI|/Subtype\s*/Link|/Launch|/GoToR", raw):
            problems.append(f"{fname} holds a link or external action")
        for sgn in LEAK:
            if sgn.encode() in raw:
                problems.append(f"{sgn!r} in {fname}")
        if fonts:
            out = subprocess.run([fonts, str(path)], capture_output=True, text=True).stdout
            rows = [ln for ln in out.split("\n")[2:] if ln.strip()]
            if any("Type 3" in ln for ln in rows):
                problems.append(f"{fname} has a Type 3 font")
            if any(re.search(r"\bno\s+(no|yes)\s+(no|yes)\s", ln) for ln in rows):
                problems.append(f"{fname} has a font that is not embedded")
            if not rows:
                notes.append(f"{fname} has no fonts")
        if info:
            meta = subprocess.run([info, str(path)], capture_output=True, text=True).stdout
            for field in ("Author", "Title", "Subject", "Keywords"):
                m = re.search(rf"^{field}:\s*(.+)$", meta, re.M)
                if m and m.group(1).strip():
                    problems.append(f"{fname} metadata {field} is set")
    # placement in paper.tex: one block per placed figure, in number order, one includegraphics each
    placed = []
    for m in re.finditer(r"\\setcounter\{figure\}\{(\d+)\}\s*\\begin\{figure\}.*?\\end\{figure\}", tex, re.S):
        placed.append((int(m.group(1)) + 1, m.group(0)))
    nums = [n for n, _ in placed]
    want = {n: f for f, n in FIGURES.values()}
    if len(nums) != len(set(nums)):
        problems.append(f"a figure number is used twice in paper.tex: {nums}")
    for n, block in placed:
        if n not in want:
            problems.append(f"figure block with number {n}, but only 1 to {len(FIGURES)} exist")
            continue
        has_inc = f"\\includegraphics[width=0.9\\columnwidth]{{{want[n]}}}" in block
        todo_box = want[n].replace("_", "\\_") in block and "TODO figure" in block
        if not (has_inc or todo_box):
            problems.append(f"Figure {n} block has neither {want[n]} nor the TODO box")
        if todo_box and (figdir / want[n]).exists():
            problems.append(f"Figure {n} shows the TODO box although {want[n]} exists")
    if nums != sorted(nums):
        warns.append(f"figures appear out of number order in paper.tex: {nums}")
    absent = [n for n in sorted(want) if n not in nums]
    if absent:
        warns.append("not placed in the text: " + ", ".join(f"Figure {n} ({want[n]})" for n in absent))
    # citations: every Figure N in the text names a real figure, and every placed figure is cited
    filled = (BUILD / "note_filled.md").read_text(encoding="utf-8")
    cited = set()
    for _, ln, skip in body_lines(filled.split("\n")):
        if skip:
            continue
        cited.update(int(x) for x in re.findall(r"\bFigures? (\d+)", ln))
    bad = sorted(c for c in cited if c not in want)
    if bad:
        problems.append(f"the text cites Figure {bad}, which does not exist")
    uncited = [n for n in nums if n in want and n not in cited]
    if uncited:
        warns.append("placed but never cited in the text: " + ", ".join(f"Figure {n}" for n in uncited))
    ok = f"{len(FIGURES) - sum('missing' in w for w in warns)} of {len(FIGURES)} figure files vector with embedded TrueType fonts; placed {nums}; cited {sorted(cited)}"
    if problems:
        rec("FAIL", "i. figures", "; ".join(problems[:6]))
    elif warns:
        rec("FAIL" if strict else "WARN", "i. figures", "; ".join(warns[:6]) + f" ({ok})")
    else:
        rec("PASS", "i. figures", ok)


# ----------------------------------------------------------------------------- journal profile (Applied Energy)
# Written independently of build.py. Checks the elsarticle package in paper/build_journal (or --build) and the
# side files in paper/journal (or <build>/journal for another --build). No page limit; identity check limited to the employer and client strings.

JOURNAL = PAPER / "journal"  # hand-written inputs: front.json, templates, declarations
SIDE = JOURNAL  # generated side files: paper/journal/ for the default build, <build>/journal/ for another --build
JOURNAL_FIG_FILES = {f"Figure_{n}.pdf": fid for fid, (_, n) in FIGURES.items()}
DECL_ORDER = ["CRediT authorship contribution statement", "Declaration of competing interest", "Funding",
              "Data availability", "Declaration of generative AI"]
SIDE_GENERATED = ("title_page.md", "cover_letter.md", "highlights.txt", "data_availability.md")
OPEN_ITEM = re.compile(r"TO (?:FILL|CONFIRM)")


def strip_line_numbers(text: str) -> str:
    """lineno puts each line number on a line of its own (raw) or at the start of a line (layout)."""
    out = []
    for ln in text.split("\n"):
        if re.fullmatch(r"\s*\d{1,4}\s*", ln):
            continue
        out.append(re.sub(r"^\s*\d{1,4}\s{2,}", "", ln))
    return "\n".join(out)


def factorial_expected(numbers: dict):
    """Table 2 (belief by rule), recomputed from factorial3/M3_rho{rho}/dA{d}/{rule}_{belief}."""
    rows, cells = [], []
    order = [("Point belief", "llf_ce"), ("Shared rate", "llf_pop"), ("Per participant", "llf_e1"),
             ("Point belief", "greedy_ce"), ("Shared rate", "greedy_pop"), ("Per participant", "greedy_e1"),
             ("Point belief", "mpc_ce"), ("Shared rate", "mpc_pop"), ("Per participant", "mpc_e1")]
    for label, suffix in order:
        for i, rho in enumerate(("0.95", "1.15")):
            cs = []
            for d in (0, 1, 2, 4):
                k = f"factorial3/M3_rho{rho}/dA{d}/{suffix}"
                if k not in numbers:
                    return None
                cs.append(printed(numbers[k], False))
                cells.append((k, cs[-1]))
            rows.append((label if i == 0 else "", rho, cs))
    tex_rows = [" & ".join([a, b] + [c.replace("\u2212", "$-$") for c in cs]) + " \\\\" for a, b, cs in rows]
    md_rows = ["| " + " | ".join([a, b] + cs) + " |" for a, b, cs in rows]
    return tex_rows, md_rows, cells


def confirm_expected(numbers: dict):
    """Table 3 (confirmation, descriptive), recomputed from confirm_cell/ keys."""
    rows, cells = [], []
    order = [("CE-LLF", "ce_llf/R_avoid_kwh_per100"), ("CE-MPC", "mpc_ce/R_avoid_kwh_per100"),
             ("Shared-rate MPC", "pop_mpc/R_avoid_kwh_per100"), ("Targeted MPC", "guarded_mpc_e1/R_avoid_kwh_per100"),
             ("Oracle", "oracle_mpc/R_avoid_kwh_per100"), ("Targeted MPC gap", "gap")]
    for label, tail in order:
        for i, rho in enumerate(("0.95", "1.15")):
            cs = []
            for d in (0, 1, 2, 4):
                k = f"confirm_cell/M3_rho{rho}/dA{d}/{tail}"
                if k not in numbers:
                    return None
                cs.append(printed(numbers[k], False))
                cells.append((k, cs[-1]))
            rows.append((label if i == 0 else "", rho, cs))
    tex_rows = [" & ".join([a, b] + [c.replace("\u2212", "$-$") for c in cs]) + " \\\\" for a, b, cs in rows]
    return tex_rows, cells


def check_b3_confirm_table(numbers: dict, used: dict | None):
    exp = confirm_expected(numbers)
    tj = json.loads((BUILD / "tables.json").read_text(encoding="utf-8"))
    tex = (BUILD / "paper.tex").read_text(encoding="utf-8").split("\n")
    probs = []
    if exp is None:
        probs.append("a confirm_cell/ key is missing (run scripts/posthoc_fla_2026_11.py)")
    else:
        tex_rows, cells = exp
        if tj.get("table4", {}).get("rows") != tex_rows:
            probs.append("table4 rows in tables.json differ from the independent recomputation")
        missing = [r for r in tex_rows if r not in tex]
        if missing:
            probs.append(f"{len(missing)} confirmation rows not verbatim in paper.tex")
        if used is not None:
            bad = [k for k, txt in cells if k not in used
                   or ("table", txt) not in [(x["mode"], x["text"]) for x in used[k]["uses"]]]
            if bad:
                probs.append(f"{len(bad)} confirmation cells missing from numbers_used.json")
    rec("FAIL" if probs else "PASS", "b3. confirmation table (Table 2)",
        "; ".join(probs) if probs else f"{len(exp[1])} cells recomputed from the JSON match tables.json, "
        "paper.tex and numbers_used.json")


def check_tables_extra(numbers: dict, used: dict | None):
    """Table 2 (factorial) in both profiles: cells in numbers_used.json, md rows in note_filled.md, tex rows equal
    an independent recomputation."""
    fac = factorial_expected(numbers)
    filled = (BUILD / "note_filled.md").read_text(encoding="utf-8")
    tj = json.loads((BUILD / "tables.json").read_text(encoding="utf-8"))
    probs = []
    if fac is None:
        probs.append("a factorial3/ key is missing from the numbers files")
    else:
        tex_rows, md_rows, cells = fac
        for r in md_rows:
            if r not in filled:
                probs.append(f"factorial md row not in note_filled.md: {r[:70]}")
        if used is not None:
            for k, txt in cells:
                if k not in used or ("table", txt) not in [(u["mode"], u["text"]) for u in used[k]["uses"]]:
                    probs.append(f"factorial cell {k} missing or different in numbers_used.json")
        if tj.get("table3", {}).get("rows") != tex_rows:
            probs.append("table3 rows in tables.json differ from the independent recomputation")
        tex = (BUILD / "paper.tex").read_text(encoding="utf-8").split("\n")
        missing = [r for r in tex_rows if r not in tex]
        if missing:
            probs.append(f"{len(missing)} factorial rows not verbatim in paper.tex")
    rec("FAIL" if probs else "PASS", "b2. factorial table (Table 3)",
        "; ".join(probs[:4]) if probs else f"{len(fac[2])} cells recomputed from the JSON match note_filled.md, "
        "numbers_used.json, tables.json and paper.tex")


def pdf_text_journal(pdf: Path):
    raw, lay = pdf_text(pdf)
    if raw is None:
        return None, None
    return strip_line_numbers(raw), strip_line_numbers(lay)


def filled_sections(filled: str) -> dict:
    lines = filled.split("\n")
    out, cur = {}, None
    for _, ln, skip in body_lines(lines):
        if skip:
            continue
        if ln.startswith("# "):
            cur = ln[2:].strip()
            out[cur] = []
            continue
        if cur is not None:
            out[cur].append(ln)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def front_meta(text: str) -> dict:
    lines = text.split("\n")
    meta = {}
    if lines and lines[0].strip() == "---":
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            m = re.match(r'^(\w+):\s*"(.*)"\s*$', ln)
            if m:
                meta[m.group(1)] = m.group(2)
    return meta


def check_j_abstract(filled: str, tex: str):
    sec = filled_sections(filled)
    ab = sec.get("Abstract", "")
    words = len(ab.split())
    cites = re.findall(r"\[([A-Za-z][A-Za-z0-9]*(?:;\s*[A-Za-z][A-Za-z0-9]*)*)\]", ab)
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S)
    tex_cites = "\\cite" in (m.group(1) if m else "")
    ok = words <= 250 and not cites and not tex_cites and m is not None
    rec("PASS" if ok else "FAIL", "j. abstract",
        f"{words} words after filling (limit 250); citations: {cites or 'none'}"
        + ("; \\cite in the tex abstract" if tex_cites else "") + ("" if m else "; no abstract environment in paper.tex"))
    return words


def check_k_keywords(meta: dict, tex: str):
    kws = [k.strip() for k in meta.get("keywords", "").split(";") if k.strip()]
    bad = [k for k in kws if re.search(r"\b(and|of)\b", k)]
    m = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", tex, re.S)
    n_tex = len(m.group(1).split("\\sep")) if m else 0
    ok = 1 <= len(kws) <= 7 and not bad and n_tex == len(kws)
    rec("PASS" if ok else "FAIL", "k. keywords",
        f"{len(kws)} keywords (1 to 7), {n_tex} in paper.tex; with 'and'/'of': {bad or 'none'}: " + "; ".join(kws))


def check_l_highlights():
    p = SIDE / "highlights.txt"
    if not p.exists():
        rec("FAIL", "l. highlights", f"{p} missing")
        return
    hl = [h for h in p.read_text(encoding="utf-8").split("\n") if h.strip()]
    long = [(len(h), h) for h in hl if len(h) > 85]
    ok = 3 <= len(hl) <= 5 and not long
    rec("PASS" if ok else "FAIL", "l. highlights",
        f"{len(hl)} lines (3 to 5), longest {max(len(h) for h in hl)} characters (limit 85 with spaces)"
        + (f"; too long: {long}" if long else "") + ("; docx present" if (SIDE / "highlights.docx").exists() else "; no docx"))


def check_m_references(tex: str, raw: str):
    bbl_p = BUILD / "paper.bbl"
    if not bbl_p.exists():
        rec("FAIL", "m. references", "paper.bbl missing")
        return
    bbl = bbl_p.read_text(encoding="utf-8")
    items = re.findall(r"\\bibitem\{([^}]+)\}", bbl)
    cited = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", tex):
        for k in m.group(1).split(","):
            if k.strip() not in cited:
                cited.append(k.strip())
    probs = []
    if set(cited) - set(items):
        probs.append(f"cited without entry: {sorted(set(cited) - set(items))}")
    if set(items) - set(cited):
        probs.append(f"entries never cited: {sorted(set(items) - set(cited))}")
    if items != cited:
        probs.append("reference order differs from order of first citation")
    if "[?]" in raw or "??" in raw:
        probs.append("unresolved [?] or ?? in the PDF text")
    long_pages = re.findall(r"(\d+)--(\d+)", bbl)
    unshort = [f"{a}-{b}" for a, b in long_pages if len(a) == len(b) and len(a) > 1 and a[0] == b[0]]
    if unshort:
        probs.append(f"last page not shortened: {unshort}")
    bib = (BUILD / "refs.bib").read_text(encoding="utf-8")
    over6 = [k for k, auth in re.findall(r"@\w+\{([^,]+),\n\s*author = \{(.*?)\},?\n", bib)
             if len([n for n in auth.split(" and ") if n.strip() != "others"]) > 6]
    if over6:
        probs.append(f"more than six authors listed: {over6}")
    tags = re.findall(r"\\bibitem\{([^}]+)\}\n\[(software|dataset)\]", bbl)
    rec("FAIL" if probs else "PASS", "m. references",
        "; ".join(probs) if probs else f"{len(items)} entries, all cited, numbered in order of first citation; "
        f"last pages shortened; at most six authors; tags {tags}")


def check_n_structure(raw: str):
    flat = re.sub(r"\s+", " ", raw)
    probs = []
    for pat, what in ((r"\b1\. Introduction\b", "section 1"), (r"\b\d+\.\d+\. [A-Z]", "a subsection n.n"),
                      (r"\b\d+\.\d+\.\d+\. [A-Z]", "a subsubsection n.n.n"), (r"Appendix A\. ", "Appendix A"),
                      (r"Appendix B\. ", "Appendix B")):
        if not re.search(pat, flat):
            probs.append(f"no {what} heading")
    pos = []
    for h in DECL_ORDER + ["References"]:
        i = flat.rfind(h) if h == "References" else flat.find(h, flat.find("Appendix B"))
        pos.append(i)
        if i < 0:
            probs.append(f"declaration heading '{h}' not found after the appendices")
    if all(i >= 0 for i in pos) and pos != sorted(pos):
        probs.append(f"declarations out of order: {pos}")
    capt = re.findall(r"Table \d+:", flat)
    rec("FAIL" if probs else "PASS", "n. structure",
        "; ".join(probs) if probs else "numbered sections 1, 1.1, 1.1.1; appendices after the main text; "
        f"declarations {' > '.join(DECL_ORDER)} directly before References; {len(capt)} table captions")


def check_o_units(filled: str):
    body = [ln for _, ln, skip in body_lines(filled.split("\n")) if not skip]
    hits = [ln[:80] for ln in body if "kW·slot" in ln and "0.25 kWh" not in ln]
    rec("FAIL" if hits else "PASS", "o. SI units",
        f"kW·slot used as a reporting unit: {hits[:3]}" if hits else
        "no result reported in kW·slot; violations in kWh (si/ keys), delays in slots of 15 min")


def check_e_journal(raw: str, tex: str, filled: str):
    targets = {"PDF text": raw, "paper.tex": tex, "paper.bbl": (BUILD / "paper.bbl").read_text(encoding="utf-8"),
               "note_filled.md": filled}
    for f in ("title_page.md", "cover_letter.md", "highlights.txt", "data_availability.md", "credit.md",
              "competing_interests.md", "funding.md", "genai_declaration.md"):
        d = SIDE if f in SIDE_GENERATED else JOURNAL
        if (d / f).exists():
            targets[f] = (d / f).read_text(encoding="utf-8")
    if not HAVE_PRIVATE_IDENTITY:
        rec("WARN", "e. employer and client strings",
            "paper/identity_private.txt is absent, so the employer and client strings were not checked")
        return
    hits = [f"{s!r} in {n}" for n, t in targets.items() for s in EMPLOYER_CLIENT if s in t or s in re.sub(r"\s+", " ", t)]
    rec("FAIL" if hits else "PASS", "e. employer and client strings",
        "; ".join(hits) if hits else f"none of {len(EMPLOYER_CLIENT)} private strings in {len(targets)} files "
        "(journal review is single-anonymized; author identity allowed)")


def side_files() -> list:
    """Every .md and .txt side file: the hand-written ones in paper/journal/ and the generated ones in SIDE."""
    found = {}
    for d in (JOURNAL, SIDE):
        for f in sorted(d.glob("*.md")) + sorted(d.glob("*.txt")):
            if d is JOURNAL and SIDE is not JOURNAL and f.name in SIDE_GENERATED:
                continue  # in a non-default build the committed copy is not part of this package
            found[f.name] = f
    return [found[k] for k in sorted(found)]


def check_f_journal():
    files = [BUILD / "note_filled.md", BUILD / "paper.tex", BUILD / "paper.bbl", NOTE] + side_files() + sorted((JOURNAL / "templates").glob("*.md"))
    hits = [p.name for p in files if p.exists() and EM in p.read_text(encoding="utf-8")]
    tex = (BUILD / "paper.tex").read_text(encoding="utf-8")
    if "\\textemdash" in tex or re.search(r"(?<!-)---(?!-)", tex):
        hits.append("LaTeX em dash in paper.tex")
    rec("FAIL" if hits else "PASS", "f. em dash", "; ".join(hits) if hits else f"none in {len(files)} files")


def check_g_journal(pdf: Path):
    out = subprocess.run([bin_path("pdffonts"), str(pdf)], capture_output=True, text=True).stdout
    rows = [ln for ln in out.split("\n")[2:] if ln.strip()]
    t3 = [ln for ln in rows if "Type 3" in ln]
    notemb = [ln.split()[0] for ln in rows if re.search(r"\bno\s+(no|yes)\s+(no|yes)\s+\d", ln)]
    rec("FAIL" if t3 or notemb else "PASS", "g3. fonts",
        f"{len(t3)} Type 3, not embedded: {notemb}" if t3 or notemb else f"{len(rows)} fonts, all embedded, no Type 3")
    lg = (BUILD / "paper.log").read_text(encoding="utf-8", errors="replace")
    errors = re.findall(r"^! .*$", lg, re.M)
    undefined = re.findall(r"(?:Citation|Reference) `[^']*' .*undefined.*", lg)
    rec("FAIL" if errors or undefined else "PASS", "g4. LaTeX errors and undefined references",
        f"{len(errors)} error(s), {len(undefined)} undefined" if errors or undefined else "0 errors, 0 undefined")
    overfull = re.findall(r"Overfull \\[hv]box.*?lines? (\d+)(?:--(\d+))?", lg)
    rec("FAIL" if overfull else "PASS", "g5. overfull boxes",
        f"{len(overfull)} at tex lines " + ", ".join(a + (f"--{b}" if b else "") for a, b in overfull) if overfull
        else "0 overfull hbox or vbox warnings")


def check_h_journal(raw: str, strict: bool):
    todos = json.loads((BUILD / "todos.json").read_text(encoding="utf-8")) if (BUILD / "todos.json").exists() else []
    open_pdf = sorted(set(m.group(0) for m in OPEN_ITEM.finditer(raw)))
    side = {f.name: len(OPEN_ITEM.findall(f.read_text(encoding="utf-8"))) for f in side_files()
            if OPEN_ITEM.search(f.read_text(encoding="utf-8"))}
    n_pdf = len(OPEN_ITEM.findall(raw))
    detail = (f"{len(todos)} note placeholder(s); {n_pdf} TO FILL/CONFIRM mark(s) in the PDF (author address); "
              f"side files with open items: {side or 'none'}")
    if todos:
        rec("FAIL", "h. unresolved placeholders", detail)
    else:
        rec(("FAIL" if strict else "WARN") if (n_pdf or side) else "PASS", "h. unresolved placeholders", detail)


def check_i_journal(tex: str, filled: str):
    probs, ok_files = [], 0
    for name in JOURNAL_FIG_FILES:
        p = BUILD / name
        if not p.exists():
            probs.append(f"{name} missing")
            continue
        raw = p.read_bytes()
        if b"/Subtype /Image" in raw or b"/Subtype/Image" in raw:
            probs.append(f"{name} holds a raster image")
        out = subprocess.run([bin_path("pdffonts"), str(p)], capture_output=True, text=True).stdout
        rows = [ln for ln in out.split("\n")[2:] if ln.strip()]
        if any("Type 3" in ln for ln in rows) or any(re.search(r"\bno\s+(no|yes)\s+(no|yes)\s+\d", ln) for ln in rows):
            probs.append(f"{name} has a Type 3 or unembedded font")
        ok_files += 1
    inc = re.findall(r"\\includegraphics\[[^\]]*\]\{(Figure_\d+)\}", tex)
    if inc != [f"Figure_{n}" for n in range(1, len(FIGURES) + 1)]:
        probs.append(f"figures included out of order or missing: {inc}")
    cited = set()
    for _, ln, skip in body_lines(filled.split("\n")):
        if not skip:
            cited.update(int(x) for x in re.findall(r"\bFigures? (\d+)", ln))
    if cited != set(range(1, len(FIGURES) + 1)):
        probs.append(f"cited figures {sorted(cited)}")
    rec("FAIL" if probs else "PASS", "i. figures",
        "; ".join(probs) if probs else f"{ok_files} separate vector files Figure_1..{len(FIGURES)}.pdf with embedded "
        "non-Type-3 fonts, included once each in order, each cited")


def _png_size(p: Path):
    b = p.read_bytes()[:24]
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    import struct
    return struct.unpack(">II", b[16:24])


def check_p_upload():
    j = BUILD / "upload_check.json"
    if not j.exists():
        rec("FAIL", "p. upload package", "upload_check.json missing (run build.py --profile journal zip)")
        return
    res = json.loads(j.read_text(encoding="utf-8"))
    want = sorted(["paper.tex", "paper.bbl"] + list(JOURNAL_FIG_FILES))
    up = BUILD / "upload"
    have = sorted(p.name for p in up.iterdir()) if up.exists() else []
    probs = []
    if have != want:
        probs.append(f"upload/ holds {have}, expected {want}")
    import zipfile
    zp = Path(res["zip"])
    if not zp.exists() or sorted(zipfile.ZipFile(zp).namelist()) != want:
        probs.append("zip content differs from the expected file list")
    for f in ("paper.tex", "paper.bbl"):
        if (up / f).exists() and (up / f).read_bytes() != (BUILD / f).read_bytes():
            probs.append(f"upload/{f} differs from the build")
    if not res.get("compiled") or res.get("undefined") or res.get("missing_files"):
        probs.append(f"clean compile failed: {res}")
    rec("FAIL" if probs else "PASS", "p. upload package",
        "; ".join(probs) if probs else f"{len(want)} files ({', '.join(want)}) and {zp.name}; compiled alone in "
        f"{res['temp_dir']} ({res['pages']} pages, no undefined references, no missing files)")


def check_q_side_files(numbers: dict, meta: dict, tex: str):
    probs = []
    front = json.loads((JOURNAL / "front.json").read_text(encoding="utf-8"))
    af = front["affiliation"]
    subs = {"TITLE": meta.get("title", ""), "KEYWORDS": "; ".join(k.strip() for k in meta.get("keywords", "").split(";") if k.strip()),
            "AUTHOR": front["author"], "EMAIL": front["email"], "EMAIL_STATUS": front.get("email_status", ""),
            "ORGANIZATION": af["organization"], "ADDRESSLINE": af.get("addressline", ""), "CITY": af.get("city", ""),
            "STATE": af.get("state", ""), "COUNTRY": af.get("country", "")}
    n_num = 0
    for src, out in (("title_page.md", "title_page.md"), ("cover_letter.md", "cover_letter.md"),
                     ("highlights.md", "highlights.txt")):
        t = (JOURNAL / "templates" / src).read_text(encoding="utf-8")
        for k, v in subs.items():
            t = t.replace(f"%%{k}%%", v)

        def sub(m):
            nonlocal n_num
            n_num += 1
            k, mode = m.group(1), m.group(2)
            return str(int(round(numbers[k]["value"]))) if mode == "i" else printed(numbers[k], bool(mode))
        t = NUM_REF.sub(sub, t)
        got = (SIDE / out).read_text(encoding="utf-8") if (SIDE / out).exists() else None
        if got != t:
            probs.append(f"{out} differs from an independent fill of its template")
    if "subtitle" in meta:
        probs.append("note.md still has a subtitle field")
    title = meta.get("title", "")
    m = re.search(r"\\title\{(.*?)\}\n", tex)
    if not m or re.sub(r"\s+", " ", m.group(1)) != title:
        probs.append("paper.tex title differs from the note.md title field")
    for f in ("title_page.md", "cover_letter.md"):
        if title not in (SIDE / f).read_text(encoding="utf-8"):
            probs.append(f"title not in {f}")
    ga = SIDE / "graphical_abstract.pdf"
    if ga.exists():
        gt = re.sub(r"\s+", " ", subprocess.run([bin_path("pdftotext"), str(ga), "-"], capture_output=True, text=True).stdout)
        if title not in gt:
            probs.append("title not in the graphical abstract")
    rec("FAIL" if probs else "PASS", "q. side files and title",
        "; ".join(probs) if probs else f"title page, cover letter and highlights equal an independent fill "
        f"({n_num} numbers); one title in note.md, paper.tex, title page, cover letter and graphical abstract")


def check_r_graphical_abstract():
    png, pdf = SIDE / "graphical_abstract.png", SIDE / "graphical_abstract.pdf"
    probs = []
    size = _png_size(png) if png.exists() else None
    if not size:
        probs.append("graphical_abstract.png missing or not a PNG")
    else:
        w, h = size
        if w < 1328 or w <= h:
            probs.append(f"PNG {w} x {h} px: needs landscape and at least 1328 px wide")
    if not pdf.exists():
        probs.append("graphical_abstract.pdf missing")
    else:
        raw = pdf.read_bytes()
        if b"/Subtype /Image" in raw or b"/Subtype/Image" in raw:
            probs.append("PDF holds a raster image")
        out = subprocess.run([bin_path("pdffonts"), str(pdf)], capture_output=True, text=True).stdout
        rows = [ln for ln in out.split("\n")[2:] if ln.strip()]
        if any("Type 3" in ln for ln in rows) or any(re.search(r"\bno\s+(no|yes)\s+(no|yes)\s+\d", ln) for ln in rows):
            probs.append("PDF has a Type 3 or unembedded font")
        bad_fonts = [ln.split()[0] for ln in rows if not re.search(r"Arial|Times|Courier|Symbol", ln)]
        if bad_fonts:
            probs.append(f"fonts other than Times, Arial, Courier or Symbol: {bad_fonts}")
        txt = subprocess.run([bin_path("pdftotext"), str(pdf), "-"], capture_output=True, text=True).stdout.lower()
        if "graphical abstract" in txt:
            probs.append("the image carries the heading 'graphical abstract'")
    rec("FAIL" if probs else "PASS", "r. graphical abstract",
        "; ".join(probs) if probs else f"PNG {size[0]} x {size[1]} px landscape; vector PDF, Arial embedded; no heading")


def check_t_table_agreement(numbers: dict):
    """Review plan P4: a policy and cell printed in both Table 1 (cell/ keys) and Table 2 (factorial3/ keys)
    must print the same string."""
    pairs = [("ce_llf", "llf_ce"), ("pop_mpc", "mpc_pop"), ("guarded_mpc_e1", "mpc_e1")]
    bad, n = [], 0
    for rho in ("0.95", "1.15"):
        for d in (0, 1, 2, 4):
            for a, b in pairs:
                k1 = f"cell/F0R_M3_dA{d}_db0_rho{rho}_r0.3/{a}/R_avoid_kwh_per100"
                k2 = f"factorial3/M3_rho{rho}/dA{d}/{b}"
                if k1 in numbers and k2 in numbers:
                    n += 1
                    p1, p2 = printed(numbers[k1], False), printed(numbers[k2], False)
                    if p1 != p2:
                        bad.append(f"{a} rho {rho} delta {d}: {p1} vs {p2}")
    rec("FAIL" if bad or not n else "PASS", "t. Tables 1 and 3 agree",
        "; ".join(bad) if bad else f"{n} shared policy-cell entries print identically")


BANNED_WORDS = {  # regex -> why (review plan P1, P2, P5, P13, P14)
    "referee": "no journal referee exists yet; say pre-submission review",
    r"(?<!utility )(?<!utility-)pilot": "pilot means only the utility pilot; say trial run",
    r"grew with delay|as confirmation slowed": "the delay result is a two-band contrast, not a trend",
    r"only inside a planner|only when a planner": "the shared rate helps the greedy ranker too",
    r"reserved seeds at 99% Bonferroni": "jargon in reader-facing text",
}


def check_u_banned_words(raw: str, tex: str):
    found = []
    texts = {"note.md": NOTE.read_text(encoding="utf-8"), "paper.tex": tex, "PDF text": raw}
    for d in (JOURNAL, SIDE):
        for f in sorted(d.glob("*.md")) + sorted(d.glob("*.txt")):
            texts[f.name] = f.read_text(encoding="utf-8")
    for w, why in BANNED_WORDS.items():
        for name, t in texts.items():
            body = re.sub(r"\s+", " ", re.sub(r"<!--.*?-->", "", t, flags=re.S))  # PDF text breaks lines inside phrases
            if re.search(rf"\b(?:{w})", body, re.I):
                found.append(f"'{w}' in {name} ({why})")
    rec("FAIL" if found else "PASS", "u. banned words", "; ".join(found) if found else f"none of {list(BANNED_WORDS)}")


FLOAT_WINDOW = (-1, 1)  # caption page minus first-citation page; the author's rule: floats near the citing text


def check_s_floats(tex: str, pdf: Path):
    """The author's Applied Energy layout rules (2026-11-18), checked from paper.tex and the PDF text:
    s.1 captions below every table and figure; s.2 numbers follow the order of first citation;
    s.3 data and AI statements directly before the references, in red while listed in build.py RED_DECLARATIONS;
    s.4 every float on its first-citation page or within FLOAT_WINDOW of it."""
    probs = []
    for env in ("table", "figure"):
        body_end = r"\\end\{tabular\}" if env == "table" else r"\\includegraphics"
        for blk in re.findall(rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}", tex, re.S):
            c, b = re.search(r"\\caption\{", blk), re.search(body_end, blk)
            if not (c and b and c.start() > b.start()):
                probs.append(f"s.1 {env} caption not below: {blk[:60]!r}")
    # Red is required only for the statements still listed in build.py RED_DECLARATIONS (author decision
    # 2026-11-24: both statements approved and printed black). Both must stay the last sections before the
    # references in either case.
    src = (Path(__file__).parent / "build.py").read_text(encoding="utf-8")
    m = re.search(r"^RED_DECLARATIONS = \(([^)]*)\)", src, re.M)
    red = re.findall(r'"([^"]+)"', m.group(1)) if m else ["@data", "genai_declaration.md"]
    titles = {"@data": "Data availability", "genai_declaration.md": "Declaration of generative AI"}
    for key in red:
        title = titles.get(key, key)
        if not re.search(r"\{\\color\{red\}[^\n]*\n\\section\*\{" + re.escape(title), tex):
            probs.append(f"s.3 '{title}' not printed in red")
    bib = tex.find("\\bibliography")
    last = re.findall(r"\\section\*?\{([^}]*)\}", tex[:bib] if bib >= 0 else tex)
    if bib < 0 or not last or not last[-1].startswith("Declaration of generative AI") or \
            (len(last) > 1 and last[-2] != "Data availability"):
        probs.append("s.3 data and AI statements are not directly before the references")
    out = subprocess.run([bin_path("pdftotext"), str(pdf), "-"], capture_output=True, text=True).stdout
    caption_page, cite_page = {}, {}
    for pno, page in enumerate(out.split("\f"), start=1):
        for line in page.split("\n"):
            m = re.match(r"(Figure|Table) (\d+):", line)
            if m:
                caption_page.setdefault(f"{m[1]} {m[2]}", pno)
                line = line[m.end():]  # a caption may cite another float
            for k in re.findall(r"\b(?:Figure|Table) \d+\b", line):
                cite_page.setdefault(k, pno)
    dists = {}
    for kind in ("Figure", "Table"):
        keys = sorted((k for k in caption_page if k.startswith(kind)), key=lambda k: int(k.split()[1]))
        firsts = [cite_page.get(k, 10 ** 6) for k in keys]
        if firsts != sorted(firsts):
            probs.append(f"s.2 {kind} numbers not in order of first citation: {dict(zip(keys, firsts))}")
        for k in keys:
            if k not in cite_page:
                probs.append(f"s.4 {k} never cited in the text")
                continue
            d = caption_page[k] - cite_page[k]
            dists[k] = d
            if not FLOAT_WINDOW[0] <= d <= FLOAT_WINDOW[1]:
                probs.append(f"s.4 {k} on page {caption_page[k]}, first cited on page {cite_page[k]}")
    rec("FAIL" if probs else "PASS", "s. float layout and red statements",
        "; ".join(probs) if probs else "captions below all tables and figures; numbered by first citation; "
        f"caption page minus first-citation page {dists}; data and AI statements in red before References")


def main_journal(args, numbers: dict):
    pdf = BUILD / "paper.pdf"
    if not pdf.exists():
        print("paper.pdf missing; run build.py --profile journal all first", file=sys.stderr)
        sys.exit(2)
    note_text = NOTE.read_text(encoding="utf-8")
    filled = (BUILD / "note_filled.md").read_text(encoding="utf-8")
    tex = (BUILD / "paper.tex").read_text(encoding="utf-8")
    meta = front_meta(note_text)
    used = check_a(numbers, note_text)
    check_b(numbers)
    check_tables_extra(numbers, used)
    check_b3_confirm_table(numbers, used)
    raw, lay = pdf_text_journal(pdf)
    if raw is None:
        rec("FAIL", "c. numbers in PDF text", "pdftotext not available")
    else:
        check_c(used, raw, lay)
    info = subprocess.run([bin_path("pdfinfo"), str(pdf)], capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    rec("PASS", "d. page count", f"{pages} pages (no page limit for the journal)")
    check_e_journal(raw or "", tex, filled)
    check_f_journal()
    check_g_journal(pdf)
    check_h_journal(raw or "", args.strict)
    check_i_journal(tex, filled)
    check_j_abstract(filled, tex)
    check_k_keywords(meta, tex)
    check_l_highlights()
    check_m_references(tex, raw or "")
    check_n_structure(raw or "")
    check_o_units(filled)
    check_p_upload()
    check_q_side_files(numbers, meta, tex)
    check_r_graphical_abstract()
    check_s_floats(tex, pdf)
    check_t_table_agreement(numbers)
    check_u_banned_words(raw or "", tex)


def main():
    global NOTE, BUILD, SIDE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--numbers", type=Path, default=DEFAULT_NUMBERS)
    ap.add_argument("--note", type=Path, default=NOTE, help="source note (default paper/note.md)")
    ap.add_argument("--build", type=Path, default=BUILD, help="build folder (default paper/build)")
    ap.add_argument("--limit", type=int, default=7, help="page limit before the references")
    ap.add_argument("--strict", action="store_true", help="overfull boxes and unresolved placeholders fail")
    ap.add_argument("--profile", choices=("aaai", "journal"), default="aaai",
                    help="aaai (default): AAAI-27 checks; journal: Applied Energy package checks (no page limit)")
    args = ap.parse_args()
    if args.profile == "journal" and args.build == BUILD:
        args.build = PAPER / "build_journal"
    NOTE, BUILD = args.note.resolve(), args.build.resolve()
    if args.profile == "journal":
        SIDE = JOURNAL if BUILD == (PAPER / "build_journal").resolve() else BUILD / "journal"
    numbers = dict(json.loads(args.numbers.read_text(encoding="utf-8"))["numbers"])
    for name in EXTRA_NUMBERS:
        extra = args.numbers.parent / name
        if extra.exists():
            numbers.update(json.loads(extra.read_text(encoding="utf-8"))["numbers"])
    if args.profile == "journal":
        main_journal(args, numbers)
        fails = [r for r in results if r[0] == "FAIL"]
        warns = [r for r in results if r[0] == "WARN"]
        print(f"\n{len(results) - len(fails) - len(warns)} passed, {len(warns)} warning(s), {len(fails)} failed")
        sys.exit(1 if fails else 0)
    note_text = NOTE.read_text(encoding="utf-8")
    pdf = BUILD / "paper.pdf"
    if not pdf.exists():
        print("paper.pdf missing; run build.py all first", file=sys.stderr)
        sys.exit(2)
    used = check_a(numbers, note_text)
    check_b(numbers)
    check_tables_extra(numbers, used)
    check_b3_confirm_table(numbers, used)
    raw, lay = pdf_text(pdf)
    if raw is None:
        rec("FAIL", "c. numbers in PDF text", "pdftotext not available")
    else:
        check_c(used, raw, lay)
    check_d(pdf, args.limit)
    check_e(raw, lay, pdf)
    check_f()
    check_g(pdf, args.strict)
    check_h(args.strict)
    check_i(args.strict)
    fails = [r for r in results if r[0] == "FAIL"]
    warns = [r for r in results if r[0] == "WARN"]
    print(f"\n{len(results) - len(fails) - len(warns)} passed, {len(warns)} warning(s), {len(fails)} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
