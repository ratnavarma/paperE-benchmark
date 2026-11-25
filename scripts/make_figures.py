"""Make the manuscript figures (vector PDFs) from the paper-numbers data file.

Usage: uv run python scripts/make_figures.py [--data results/paper_numbers.json]
       [--posthoc results/posthoc_g3_runs.json] [--ranker results/posthoc_ranker.json] [--out paper/figures]

Writes five PDFs: fig_setting.pdf (the setting), fig_window.pdf (hedge or correct), fig_ladder.pdf
(the scheduler ladder, numbers read from the post hoc file), fig_layers.pdf (hedging and targeting
layers) and fig_e3.pdf (E3: top, Proposition 1 gap against spare cap; bottom, Proposition 3 recovery
against prior events). The first three are schematics drawn in inch coordinates.
Single-column width (3.3 in), 8 pt text, TrueType (Type 42) fonts, black and grey only: series
differ by marker shape, fill and line style, so the figures read in grayscale. matplotlib is a
dev-only dependency used here and nowhere in the library.

Applied Energy build (2026-11-02): axis labels are words with SI units in parentheses, legends are words,
energy is in kWh (one instance unit = 0.25 kWh, rescaled here, never typed), delay is in minutes (one slot =
15 min) and the ladder has three rules (LLF, the greedy expected-value ranker, MPC), its ranker arrows read
from results/posthoc_ranker.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIDTH_IN = 3.3

# fig_e3 shows M = 0 only (no observed history), the clearest single view; one panel per M adds
# nothing. The M = 1, 3, 5 pooled gap points also pass the simultaneous rule (see
# e3/summary/n_pass); pointwise they can differ from the M = 0 points.
E3_M = 0
E3_QS = (0.14, 0.40, 0.50)
E3_P3_MS = (0, 1, 3, 5)  # prior events M of the Proposition 3 points (keys e3/gap_e1/<cap>/q<q>/c8/M<M>)
E3_P3_CAPS = ("pooled", "per_copy")
E3_P3_C = 8
KWH_PER_UNIT = 0.25   # one instance unit is 1 kW for one 15-minute slot
MIN_PER_SLOT = 15
LAYER_M = 3
LAYER_RHOS = (0.95, 1.15)
LAYER_DAS = (0, 1, 2, 4)


def set_style() -> None:
    plt.rcParams.update({
        "pdf.fonttype": 42, "ps.fonttype": 42,
        "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",  # bundled; no system-font dependence
        "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "legend.fontsize": 7, "axes.linewidth": 0.6, "lines.linewidth": 0.9,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "figure.dpi": 150, "savefig.dpi": 300,
    })


def closed_gap(K: float, q: float, c):
    """gap(c) = q c / 2 for c <= K, q (K - c / 2) for c >= K (Proposition for the pooled cap)."""
    c = np.asarray(c, dtype=float)
    return np.where(c <= K, q * c / 2.0, q * (K - c / 2.0))


class MissingDataError(Exception):
    """A key (or stored field) the figures need is absent from the data file."""


def _get(nums: dict, key: str) -> dict:
    if key not in nums:
        raise MissingDataError(f"missing data key: {key}")
    return nums[key]


def simultaneous_bounds(rec: dict, key: str, m_getter, allow_se_fallback: bool):
    """(lo, hi) of the simultaneous interval of one E3 record, as stored.

    The stored simultaneous_lo/hi are used directly. Only if a stored bound is absent AND
    allow_se_fallback is set, the half-width t_{1 - alpha/(2m)} * mc_se is used, with
    m = e3/summary/n_points, alpha = 0.05, df = n_seeds - 1. Otherwise this raises.
    """
    lo, hi = rec.get("simultaneous_lo"), rec.get("simultaneous_hi")
    if lo is not None and hi is not None:
        return float(lo), float(hi)
    if not allow_se_fallback:
        raise MissingDataError(f"missing stored simultaneous_lo/simultaneous_hi in {key} "
                               "(pass --allow-se-fallback to use the t-quantile * mc_se)")
    if rec.get("mc_se") is None:
        raise MissingDataError(f"missing mc_se in {key}")
    df = max(int(rec.get("n_seeds", 2)) - 1, 1)
    hw = float(stats.t.ppf(1 - 0.05 / (2 * m_getter()), df) * rec["mc_se"])
    return rec["value"] - hw, rec["value"] + hw


def e3_series(nums: dict, allow_se_fallback: bool = False) -> dict:
    """q -> dict(c, y, lo, hi, K) of the plotted points (absolute simultaneous bounds)."""
    def m_getter():
        return int(_get(nums, "e3/summary/n_points")["value"])

    out = {}
    for q in E3_QS:
        cs, ys, los, his, K = [], [], [], [], 8
        for c in range(0, 17, 2):
            key = f"e3/gap_oracle/pooled/q{q:g}/c{c}/M{E3_M}"
            rec = _get(nums, key)
            lo, hi = simultaneous_bounds(rec, key, m_getter, allow_se_fallback)
            cs.append(c)
            ys.append(float(rec["value"]))
            los.append(lo)
            his.append(hi)
            K = rec.get("K", K)
        out[q] = dict(c=np.array(cs, float), y=np.array(ys), lo=np.array(los),
                      hi=np.array(his), K=K)
    return out


def e3_prop3_series(nums: dict, allow_se_fallback: bool = False) -> dict:
    """(cap, q) -> dict(M, y, lo, hi, pred, K) of the Proposition 3 points (pop - e1 gap).

    y is the measured gap, [lo, hi] the stored simultaneous interval, pred the stored prediction
    K q/2 - E[R_e1] (Proposition 3).
    """
    def m_getter():
        return int(_get(nums, "e3/summary/n_points")["value"])

    out = {}
    for cap in E3_P3_CAPS:
        for q in E3_QS:
            Ms, ys, los, his, preds, K = [], [], [], [], [], 8
            for M in E3_P3_MS:
                key = f"e3/gap_e1/{cap}/q{q:g}/c{E3_P3_C}/M{M}"
                rec = _get(nums, key)
                if rec.get("predicted") is None:
                    raise MissingDataError(f"missing predicted in {key}")
                lo, hi = simultaneous_bounds(rec, key, m_getter, allow_se_fallback)
                Ms.append(M)
                ys.append(float(rec["value"]))
                los.append(lo)
                his.append(hi)
                preds.append(float(rec["predicted"]))
                K = rec.get("K", K)
            out[(cap, q)] = dict(M=np.array(Ms, float), y=np.array(ys), lo=np.array(los),
                                 hi=np.array(his), pred=np.array(preds), K=K)
    return out


LAYER_SERIES = [  # layer -> (marker, linestyle, x offset); same encoding in both panels
    ("planning", "^", ":", -0.1),
    ("hedging", "o", "-", 0.0),
    ("targeting", "s", "--", 0.1),
]


def layer_series(nums: dict) -> dict:
    """(rho, layer) -> dict(x, y, lo, hi) of the plotted points (stored 95% interval bounds)."""
    out = {}
    for rho in LAYER_RHOS:
        for layer, _mk, _ls, off in LAYER_SERIES:
            xs, ys, los, his = [], [], [], []
            for d in LAYER_DAS:
                rec = _get(nums, f"layers/M{LAYER_M}_rho{rho:g}/dA{d}/{layer}")
                for f in ("value", "ci_lo", "ci_hi"):
                    if rec.get(f) is None:
                        raise MissingDataError(
                            f"missing field {f} in layers/M{LAYER_M}_rho{rho:g}/dA{d}/{layer}")
                xs.append(d + off)
                ys.append(float(rec["value"]))
                los.append(float(rec["ci_lo"]))
                his.append(float(rec["ci_hi"]))
            out[(rho, layer)] = dict(x=np.array(xs), y=np.array(ys), lo=np.array(los),
                                     hi=np.array(his))
    return out


def _yerr(sr: dict):
    """Asymmetric error-bar array from stored absolute bounds."""
    return [np.maximum(sr["y"] - sr["lo"], 0.0), np.maximum(sr["hi"] - sr["y"], 0.0)]


def fig_e3(nums: dict, out: Path, allow_se_fallback: bool = False) -> None:
    data = e3_series(nums, allow_se_fallback)
    p3 = e3_prop3_series(nums, allow_se_fallback)
    styles = {  # q -> (marker, filled, linestyle, grey)
        0.14: ("o", False, "-", "0.0"),
        0.40: ("s", True, "--", "0.25"),
        0.50: ("^", True, ":", "0.0"),
    }
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(WIDTH_IN, 4.5), gridspec_kw=dict(height_ratios=(1, 1.1)))
    # ---- top: Proposition 1 gap against spare cap c
    ax.axhline(0, color="0.6", lw=0.5, zorder=0)
    offs = {0.14: -0.22, 0.40: 0.0, 0.50: 0.22}
    handles = []
    for q in E3_QS:
        mk, filled, ls, grey = styles[q]
        sr = data[q]
        xs = np.linspace(0, 16, 161)
        ax.plot(xs, KWH_PER_UNIT * closed_gap(sr["K"], q, xs), color=grey, ls=ls, lw=0.9, zorder=1)
        sr = {k: (KWH_PER_UNIT * v if k in ("y", "lo", "hi") else v) for k, v in sr.items()}
        ax.errorbar(sr["c"] + offs[q], sr["y"], yerr=_yerr(sr), fmt=mk, ms=4.2, mew=0.8,
                    color=grey, mfc=grey if filled else "white", elinewidth=0.7, capsize=1.8,
                    capthick=0.7, ls="none", zorder=3)
        handles.append(plt.Line2D([], [], color=grey, ls=ls, marker=mk, ms=4.2, mew=0.8,
                                  mfc=grey if filled else "white", label=f"stuck probability {q:.2f}"))
    ax.axvline(8, color="0.7", lw=0.5, ls=(0, (1, 2)), zorder=0)
    ax.set_ylim(ax.get_ylim()[0], 1.4 * ax.get_ylim()[1])  # headroom for the legend
    ax.set_xlim(-0.8, 16.8)
    ax.set_xticks(range(0, 17, 2))
    ax.set_xlabel("Spare capacity in the second slot (kW)")
    ax.set_ylabel("Residual, shared rate\nminus oracle (kWh)")
    ax.legend(handles=handles, loc="upper right", frameon=False, handlelength=2.6,
              borderaxespad=0.2, labelspacing=0.3)

    # ---- bottom: Proposition 3 recovery, pop - e1 gap against prior events M, c = K
    # cap type: line style (prediction) and fill (measured); q: marker and grey level as above.
    cap_style = {"pooled": ("-", True, -1), "per_copy": ((0, (3, 1.5)), False, 1)}
    bx.axhline(0, color="0.6", lw=0.5, zorder=0)
    qoff = {0.14: -0.16, 0.40: 0.0, 0.50: 0.16}
    for (cap, q), sr in p3.items():
        sr = {k: (KWH_PER_UNIT * v if k in ("y", "lo", "hi", "pred") else v) for k, v in sr.items()}
        mk, _f, _ls, grey = styles[q]
        cls, cfilled, side = cap_style[cap]
        x = sr["M"] + qoff[q] + 0.07 * side
        bx.plot(sr["M"] + qoff[q] + 0.07 * side, sr["pred"], color=grey, ls=cls, lw=0.8, zorder=1)
        bx.errorbar(x, sr["y"], yerr=_yerr(sr), fmt=mk, ms=3.8, mew=0.8, color=grey,
                    mfc=grey if cfilled else "white", elinewidth=0.7, capsize=1.5, capthick=0.7,
                    ls="none", zorder=3)
    bx.set_xlim(-0.6, 5.6)
    top = KWH_PER_UNIT * max(float(sr["hi"].max()) for sr in p3.values())
    bx.set_ylim(bx.get_ylim()[0], top + 0.9 * KWH_PER_UNIT)  # headroom for the two legends
    bx.set_xticks(E3_P3_MS)
    bx.set_xlabel("Earlier events with confirmed outcomes (count)")
    bx.set_ylabel("Residual, shared rate minus\nper-participant model (kWh)")
    q_handles = [plt.Line2D([], [], color=styles[q][3], ls="none", marker=styles[q][0], ms=3.8,
                            mew=0.8, mfc=styles[q][3], label=f"stuck prob. {q:.2f}") for q in E3_QS]
    cap_handles = [plt.Line2D([], [], color="0.2", ls=cap_style[c][0], marker="o", ms=3.8, mew=0.8,
                              mfc="0.2" if cap_style[c][1] else "white", label=lab)
                   for c, lab in (("pooled", "pooled cap"), ("per_copy", "per-pair cap"))]
    leg1 = bx.legend(handles=q_handles, loc="upper left", frameon=False, handlelength=1.0,
                     borderaxespad=0.2, labelspacing=0.3)
    bx.add_artist(leg1)
    bx.legend(handles=cap_handles, loc="upper left", bbox_to_anchor=(0.46, 1.0), frameon=False,
              handlelength=2.6, borderaxespad=0.2, labelspacing=0.3)
    fig.tight_layout(pad=0.4, h_pad=0.8)
    fig.savefig(out / "fig_e3.pdf")
    plt.close(fig)


def fig_layers(nums: dict, out: Path) -> None:
    data = layer_series(nums)
    fig, axes = plt.subplots(1, len(LAYER_RHOS), figsize=(WIDTH_IN, 2.75), sharey=True)
    for ax, rho in zip(axes, LAYER_RHOS):
        ax.axhline(0, color="0.5", lw=0.6, zorder=0)
        for layer, mk, ls, _off in LAYER_SERIES:
            sr = data[(rho, layer)]
            ax.errorbar(sr["x"], sr["y"], yerr=_yerr(sr), fmt=mk, ls=ls, ms=3.8, mew=0.8,
                        color="black", mfc="white", elinewidth=0.7, capsize=1.5, capthick=0.7,
                        zorder=3)
        ax.set_xticks(LAYER_DAS)
        ax.set_xticklabels([str(MIN_PER_SLOT * d) for d in LAYER_DAS])
        ax.set_xlim(-0.5, 4.5)
        ax.text(0.96, 0.96, ("loose" if rho < 1 else "tight") + f" limit\nstress {rho:.2f}",
                transform=ax.transAxes, ha="right", va="top", linespacing=1.1)
    fig.supxlabel("Confirmation delay (min)", fontsize=8)
    axes[0].set_ylabel("Gain (kWh per 100\nparticipants per event)")
    words = {"planning": "planning", "hedging": "shared-rate hedging", "targeting": "per-participant targeting"}
    handles = [plt.Line2D([], [], color="black", ls=ls, marker=mk, ms=3.8, mew=0.8, mfc="white",
                          label=words[lab]) for lab, mk, ls, _ in LAYER_SERIES]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, handlelength=2.2,
               columnspacing=1.0, handletextpad=0.4, borderaxespad=0.0, fontsize=6.6)
    fig.tight_layout(pad=0.4, w_pad=0.6, rect=(0, 0, 1, 0.86))
    fig.savefig(out / "fig_layers.pdf")
    plt.close(fig)


# ---------------------------------------------------------------------------------- schematics
# The three explanatory figures are drawn in inch coordinates on a full-figure axis (1 unit = 1 in),
# so sizes and gaps are set directly. Black, white and grey only: line style, fill and marker shape
# carry the meaning.

SCHEM = 6.8   # schematic label size (pt); figures are placed at 0.9 column width
SMALL = 6.1
MINUS_CH = "−"


def _canvas(w: float, h: float):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def _arrow(ax, p0, p1, lw=0.9, ls="-", color="black", scale=6, style="-|>"):
    ax.annotate("", xy=p1, xytext=p0, zorder=3,
                arrowprops=dict(arrowstyle=style, lw=lw, ls=ls, color=color, shrinkA=0, shrinkB=0,
                                mutation_scale=scale))


def _box(ax, x, y, w, h, lw=0.7, ls="-", fc="white", ec="black", hatch=None, z=2):
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((x, y), w, h, lw=lw, ls=ls, fc=fc, ec=ec, hatch=hatch, zorder=z))


def fig_setting(out: Path) -> None:
    W, H = WIDTH_IN, 3.55
    fig, ax = _canvas(W, H)
    # shared feeder limit across the top
    ax.plot([0.05, W - 0.05], [3.30, 3.30], color="black", lw=3.0, solid_capstyle="butt", zorder=2)
    ax.text(W / 2, 3.45, "shared feeder limit: setpoints in a slot sum to at most the cap",
            ha="center", va="center", fontsize=SCHEM)
    # operator
    ox0, ox1, oy0, oy1 = 0.05, 0.50, 0.80, 3.02
    _box(ax, ox0, oy0, ox1 - ox0, oy1 - oy0, lw=1.0, fc="0.9")
    ax.text((ox0 + ox1) / 2, (oy0 + oy1) / 2, "operator", rotation=90, ha="center", va="center",
            fontsize=7)
    ax.plot([0.275, 0.275], [oy1, 3.30], color="black", lw=0.8, zorder=1)
    ax.plot([W - 0.06, W - 0.06], [2.92, 3.30], color="black", lw=0.8, zorder=1)
    # participants: debt bar and deadline tick per row
    bx0, bx1 = 1.58, W - 0.05
    ys = [2.62 - 0.34 * k for k in range(6)]
    debts = [0.62, 0.38, 0.70, 0.28, 0.50, 0.58]
    dls = [3.10, 2.96, 3.16, 2.86, 3.02, 2.92]
    silent = 5
    for k, (yc, debt, dl) in enumerate(zip(ys, debts, dls)):
        _box(ax, bx0, yc - 0.14, bx1 - bx0, 0.28, lw=0.7, ls=(0, (3, 2)) if k == silent else "-")
        ax.text(bx0 + 0.07, yc, f"{k + 1}", ha="center", va="center", fontsize=SCHEM)
        _box(ax, 1.78, yc - 0.045, debt, 0.09, lw=0.6, fc="0.6", z=3)
        ax.plot([2.62, bx1 - 0.06], [yc, yc], color="0.5", lw=0.5, zorder=2)
        ax.plot([dl, dl], [yc - 0.08, yc + 0.08], color="black", lw=1.2, zorder=3)
        # setpoint (solid) out, confirmation (dashed) back
        _arrow(ax, (ox1, yc + 0.055), (bx0, yc + 0.055), lw=0.9)
        if k != silent:
            _arrow(ax, (bx0, yc - 0.055), (ox1, yc - 0.055), lw=0.7, ls=(0, (2.5, 1.5)), color="0.3")
    ax.text(1.78 + 0.35, 2.92, "debt", ha="center", va="bottom", fontsize=SMALL)
    ax.text(2.99, 2.92, "deadline", ha="center", va="bottom", fontsize=SMALL)
    ax.text((ox1 + bx0) / 2, 2.84, "setpoints $x_{it}$\nin slot $t$", ha="center", va="bottom",
            fontsize=SMALL, linespacing=1.1)
    ax.text((ox1 + bx0) / 2, 0.72, "$y_{is}$ confirmed\n$\\delta$ slots later", ha="center", va="top",
            fontsize=SMALL, linespacing=1.1)
    ax.text(W - 0.08, 0.50, "stuck after the pause,\ninvisible until commanded", ha="right", va="center",
            fontsize=SMALL, linespacing=1.1)
    _arrow(ax, (W - 0.45, 0.64), (W - 0.45, ys[silent] - 0.14), lw=0.6, scale=5)
    ax.text(2.30, 3.13, "$N$ participants, 6 shown", ha="center", va="center", fontsize=SMALL)
    # slot axis: setpoint at t, confirmation at t + delta
    ay, ax0 = 0.30, 0.10
    sl = 0.27
    ax.plot([ax0, ax0 + 5 * sl + 0.08], [ay, ay], color="black", lw=0.7)
    for j, lab in enumerate(["$t$", "$t{+}1$", "$t{+}\\delta$"]):
        x = ax0 + 0.10 + (j if j < 2 else 2) * sl
        ax.plot([x, x], [ay - 0.03, ay + 0.03], color="black", lw=0.7)
        ax.text(x, ay - 0.06, lab, ha="center", va="top", fontsize=SMALL)
    ax.plot([ax0 + 0.10], [ay], marker="o", ms=3.5, mfc="black", mec="black", zorder=4)
    ax.plot([ax0 + 0.10 + 2 * sl], [ay], marker="o", ms=3.5, mfc="white", mec="black", mew=0.8, zorder=4)
    ax.text(ax0 + 5 * sl + 0.13, ay, "15-min slots", ha="left", va="center", fontsize=SMALL)
    ax.text(ax0 + 0.10, ay + 0.07, "setpoint", ha="center", va="bottom", fontsize=SMALL - 0.4)
    ax.text(ax0 + 0.10 + 2 * sl, ay + 0.07, "confirmed", ha="center", va="bottom", fontsize=SMALL - 0.4)
    fig.savefig(out / "fig_setting.pdf")
    plt.close(fig)


def fig_window(out: Path) -> None:
    W, H = WIDTH_IN, 3.05
    fig, ax = _canvas(W, H)
    x0, cw, ncell = 0.25, 0.29, 10
    s, d = 3, 8

    def row(y0, delta, title, fail_lab_dx=0.0):
        ax.text(0.05, y0 + 0.55, title, ha="left", va="center", fontsize=SCHEM + 0.6)
        conf = s + delta
        window = list(range(conf, d))
        for c in range(ncell):
            in_w = c in window
            _box(ax, x0 + c * cw, y0, cw, 0.30, lw=0.6,
                 fc="0.8" if in_w else ("0.93" if c >= d else "white"), hatch="////" if in_w else None)
            ax.text(x0 + (c + 0.5) * cw, y0 - 0.09, f"{c}", ha="center", va="top", fontsize=SMALL)
        # deadline: bold line at the start of slot d (slot d - 1 is the last usable one)
        ax.plot([x0 + d * cw] * 2, [y0 - 0.04, y0 + 0.40], color="black", lw=1.6, zorder=4)
        # failed setpoint at s
        ax.plot([x0 + (s + 0.5) * cw], [y0 + 0.15], marker="X", ms=5.5, mfc="black", mec="black", zorder=5)
        ax.text(x0 + (s + 0.5) * cw, y0 + 0.43, f"failed setpoint\n$s={s}$", ha="center", va="bottom",
                fontsize=SMALL, linespacing=1.1)
        # confirmation at s + delta
        ax.plot([x0 + (conf + 0.5) * cw], [y0 + 0.15], marker="D", ms=4.2, mfc="white", mec="black",
                mew=0.9, zorder=5)
        return conf, window

    # row A: delta = 2, window s + delta <= t <= d - 1 is non-empty
    yA = 2.15
    conf, win = row(yA, 2, "$\\delta=2$")
    ax.text(x0 + (conf + 0.5) * cw + 0.04, yA + 0.43, f"confirmed\n$s+\\delta={conf}$", ha="left",
            va="bottom", fontsize=SMALL, linespacing=1.1)
    ax.text(x0 + d * cw, yA + 0.55, f"$d_i={d}$", ha="center", va="bottom", fontsize=SMALL)
    ax.plot([x0 + (win[1] + 0.5) * cw], [yA + 0.15], marker="o", ms=4.2, mfc="black", mec="black", zorder=5)
    ax.plot([x0 + win[0] * cw + 0.02, x0 + (win[-1] + 1) * cw - 0.02], [yA - 0.26] * 2, color="black",
            lw=0.8)
    ax.text(x0 + (win[0] + len(win) / 2) * cw, yA - 0.30,
            "correction window\n$s+\\delta\\leq t\\leq d_i-1$", ha="center", va="top", fontsize=SMALL,
            linespacing=1.1)

    # row B: delta = 5, s + delta = d, no slot left to correct in
    yB = 0.72
    conf, win = row(yB, 5, "$\\delta=5$")
    ax.text(x0 + (conf + 0.5) * cw + 0.05, yB + 0.43, f"confirmed\n$s+\\delta={conf}$", ha="left",
            va="bottom", fontsize=SMALL, linespacing=1.1)
    ax.plot([x0 + 4.5 * cw], [yB + 0.15], marker="^", ms=4.8, mfc="white", mec="black", mew=0.9, zorder=5)
    ax.text(x0 + 4.5 * cw + 0.07, yB + 0.43, "hedge sent\nin advance", ha="left", va="bottom",
            fontsize=SMALL, linespacing=1.1)
    ax.text(x0 + 5.0 * cw, yB - 0.27, f"$s+\\delta={conf}>d_i-1={d - 1}$: window empty, hedge only",
            ha="center", va="top", fontsize=SMALL)

    # key
    items = [("X", "black", "black", "failed setpoint"), ("D", "white", "black", "outcome known"),
             ("o", "black", "black", "re-dispatch"), ("^", "white", "black", "hedge")]
    handles = [plt.Line2D([], [], ls="none", marker=m, ms=4.2, mfc=fc, mec=ec, mew=0.9, label=lab)
               for m, fc, ec, lab in items]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=SMALL,
               handletextpad=0.2, columnspacing=0.8, borderaxespad=0.02)
    ax.text(W - 0.05, 2.93, "slots of 15 min", ha="right", va="center", fontsize=SMALL, color="0.25")
    fig.savefig(out / "fig_window.pdf")
    plt.close(fig)


LADDER_KEY = "posthoc_runs/factorial/M3_rho0.95/dA2/"
RANKER_KEY = "posthoc_ranker/M3_rho0.95/dA2/"
# rows: 0 LLF, 1 greedy ranker, 2 MPC; columns: 0 certainty-equivalent, 1 shared rate, 2 per participant
LADDER_BELIEF = {  # (rule row, left belief column) -> (source, key suffix); the arrow runs to the next column
    (0, 0): ("g3", "belief_ce_to_pop_in_llf"), (0, 1): ("g3", "belief_pop_to_e1_in_llf"),
    (1, 0): ("rk", "belief_ce_to_pop_in_greedy"), (1, 1): ("rk", "belief_pop_to_e1_in_greedy"),
    (2, 0): ("g3", "belief_ce_to_pop_in_mpc"), (2, 1): ("g3", "belief_pop_to_e1_in_mpc"),
}
LADDER_RULE = {  # (upper rule row, belief column) -> (source, key suffix); the arrow runs one row down
    (0, 0): ("rk", "rule_llf_to_greedy_given_ce"), (0, 1): ("rk", "rule_llf_to_greedy_given_pop"),
    (0, 2): ("rk", "rule_llf_to_greedy_given_e1"),
    (1, 0): ("rk", "rule_greedy_to_mpc_given_ce"), (1, 1): ("rk", "rule_greedy_to_mpc_given_pop"),
    (1, 2): ("rk", "rule_greedy_to_mpc_given_e1"),
}
LADDER_FIELDS = ("value", "ci_lo", "ci_hi")


def ladder_values(post: dict, ranker: dict) -> dict:
    """(source, suffix) -> dict(value, ci_lo, ci_hi) for the twelve arrows, read from the post hoc data files."""
    out = {}
    for src, suffix in list(LADDER_BELIEF.values()) + list(LADDER_RULE.values()):
        data, key = (post, LADDER_KEY + suffix) if src == "g3" else (ranker, RANKER_KEY + suffix)
        rec = _get(data, key)
        for f in LADDER_FIELDS:
            if rec.get(f) is None:
                raise MissingDataError(f"missing field {f} in {key}")
        out[(src, suffix)] = {f: float(rec[f]) for f in LADDER_FIELDS}
    return out


def _fmt2(x: float) -> str:
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(abs(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (MINUS_CH if x < 0 and d != 0 else "") + f"{d:.2f}"


def _gain_label(v: dict) -> str:
    sign = "+" if v["value"] > 0 and _fmt2(v["value"]) != "0.00" else ""
    return f"{sign}{_fmt2(v['value'])}\n[{_fmt2(v['ci_lo'])}, {_fmt2(v['ci_hi'])}]"


def fig_ladder(post: dict, ranker: dict, out: Path) -> None:
    vals = ladder_values(post, ranker)
    W, H = WIDTH_IN, 4.30
    fig, ax = _canvas(W, H)
    bw, bh = 0.56, 0.50
    xs = [0.23, 0.23 + bw + 0.66, 0.23 + 2 * (bw + 0.66)]
    ys = [3.18, 1.88, 0.58]  # bottom edges of the LLF, ranker and MPC rows
    names = [["CE-LLF", "LLF with\nshared rate", "LLF-POST"],
             ["Ranker,\npoint belief", "Ranker,\nshared rate", "Ranker, per\nparticipant"],
             ["CE-MPC", "Shared-rate\nMPC", "Targeted\nMPC"]]
    heads = ["point belief\n(every setpoint\ndelivers)", "one shared\nfailure rate", "failure rate\nper participant"]
    for c, hd in enumerate(heads):
        ax.text(xs[c] + bw / 2, ys[0] + bh + 0.08, hd, ha="center", va="bottom", fontsize=SMALL - 0.5,
                linespacing=1.05)
    for r, rl in enumerate(["greedy LLF", "greedy ranker", "planner (MPC)"]):
        ax.text(0.09, ys[r] + bh / 2, rl, rotation=90, ha="center", va="center", fontsize=SMALL)
    for r in range(3):
        for c in range(3):
            cand, base = (r, c) == (2, 2), (r, c) == (0, 0)
            _box(ax, xs[c], ys[r], bw, bh, lw=2.0 if cand else 0.8, fc="0.82" if cand else "white",
                 hatch="///" if base else None)
            ax.text(xs[c] + bw / 2, ys[r] + bh / 2, names[r][c], ha="center", va="center",
                    fontsize=SMALL - 0.4, linespacing=1.0,
                    bbox=dict(fc="white", ec="none", pad=0.6) if base else None, zorder=4)

    def style(v):  # solid: lower avoidable residual; dashed: higher
        return ("-", 1.1) if v["value"] > 0 else ((0, (3, 1.6)), 1.1)

    for (r, c), ref in LADDER_BELIEF.items():
        v = vals[ref]
        ls, lw = style(v)
        yc = ys[r] + bh / 2
        _arrow(ax, (xs[c] + bw + 0.03, yc), (xs[c + 1] - 0.03, yc), lw=lw, ls=ls, scale=7)
        ax.text((xs[c] + bw + xs[c + 1]) / 2, yc + 0.05, _gain_label(v), ha="center", va="bottom",
                fontsize=SMALL - 0.4, linespacing=1.0)
    for (r, c), ref in LADDER_RULE.items():
        v = vals[ref]
        ls, lw = style(v)
        xc = xs[c] + bw / 2
        _arrow(ax, (xc, ys[r] - 0.03), (xc, ys[r + 1] + bh + 0.03), lw=lw, ls=ls, scale=7)
        ax.text(xc, (ys[r] + ys[r + 1] + bh) / 2, _gain_label(v), ha="center", va="center",
                fontsize=SMALL - 0.4, linespacing=1.0, bbox=dict(fc="white", ec="none", pad=1.0), zorder=5)
    ax.text(W / 2, 0.22, "gain in kWh per 100 participants per event; solid arrow: lower\n"
            "avoidable residual; dashed arrow: higher", ha="center", va="center",
            fontsize=SMALL - 0.3, linespacing=1.1, color="0.2")
    fig.savefig(out / "fig_ladder.pdf")
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=ROOT / "results" / "paper_numbers.json")
    ap.add_argument("--posthoc", type=Path, default=ROOT / "results" / "posthoc_g3_runs.json",
                    help="post hoc numbers file the scheduler-ladder arrows are read from")
    ap.add_argument("--ranker", type=Path, default=ROOT / "results" / "posthoc_ranker.json",
                    help="post hoc ranker numbers file the ranker arrows of the ladder are read from")
    ap.add_argument("--out", type=Path, default=ROOT / "paper" / "figures")
    ap.add_argument("--allow-se-fallback", action="store_true",
                    help="if a stored simultaneous bound is absent, use t_{1-alpha/(2m)} * mc_se")
    args = ap.parse_args(argv)
    nums = json.loads(args.data.read_text())["numbers"]
    post = json.loads(args.posthoc.read_text())["numbers"]
    ranker = json.loads(args.ranker.read_text())["numbers"]
    set_style()
    try:
        # build both series before writing anything, so a missing key leaves no partial output
        e3_series(nums, args.allow_se_fallback)
        e3_prop3_series(nums, args.allow_se_fallback)
        layer_series(nums)
        ladder_values(post, ranker)
        args.out.mkdir(parents=True, exist_ok=True)
        fig_e3(nums, args.out, args.allow_se_fallback)
        fig_layers(nums, args.out)
        fig_setting(args.out)
        fig_window(args.out)
        fig_ladder(post, ranker, args.out)
    except MissingDataError as e:
        raise SystemExit(f"make_figures: error: {e}") from None
    names = ("fig_setting", "fig_window", "fig_ladder", "fig_layers", "fig_e3")
    print("[make_figures] wrote " + ", ".join(str(args.out / f"{n}.pdf") for n in names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
