"""Graphical abstract for the Applied Energy submission (scripted vector diagram, no generative image tool).

Usage: uv run python scripts/make_graphical_abstract.py [--out paper/journal]

Left: the setting, drawn like Figure 1 of the paper (one feeder limit, cars owing energy, an operator sending
setpoints, confirmations coming back late, one car silently stuck). Right: the three steps of the results and
the confirmed headline share, read from results/confirm_paper_numbers.json (confirm/C3, 99% Bonferroni
interval on 200 reserved seeds). The title is read from the single front-matter field of paper/note.md.

Writes graphical_abstract.pdf (vector, TrueType fonts) and graphical_abstract.png (300 dpi, landscape,
at least 1328 px wide) in --out. Fonts: Arial (the guide allows Times, Arial, Courier or Symbol).
No heading "graphical abstract" inside the image (guide).
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W, H = 6.6, 2.64          # inches; ratio 5 : 2 as the guide's 500 x 200 example
MIN_WIDTH_PX = 1328
MINUS = "−"


def fmt(x: float) -> str:
    d = Decimal(abs(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (MINUS if x < 0 and d != 0 else "") + f"{d:.2f}"


def title_from_note(note: Path) -> str:
    lines = note.read_text(encoding="utf-8").split("\n")
    if lines[0].strip() != "---":
        raise SystemExit("note.md has no front matter")
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        m = re.match(r'^title:\s*"(.*)"\s*$', ln)
        if m:
            return m.group(1)
    raise SystemExit("no title field in the front matter of note.md")


def arrow(ax, p0, p1, lw=1.2, ls="-", color="black", scale=9):
    ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", lw=lw, ls=ls, color=color,
                                                      shrinkA=0, shrinkB=0, mutation_scale=scale))


def car(ax, x, y, stuck=False):
    """A small side-view car, 0.42 in wide, its lower left corner at (x, y)."""
    ls = (0, (3, 2)) if stuck else "-"
    fc = "white" if stuck else "0.85"
    ax.add_patch(FancyBboxPatch((x, y + 0.06), 0.42, 0.11, boxstyle="round,pad=0.0,rounding_size=0.03",
                                lw=0.9, ls=ls, ec="black", fc=fc, zorder=3))
    ax.add_patch(FancyBboxPatch((x + 0.09, y + 0.17), 0.22, 0.08, boxstyle="round,pad=0.0,rounding_size=0.03",
                                lw=0.9, ls=ls, ec="black", fc=fc, zorder=3))
    for cx in (x + 0.10, x + 0.32):
        ax.add_patch(Circle((cx, y + 0.06), 0.045, lw=0.8, ec="black", fc="white", zorder=4))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--confirm", type=Path, default=ROOT / "results" / "confirm_paper_numbers.json")
    ap.add_argument("--note", type=Path, default=ROOT / "paper" / "note.md")
    ap.add_argument("--out", type=Path, default=ROOT / "paper" / "journal")
    args = ap.parse_args(argv)
    c3 = json.loads(args.confirm.read_text(encoding="utf-8"))["numbers"]["confirm/C3"]
    share, lo, hi = float(c3["value"]), float(c3["ci_lo"]), float(c3["ci_hi"])
    title = title_from_note(args.note)

    plt.rcParams.update({"font.family": "Arial", "pdf.fonttype": 42, "ps.fonttype": 42,
                         "font.size": 9, "savefig.dpi": 300})
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    ax.text(W / 2, H - 0.13, title, ha="center", va="center", fontsize=8.6, weight="bold", wrap=True)
    ax.plot([3.18, 3.18], [0.12, H - 0.32], color="0.75", lw=0.8)

    # ---------------- left: the setting
    fy = 2.02
    ax.plot([0.15, 3.02], [fy, fy], color="black", lw=3.2, solid_capstyle="butt")
    ax.text(1.58, fy + 0.13, "one feeder limit shared by all cars", ha="center", va="center", fontsize=7.6)
    ax.add_patch(Rectangle((0.15, 0.52), 0.55, 1.18, lw=1.0, ec="black", fc="0.9", zorder=2))
    ax.text(0.425, 1.11, "operator", rotation=90, ha="center", va="center", fontsize=8)
    ax.plot([0.425, 0.425], [1.70, fy], color="black", lw=0.8)
    xs, ys = [2.05, 2.55, 2.05, 2.55], [1.40, 1.40, 0.72, 0.72]
    for k, (x, y) in enumerate(zip(xs, ys)):
        stuck = k == 3
        car(ax, x, y, stuck)
        ax.plot([x + 0.21, x + 0.21], [y + 0.25, fy], color="0.55", lw=0.6, zorder=1)
    arrow(ax, (0.72, 1.48), (1.98, 1.48))
    ax.text(1.35, 1.53, "setpoint now", ha="center", va="bottom", fontsize=7.4)
    arrow(ax, (1.98, 0.86), (0.72, 0.86), ls=(0, (3, 2)), color="0.3", lw=1.0)
    ax.text(1.35, 0.92, "confirmed\n30 to 60 min later", ha="center", va="bottom", fontsize=7.4, linespacing=1.0)
    ax.text(2.97, 0.50, "silently stuck", ha="right", va="top", fontsize=7.4, style="italic")
    ax.text(1.58, 0.22, "Deferred energy must reach each car before it leaves",
            ha="center", va="center", fontsize=7.4, color="0.2")

    # ---------------- right: three steps and the confirmed share
    x0, x1 = 3.42, 6.42
    steps = [("1", "Plan instead of a greedy rule"),
             ("2", "Hedge with one shared failure rate"),
             ("3", "Learn who fails, per participant")]
    for k, (n, txt) in enumerate(steps):
        y = 2.03 - 0.30 * k
        ax.add_patch(Circle((x0 + 0.10, y), 0.095, ec="black", fc="0.85" if k < 2 else "white", lw=0.9))
        ax.text(x0 + 0.10, y, n, ha="center", va="center", fontsize=8, weight="bold")
        ax.text(x0 + 0.28, y, txt, ha="left", va="center", fontsize=8.4)
    by, bh = 0.78, 0.30
    split = x0 + share * (x1 - x0)
    ax.add_patch(Rectangle((x0, by), split - x0, bh, ec="black", fc="0.80", lw=0.9))
    ax.add_patch(Rectangle((split, by), x1 - split, bh, ec="black", fc="white", lw=0.9, hatch="//"))
    ax.text((x0 + split) / 2, by + bh / 2, "steps 1 and 2: " + fmt(share), ha="center", va="center",
            fontsize=8.6, weight="bold")
    ax.text((split + x1) / 2, by + bh / 2, "step 3", ha="center", va="center", fontsize=7.6,
            bbox=dict(fc="white", ec="none", pad=0.5))
    ax.text(x0, by + bh + 0.08, "Share of the per-participant planner's gain over the greedy rule",
            ha="left", va="bottom", fontsize=7.6)
    ax.text(x0, by - 0.10, f"Confirmed on 200 held-out instances, 99% interval {fmt(lo)} to {fmt(hi)}",
            ha="left", va="top", fontsize=7.4, color="0.15")
    ax.text(x0, by - 0.33, "Synthetic benchmark, 30 participants, 30 min delay",
            ha="left", va="top", fontsize=7.4, color="0.15")

    args.out.mkdir(parents=True, exist_ok=True)
    pdf, png = args.out / "graphical_abstract.pdf", args.out / "graphical_abstract.png"
    fig.savefig(pdf, metadata={"Creator": None, "Producer": None})
    fig.savefig(png, dpi=300)
    plt.close(fig)
    from matplotlib import image
    h_px, w_px = image.imread(png).shape[:2]
    if w_px < MIN_WIDTH_PX or w_px <= h_px:
        raise SystemExit(f"graphical abstract is {w_px} x {h_px} px; needs landscape and at least {MIN_WIDTH_PX} px wide")
    print(f"[graphical_abstract] wrote {pdf} and {png} ({w_px} x {h_px} px); C3 = {fmt(share)} [{fmt(lo)}, {fmt(hi)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
