"""ACN T2 instance construction (protocol section 3).

Builds ``Instance`` objects for real ACN site-days by:
- Extracting real ``N, E, P, a, d`` from sessions connected at ``e = 17:00`` local
  with remaining need ``>= 0.25`` kWh and ``d_i >= 1`` (dropping site-days with ``N < 5``).
- Reusing ``papere.generator.generate_f0r`` and its frozen streams for base load
  (``_base_load`` with ``B0 = N``), failure classes, stuck probabilities, prior events
  (``M``) and availability chains, and replacing ``E, P, a, d, announced, L``.
- Selecting a site-day uniformly with replacement from all eligible site-days using a
  dedicated child stream named ``acn_day`` of ``SeedSequence(seed)``.
- Supporting the T2-emp variant (stuck probabilities drawn from ``Beta(alpha, beta)``)
  and the real-limit variant (``L`` from the site's 99th-percentile aggregate charging
  power over the 17:00-23:00 window).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Mapping, Sequence

import numpy as np

from papere.flow import max_flow
from papere.generator import H_F0R, M_MAX, generate_f0r, stream
from papere.instance import Cell, Instance, chain_availability, iid_availability
from papere.ledger import flow_problem

from .load import (
    MIN_SESSIONS_PER_DAY,
    Session,
    SiteDay,
    eligible_site_days,
    sessions_connected_at,
)

T2_EVENT_HOUR = 17
T2_SLOT_MIN = 15
T2_SLOT_S = T2_SLOT_MIN * 60.0
T2_H = H_F0R  # 24 slots (6 hours: 17:00-23:00)
T2_MIN_REMAINING_KWH = 0.25
T2_UNIT_KWH = 0.25
T2_P_UNITS = 6  # 6.6 kW at 208 V, 32 A, floored
T2_MIN_PARTICIPANTS = 5
SITE_VOLTAGE_V = 208.0

# Dedicated child stream ids disjoint from papere.generator._STREAM_IDS (1..10).
_ACN_STREAM_IDS: dict[str, int] = {
    "acn_day": 101,
    "emp_q": 102,
}


def acn_stream(seed: int, name: str, salt: int = 0) -> np.random.Generator:
    """Named child stream of ``SeedSequence(seed)`` for ACN-specific draws."""
    sid = _ACN_STREAM_IDS[name]
    key = (sid,) if salt == 0 else (sid, int(salt))
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(int(seed), spawn_key=key)))


def _ro(arr: np.ndarray) -> np.ndarray:
    arr.flags.writeable = False
    return arr


@dataclass(frozen=True)
class T2SiteDayData:
    """Real participant arrays for one T2-eligible ACN site-day (N >= 5)."""

    site: str
    local_date: date
    timezone: str
    n_cleaned_sessions: int
    session_ids: tuple[str, ...]
    E: np.ndarray  # [N] int64
    P: np.ndarray  # [N] int64
    a: np.ndarray  # [N] int64
    d: np.ndarray  # [N] int64

    @property
    def N(self) -> int:
        return int(self.E.size)

    @property
    def key(self) -> tuple[str, str]:
        return (self.site, self.local_date.isoformat())


def extract_t2_site_day(
    sessions: Sequence[Session],
    site_day: SiteDay,
    *,
    event_hour: int = T2_EVENT_HOUR,
    H: int = T2_H,
    min_remaining_kwh: float = T2_MIN_REMAINING_KWH,
    p_units: int = T2_P_UNITS,
    min_participants: int = T2_MIN_PARTICIPANTS,
) -> T2SiteDayData | None:
    """Extract T2 participant vectors ``(E, P, a, d)`` for one site-day, or ``None`` if ``N < 5``."""
    e_ts = site_day.event_timestamp(event_hour, 0)
    connected = sorted(
        sessions_connected_at(sessions, e_ts),
        key=lambda s: (s.connection_ts, s.session_id),
    )

    sids: list[str] = []
    E_list: list[int] = []
    d_list: list[int] = []
    for s in connected:
        rem = s.remaining_need_at(e_ts)
        if rem < min_remaining_kwh:
            continue
        d_i = min(int(H), int(math.floor((s.disconnect_ts - e_ts) / T2_SLOT_S)))
        if d_i <= 0:
            continue
        e_i = max(1, int(math.ceil(rem / T2_UNIT_KWH - 1e-12)))
        sids.append(s.session_id)
        E_list.append(e_i)
        d_list.append(d_i)

    n = len(E_list)
    if n < int(min_participants):
        return None

    E_arr = _ro(np.asarray(E_list, dtype=np.int64))
    P_arr = _ro(np.full(n, int(p_units), dtype=np.int64))
    a_arr = _ro(np.zeros(n, dtype=np.int64))
    d_arr = _ro(np.asarray(d_list, dtype=np.int64))
    return T2SiteDayData(
        site=site_day.site,
        local_date=site_day.local_date,
        timezone=site_day.timezone,
        n_cleaned_sessions=site_day.n_cleaned_sessions,
        session_ids=tuple(sids),
        E=E_arr,
        P=P_arr,
        a=a_arr,
        d=d_arr,
    )


def build_t2_site_days(
    sessions_by_site: Mapping[str, Sequence[Session]],
    *,
    min_sessions_per_day: int = MIN_SESSIONS_PER_DAY,
    min_participants: int = T2_MIN_PARTICIPANTS,
) -> list[T2SiteDayData]:
    """Return all T2-eligible site-days across sites, sorted by ``(site, date)``."""
    out: list[T2SiteDayData] = []
    for site in sorted(sessions_by_site.keys()):
        sess = sessions_by_site[site]
        days = eligible_site_days(sess, min_sessions=min_sessions_per_day)
        for sd in days:
            data = extract_t2_site_day(sess, sd, min_participants=min_participants)
            if data is not None:
                out.append(data)
    out.sort(key=lambda x: (x.site, x.local_date))
    return out


def site_real_limit_p99(
    sessions: Sequence[Session],
    site_days: Sequence[SiteDay],
    *,
    event_hour: int = T2_EVENT_HOUR,
    H: int = T2_H,
    slot_min: int = T2_SLOT_MIN,
    voltage_v: float = SITE_VOLTAGE_V,
) -> float:
    """Observed 99th-percentile aggregate charging power (kW = units) over ``[e, e + H*15m)``.

    For each eligible site-day and each 15-minute slot in the window, sums 1-minute LOCF
    charging currents across all cleaned sessions active at each minute, converts to kW at
    ``voltage_v`` (208 V), averages over the 15 minutes of the slot, and takes the 99th
    percentile over all ``len(site_days) * H`` slots.
    """
    if not site_days:
        return math.nan
    n_min_win = int(H) * int(slot_min)
    slot_powers_kw: list[np.ndarray] = []
    kw_per_amp = float(voltage_v) / 1000.0

    for sd in site_days:
        e_ts = sd.event_timestamp(event_hour, 0)
        end_ts = e_ts + n_min_win * 60.0
        minute_grid = e_ts + 60.0 * np.arange(n_min_win, dtype=np.float64)
        agg_amps = np.zeros(n_min_win, dtype=np.float64)
        for s in sessions:
            if s.disconnect_ts <= e_ts or s.connection_ts >= end_ts:
                continue
            agg_amps += s.current_at(minute_grid)
        slot_means_kw = agg_amps.reshape(int(H), int(slot_min)).mean(axis=1) * kw_per_amp
        slot_powers_kw.append(slot_means_kw)

    all_slots = np.concatenate(slot_powers_kw)
    return float(np.percentile(all_slots, 99.0))


def compute_site_real_limits(
    sessions_by_site: Mapping[str, Sequence[Session]],
    *,
    min_sessions_per_day: int = MIN_SESSIONS_PER_DAY,
) -> dict[str, float]:
    """Compute the observed 99th-percentile aggregate charging power (units) per site."""
    limits: dict[str, float] = {}
    for site in sorted(sessions_by_site.keys()):
        sess = sessions_by_site[site]
        days = eligible_site_days(sess, min_sessions=min_sessions_per_day)
        limits[site] = site_real_limit_p99(sess, days)
    return limits


def pick_site_day(seed: int, site_days: Sequence[T2SiteDayData]) -> T2SiteDayData:
    """Pick a site-day uniformly with replacement using stream ``acn_day``."""
    if not site_days:
        raise ValueError("site_days must be non-empty")
    idx = int(acn_stream(seed, "acn_day").integers(0, len(site_days)))
    return site_days[idx]


def build_acn_instance(
    seed: int,
    cell: Cell,
    site_day: T2SiteDayData,
    *,
    emp_beta_ab: tuple[float, float] | None = None,
    real_limit_units: float | None = None,
    redraw_prob: float | None = None,
    beta_q: tuple[float, float] | None = None,
    stream_salt: dict | None = None,
) -> Instance:
    """Build an ``Instance`` for ``(seed, cell, site_day)`` reusing the frozen F0-R generator.

    - ``N, E, P, a, d`` come from ``site_day``.
    - ``b_mean, b, cls, q, v, u, prior_A, prior_stuck, avail_mode, r`` are generated by
      calling ``papere.generator.generate_f0r(seed, cell, N=N)``.
    - ``L = (sum(E) / rho + sum(b_mean)) / H`` (frozen formula), or in the real-limit
      variant ``L = real_limit_units + sum(b_mean) / H`` so mean EV headroom equals
      ``real_limit_units`` with the same base-load fluctuations.
    - When ``emp_beta_ab = (alpha, beta)`` is supplied (T2-emp), ``q`` is drawn from
      ``Beta(alpha, beta)`` via child stream ``emp_q`` and ``prior_A``/``prior_stuck`` are
      rebuilt from the same ``prior_v``/``prior_u`` streams via ``chain_availability``.
    - ``redraw_prob`` and ``beta_q`` (round 3 M3 options) forward to ``generate_f0r`` and
      use disjoint streams (``redraw_u``, ``redraw_cls``, ``beta_q``); defaults reproduce
      the existing instances identically.
    """
    eff_rp = float(cell.redraw_prob if redraw_prob is None else redraw_prob)
    eff_bq = cell.beta_q if beta_q is None else beta_q
    if emp_beta_ab is not None and (eff_rp != 0.0 or eff_bq is not None):
        raise ValueError("emp_beta_ab cannot be combined with redraw_prob or beta_q")

    N = site_day.N
    H = T2_H
    salt = stream_salt or {}
    base = generate_f0r(
        seed,
        cell,
        N=N,
        stream_salt=stream_salt,
        redraw_prob=redraw_prob,
        beta_q=beta_q,
    )

    E = np.array(site_day.E, dtype=np.int64, copy=True)
    P = np.array(site_day.P, dtype=np.int64, copy=True)
    a = np.array(site_day.a, dtype=np.int64, copy=True)
    d = np.array(site_day.d, dtype=np.int64, copy=True)
    announced = (
        (np.arange(H)[None, :] >= a[:, None]) & (np.arange(H)[None, :] < d[:, None])
    ).astype(np.int64)

    cls = base.cls
    q = base.q
    prior_A = base.prior_A
    prior_stuck = base.prior_stuck

    if emp_beta_ab is not None and not cell.deterministic:
        alpha, beta = float(emp_beta_ab[0]), float(emp_beta_ab[1])
        if alpha <= 0.0 or beta <= 0.0:
            raise ValueError(f"emp_beta_ab must be positive, got {(alpha, beta)}")
        q_draw = np.clip(
            acn_stream(seed, "emp_q", salt.get("emp_q", 0)).beta(alpha, beta, size=N),
            0.0,
            1.0,
        )
        pv = stream(seed, "prior_v", salt.get("prior_v", 0)).random((N, M_MAX))
        pu = stream(seed, "prior_u", salt.get("prior_u", 0)).random((N, M_MAX, H))
        M = cell.M
        if cell.homogeneous_iid:
            prior_A = _ro(iid_availability(pv[:, :M], pu[:, :M], q_draw[:, None]))
        else:
            prior_A = _ro(chain_availability(pv[:, :M], pu[:, :M], q_draw[:, None], cell.r))
        prior_stuck = _ro(pv[:, :M] < q_draw[:, None])
        q = _ro(q_draw.astype(np.float64))
        cls = _ro(np.zeros(N, dtype=np.int64))

    if real_limit_units is None:
        l_val = (float(E.sum()) / float(cell.rho) + float(base.b_mean.sum())) / float(H)
    else:
        l_val = float(real_limit_units) + float(base.b_mean.sum()) / float(H)
    L = np.full((1, H), l_val, dtype=np.float64)

    return Instance(
        family=base.family,
        cell=cell,
        seed=int(seed),
        N=N,
        H=H,
        P=_ro(P),
        E=_ro(E),
        a=_ro(a),
        d=_ro(d),
        group=base.group,
        L=_ro(L),
        b_mean=base.b_mean,
        announced=_ro(announced),
        prior_A=prior_A,
        prior_stuck=prior_stuck,
        cls=cls,
        q=q,
        b=base.b,
        avail_mode=base.avail_mode,
        r=base.r,
        v=base.v,
        u=base.u,
    )


def instance_feasibility(inst: Instance) -> dict[str, bool]:
    """Check full-availability feasibility of ``inst`` under realized headroom ``L - b``."""
    a_full = np.ones((inst.N, inst.H), dtype=np.int64)
    fp = flow_problem(inst, a_full)
    f_all, _ = max_flow(fp)
    e_total = int(inst.E.sum())
    e_indiv = int(np.minimum(inst.E, inst.P * np.maximum(0, inst.d - inst.a)).sum())
    return {
        "feasible_strict": bool(f_all == e_total),
        "feasible_cap": bool(f_all == e_indiv),
        "feasible_headroom": bool((inst.L > inst.b).all()),
    }
