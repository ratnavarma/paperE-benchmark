"""Tuning-seed fit of the population parameters (POLICY_SPEC Section 3.1).

Uses prior-event data only (``prior_A``, ``prior_stuck``) of F0-R instances on the primary
cell family with ``M = 5`` prior events and ``r = 0.3`` for seeds 60000-60049. This module
lives outside ``policies/`` and may import the generator; policies receive the result as
plain numbers (``PopulationParams``).

* ``alpha, beta``: beta-binomial maximum likelihood over per-participant stuck counts out of
  ``M = 5`` events.
* ``q_bar_stuck, q_bar_total``: pooled stuck count and number of (participant, event) pairs
  (reported; the population-mode ``q_bar`` uses alpha, beta, see below).
* ``n_aa, n_as, n_ss, n_sa``: transition counts over every prior chain (slot t-1 -> t within
  each event). Policies use only their within-row ratios: each row (avail, stuck) is
  rescaled to an effective sample size of ``PRIOR_ESS = 10`` and the instance's own counts
  are added, so the tuning seeds are a prior of limited strength. The population-mode
  ``q_bar`` is the same Beta(alpha, beta) prior as e1 updated with the pooled stuck count.

CLI: ``uv run python -m papere.fit`` writes ``results/population_params.json``.
"""
from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize
from scipy.special import betaln, gammaln

from .generator import F0R_CELLS, generate_f0r
from .instance import Cell
from .policies.base import PopulationParams

TUNING_SEEDS = range(60000, 60050)
M_FIT = 5
R_FIT = 0.3
RESULT_PATH = Path(__file__).resolve().parents[2] / "results" / "population_params.json"


def fit_cell() -> Cell:
    """The primary F0-R cell with M = 5 and r = 0.3 (delta_A = 2, rho = 0.95)."""
    for cell in F0R_CELLS:
        if (cell.family == "F0R" and cell.M == M_FIT and cell.r == R_FIT
                and cell.delta_A == 2 and cell.delta_b == 0 and cell.rho == 0.95):
            return cell
    return Cell(family="F0R", M=M_FIT, delta_A=2, delta_b=0, rho=0.95, r=R_FIT)


def beta_binomial_mle(counts: np.ndarray, n_trials: int) -> tuple[float, float, float]:
    """MLE of (alpha, beta) for counts out of ``n_trials``; returns (alpha, beta, loglik)."""
    k = np.asarray(counts, dtype=np.float64)
    n = float(n_trials)
    logc = gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)

    def nll(theta: np.ndarray) -> float:
        a, b = np.exp(theta)
        return -float(np.sum(logc + betaln(k + a, n - k + b) - betaln(a, b)))

    p0 = float(np.clip(k.mean() / n, 1e-3, 1 - 1e-3))
    best = None
    for conc in (0.5, 2.0, 10.0):          # several starts: the likelihood can be flat
        x0 = np.log([p0 * conc, (1 - p0) * conc])
        res = minimize(nll, x0, method="L-BFGS-B", bounds=[(-8.0, 8.0), (-8.0, 8.0)])
        if best is None or res.fun < best.fun:
            best = res
    a, b = np.exp(best.x)
    return float(a), float(b), -float(best.fun)


def binomial_loglik(counts: np.ndarray, n_trials: int) -> float:
    k = np.asarray(counts, dtype=np.float64)
    n = float(n_trials)
    p = k.sum() / (n * k.size)
    logc = gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)
    return float(np.sum(logc + k * np.log(p) + (n - k) * np.log1p(-p)))


def collect(seeds=TUNING_SEEDS, cell: Cell | None = None) -> dict:
    """Pooled prior-event statistics over ``seeds`` (prior events only)."""
    cell = fit_cell() if cell is None else cell
    if cell.M != M_FIT:
        raise ValueError("the fit uses all five prior events (M = 5)")
    stuck_counts, n_aa, n_as, n_ss, n_sa = [], 0, 0, 0, 0
    pairs = 0
    for seed in seeds:
        inst = generate_f0r(seed, cell)
        stuck_counts.append(inst.prior_stuck.sum(axis=1))
        pairs += inst.prior_stuck.size
        a0, a1 = inst.prior_A[:, :, :-1] == 1, inst.prior_A[:, :, 1:] == 1
        n_aa += int(np.sum(a0 & a1))
        n_as += int(np.sum(a0 & ~a1))
        n_sa += int(np.sum(~a0 & a1))
        n_ss += int(np.sum(~a0 & ~a1))
    counts = np.concatenate(stuck_counts)
    return dict(counts=counts, pairs=pairs, n_aa=n_aa, n_as=n_as, n_ss=n_ss, n_sa=n_sa)


def fit_population_params(seeds=TUNING_SEEDS, *, details: bool = False):
    """Fit ``PopulationParams`` on ``seeds`` (default 60000-60049)."""
    data = collect(seeds)
    counts = data["counts"]
    alpha, beta, ll_bb = beta_binomial_mle(counts, M_FIT)
    params = PopulationParams(
        alpha=alpha, beta=beta,
        q_bar_stuck=float(counts.sum()), q_bar_total=float(data["pairs"]),
        n_aa=float(data["n_aa"]), n_as=float(data["n_as"]),
        n_ss=float(data["n_ss"]), n_sa=float(data["n_sa"]))
    if not details:
        return params
    ll_bin = binomial_loglik(counts, M_FIT)
    info = dict(
        n_participants=int(counts.size),
        beta_binomial_mean=alpha / (alpha + beta),
        beta_binomial_intra_class_correlation=1.0 / (alpha + beta + 1.0),
        pooled_stuck_rate=params.q_bar_stuck / params.q_bar_total,
        loglik_beta_binomial=ll_bb, loglik_binomial=ll_bin,
        lrt_statistic=2.0 * (ll_bb - ll_bin),
        p_stay_hat=params.n_aa / (params.n_aa + params.n_as),
        r_hat=params.n_sa / (params.n_sa + params.n_ss))
    return params, info


def _git_commit() -> dict:
    root = Path(__file__).resolve().parents[2]
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return dict(commit=head, working_tree_dirty=dirty)
    except (OSError, subprocess.CalledProcessError):
        return dict(commit=None, working_tree_dirty=None)


def load_population_params(path: str | Path = RESULT_PATH) -> PopulationParams:
    """Read the frozen parameters written by the CLI."""
    with open(path) as fh:
        blob = json.load(fh)
    return PopulationParams(**blob["values"])


def main(path: str | Path = RESULT_PATH) -> None:
    seeds = TUNING_SEEDS
    params, info = fit_population_params(seeds, details=True)
    cell = fit_cell()
    blob = dict(
        seeds=dict(first=seeds[0], last=seeds[-1], count=len(seeds)),
        cell_id=cell.cell_id,
        method=("prior-event data only; (alpha, beta) by beta-binomial maximum likelihood "
                "(scipy L-BFGS-B on log-parameters, best of three starts) over per-participant "
                "stuck counts out of M = 5 events; q_bar = pooled stuck count and "
                "(participant, event) pair count; transition counts over all prior chains, "
                "slot t-1 -> t within each event, as Beta pseudo-counts"),
        values=asdict(params),
        diagnostics=info,
        versions=dict(python=platform.python_version(), numpy=np.__version__,
                      scipy=scipy.__version__),
        git=_git_commit())
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(blob, fh, indent=2)
        fh.write("\n")
    print(json.dumps(blob, indent=2))


if __name__ == "__main__":
    main()
