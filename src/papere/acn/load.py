"""ACN-Data loading, cleaning, 1-minute resampling, delivered energy and site-days.

Implements section 0 of ``acn/PROTOCOL_ACN.md``:
- Read ``acn/data/acn_<site>.json.gz`` for sites ``caltech``, ``jpl``, ``office001``.
- Cleaning in order: drop if disconnect <= connection, duration > 24 h,
  kWhDelivered < 0.1, or pilot or current series missing.
- Local time via each session's ``timezone`` field.
- Energy need: last ``kWhRequested`` in ``userInputs`` if present, else ``kWhDelivered``
  (``need_source`` in ``{"requested", "delivered"}``).
- 1-minute resampling of pilot and current by carrying the last value forward,
  connected window only.
- Delivered energy up to time t: ``kWhDelivered * (int_0^t I) / (int_0^T I)``.
- Site-day: weekday (Monday-Friday) at one site with at least 10 cleaned sessions.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime
import gzip
import json
import math
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

import numpy as np

DEFAULT_SITES: tuple[str, ...] = ("caltech", "jpl", "office001")
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "acn" / "data"
DEFAULT_TIMEZONE = "America/Los_Angeles"
MAX_DURATION_S = 24.0 * 3600.0
MIN_KWH_DELIVERED = 0.1
MIN_SESSIONS_PER_DAY = 10

_DATE_EPOCH_CACHE: dict[str, float] = {}
_TZ_CACHE: dict[str, ZoneInfo] = {}


def _get_tz(name: str | None) -> ZoneInfo:
    key = name if name else DEFAULT_TIMEZONE
    tz = _TZ_CACHE.get(key)
    if tz is None:
        tz = ZoneInfo(key)
        _TZ_CACHE[key] = tz
    return tz


def parse_timestamp(value: str | float | int) -> float:
    """Parse an ACN timestamp string (RFC 2822 GMT or ISO-8601) to UTC epoch seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    s = value.strip()
    # Fast path for ACN-Data's standard RFC 2822 GMT format: 'Fri, 01 Nov 2019 14:13:26 GMT'
    if len(s) == 29 and s.endswith(" GMT") and s[19] == ":" and s[22] == ":":
        prefix = s[:17]
        base = _DATE_EPOCH_CACHE.get(prefix)
        if base is None:
            base = parsedate_to_datetime(prefix + "00:00:00 GMT").timestamp()
            _DATE_EPOCH_CACHE[prefix] = base
        try:
            hh = int(s[17:19])
            mm = int(s[20:22])
            ss = int(s[23:25])
            return base + hh * 3600.0 + mm * 60.0 + ss
        except ValueError:
            pass
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.timestamp()
    except (TypeError, ValueError):
        pass
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.timestamp()


def _parse_series(raw: dict | None, value_key: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Extract sorted finite (timestamps_epoch, values) from a pilot/current dict."""
    if not isinstance(raw, dict):
        return None
    ts_list = raw.get("timestamps")
    val_list = raw.get(value_key)
    if not ts_list or not val_list or len(ts_list) != len(val_list):
        return None
    ts_out: list[float] = []
    val_out: list[float] = []
    for t_raw, v_raw in zip(ts_list, val_list):
        if t_raw is None or v_raw is None:
            continue
        try:
            vf = float(v_raw)
            if not math.isfinite(vf):
                continue
            tf = parse_timestamp(t_raw)
        except (TypeError, ValueError):
            continue
        ts_out.append(tf)
        val_out.append(vf)
    if not ts_out:
        return None
    ts_arr = np.asarray(ts_out, dtype=np.float64)
    val_arr = np.asarray(val_out, dtype=np.float64)
    if ts_arr.size > 1 and np.any(ts_arr[:-1] > ts_arr[1:]):
        order = np.argsort(ts_arr, kind="mergesort")
        ts_arr = ts_arr[order]
        val_arr = val_arr[order]
    return ts_arr, val_arr


def resample_locf(raw_ts: np.ndarray, raw_vals: np.ndarray, grid_ts: np.ndarray) -> np.ndarray:
    """Resample ``(raw_ts, raw_vals)`` onto ``grid_ts`` by carrying the last value forward.

    Grid points strictly before the first sample receive ``np.nan``.
    """
    if raw_ts.size == 0 or grid_ts.size == 0:
        return np.full(grid_ts.shape, np.nan, dtype=np.float64)
    idx = np.searchsorted(raw_ts, grid_ts, side="right") - 1
    out = np.full(grid_ts.shape, np.nan, dtype=np.float64)
    valid = idx >= 0
    out[valid] = raw_vals[idx[valid]]
    return out


def extract_need(raw: dict, kwh_delivered: float) -> tuple[float, str]:
    """Return ``(need_kwh, need_source)`` per protocol section 0."""
    inputs = raw.get("userInputs")
    if isinstance(inputs, list):
        for entry in reversed(inputs):
            if not isinstance(entry, dict):
                continue
            req = entry.get("kWhRequested")
            if req is None:
                continue
            try:
                val = float(req)
            except (TypeError, ValueError):
                continue
            if math.isfinite(val):
                return val, "requested"
    return float(kwh_delivered), "delivered"


@dataclass
class CleaningReport:
    """Counts of sessions kept and dropped at each cleaning step (in protocol order)."""

    site: str
    raw_count: int = 0
    dropped_disconnect_le_connection: int = 0
    dropped_duration_gt_24h: int = 0
    dropped_kwh_lt_0_1: int = 0
    dropped_missing_series: int = 0
    kept_count: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "site": self.site,
            "raw_count": self.raw_count,
            "dropped_disconnect_le_connection": self.dropped_disconnect_le_connection,
            "dropped_duration_gt_24h": self.dropped_duration_gt_24h,
            "dropped_kwh_lt_0_1": self.dropped_kwh_lt_0_1,
            "dropped_missing_series": self.dropped_missing_series,
            "kept_count": self.kept_count,
        }


@dataclass
class Session:
    """One cleaned ACN session with 1-minute LOCF pilot/current arrays."""

    site: str
    session_id: str
    user_id: str | None
    timezone: str
    connection_ts: float
    disconnect_ts: float
    local_date: date
    kwh_delivered: float
    need_kwh: float
    need_source: str  # "requested" | "delivered"
    grid_ts: np.ndarray        # [M] UTC epoch seconds, conn + 60*k while < disconnect
    dt_s: np.ndarray           # [M] interval width in seconds (60.0 except possible last bin)
    pilot_1m: np.ndarray       # [M] float64 pilot signal (A), NaN before first sample
    current_1m: np.ndarray     # [M] float64 charging current (A), NaN before first sample
    _cum_area: np.ndarray = field(repr=False)  # [M+1] cumulative integral of max(current, 0) * dt_s
    _total_area: float = field(repr=False)

    @property
    def duration_s(self) -> float:
        return self.disconnect_ts - self.connection_ts

    def delivered_energy_at(self, t_ts: float) -> float:
        """Delivered energy (kWh) accumulated up to UTC epoch timestamp ``t_ts``."""
        if t_ts <= self.connection_ts:
            return 0.0
        if t_ts >= self.disconnect_ts:
            return self.kwh_delivered
        if self._total_area <= 0.0:
            frac = (t_ts - self.connection_ts) / self.duration_s
            return self.kwh_delivered * frac
        elapsed = t_ts - self.connection_ts
        k = int(elapsed // 60.0)
        n = self.grid_ts.size
        if k >= n:
            return self.kwh_delivered
        rem_s = min(max(elapsed - 60.0 * k, 0.0), float(self.dt_s[k]))
        c_k = float(self.current_1m[k])
        c_pos = c_k if (math.isfinite(c_k) and c_k > 0.0) else 0.0
        area = float(self._cum_area[k]) + c_pos * rem_s
        return self.kwh_delivered * (area / self._total_area)

    def remaining_need_at(self, t_ts: float) -> float:
        """Remaining energy need (kWh) at ``t_ts``: ``need_kwh - delivered_energy_at(t_ts)``."""
        return self.need_kwh - self.delivered_energy_at(t_ts)

    def current_at(self, query_ts: np.ndarray) -> np.ndarray:
        """Sample this session's 1-minute LOCF current at arbitrary UTC timestamps.

        Returns 0.0 outside ``[connection_ts, disconnect_ts)`` or where current is NaN.
        """
        q = np.asarray(query_ts, dtype=np.float64)
        out = np.zeros(q.shape, dtype=np.float64)
        inside = (q >= self.connection_ts) & (q < self.disconnect_ts)
        if not np.any(inside):
            return out
        k = np.floor((q[inside] - self.connection_ts) / 60.0).astype(np.int64)
        k = np.clip(k, 0, self.current_1m.size - 1)
        vals = self.current_1m[k]
        out[inside] = np.where(np.isfinite(vals) & (vals > 0.0), vals, 0.0)
        return out


@dataclass(frozen=True)
class SiteDay:
    """An eligible weekday site-day (at least 10 cleaned sessions)."""

    site: str
    local_date: date
    timezone: str
    n_cleaned_sessions: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.site, self.local_date.isoformat())

    def event_timestamp(self, hour: int, minute: int = 0) -> float:
        """UTC epoch seconds for local ``hour:minute`` on this site-day."""
        dt = datetime(
            self.local_date.year,
            self.local_date.month,
            self.local_date.day,
            int(hour),
            int(minute),
            0,
            tzinfo=_get_tz(self.timezone),
        )
        return dt.timestamp()


def clean_session(raw: dict, site: str, report: CleaningReport | None = None) -> Session | None:
    """Clean one raw ACN session dict in protocol order and resample to 1 minute."""
    if report is not None:
        report.raw_count += 1

    # 1. disconnect <= connection
    conn_raw = raw.get("connectionTime")
    disc_raw = raw.get("disconnectTime")
    if conn_raw is None or disc_raw is None:
        if report is not None:
            report.dropped_disconnect_le_connection += 1
        return None
    try:
        conn_ts = parse_timestamp(conn_raw)
        disc_ts = parse_timestamp(disc_raw)
    except (TypeError, ValueError):
        if report is not None:
            report.dropped_disconnect_le_connection += 1
        return None
    if disc_ts <= conn_ts:
        if report is not None:
            report.dropped_disconnect_le_connection += 1
        return None

    # 2. duration > 24 h
    if (disc_ts - conn_ts) > MAX_DURATION_S:
        if report is not None:
            report.dropped_duration_gt_24h += 1
        return None

    # 3. kWh delivered < 0.1
    kwh_raw = raw.get("kWhDelivered")
    try:
        kwh = float(kwh_raw)
    except (TypeError, ValueError):
        kwh = math.nan
    if not math.isfinite(kwh) or kwh < MIN_KWH_DELIVERED:
        if report is not None:
            report.dropped_kwh_lt_0_1 += 1
        return None

    # 4. pilot or current series missing
    pilot_parsed = _parse_series(raw.get("pilotSignal"), "pilot")
    current_parsed = _parse_series(raw.get("chargingCurrent"), "current")
    if pilot_parsed is None or current_parsed is None:
        if report is not None:
            report.dropped_missing_series += 1
        return None

    tz_name = str(raw.get("timezone") or DEFAULT_TIMEZONE)
    local_dt = datetime.fromtimestamp(conn_ts, tz=_get_tz(tz_name))
    local_d = local_dt.date()

    need_kwh, need_source = extract_need(raw, kwh)

    # 1-minute grid over connected window [conn_ts, disc_ts)
    dur = disc_ts - conn_ts
    n_min = max(1, int(math.ceil((dur - 1e-9) / 60.0)))
    grid_ts = conn_ts + 60.0 * np.arange(n_min, dtype=np.float64)
    dt_s = np.minimum(grid_ts + 60.0, disc_ts) - grid_ts

    pilot_1m = resample_locf(pilot_parsed[0], pilot_parsed[1], grid_ts)
    current_1m = resample_locf(current_parsed[0], current_parsed[1], grid_ts)

    cur_pos = np.where(np.isfinite(current_1m) & (current_1m > 0.0), current_1m, 0.0)
    bin_area = cur_pos * dt_s
    cum_area = np.empty(n_min + 1, dtype=np.float64)
    cum_area[0] = 0.0
    np.cumsum(bin_area, out=cum_area[1:])
    total_area = float(cum_area[-1])

    uid_raw = raw.get("userID")
    uid: str | None = None
    if uid_raw is not None:
        s_uid = str(uid_raw).strip()
        if s_uid:
            uid = s_uid

    sid = str(raw.get("sessionID") or raw.get("_id") or "")

    if report is not None:
        report.kept_count += 1

    return Session(
        site=site,
        session_id=sid,
        user_id=uid,
        timezone=tz_name,
        connection_ts=conn_ts,
        disconnect_ts=disc_ts,
        local_date=local_d,
        kwh_delivered=kwh,
        need_kwh=need_kwh,
        need_source=need_source,
        grid_ts=grid_ts,
        dt_s=dt_s,
        pilot_1m=pilot_1m,
        current_1m=current_1m,
        _cum_area=cum_area,
        _total_area=total_area,
    )


def load_raw_sessions(path: Path | str, *, max_sessions: int | None = None) -> list[dict]:
    """Read raw session list from an ACN ``.json.gz`` or ``.json`` file."""
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    items = payload if isinstance(payload, list) else payload.get("_items", [])
    if max_sessions is not None:
        return list(items[: int(max_sessions)])
    return list(items)


def load_site(
    site: str,
    data_dir: Path | str = DEFAULT_DATA_DIR,
    *,
    max_sessions: int | None = None,
) -> tuple[list[Session], CleaningReport]:
    """Load and clean sessions for ``site`` from ``<data_dir>/acn_<site>.json.gz``."""
    path = Path(data_dir) / f"acn_{site}.json.gz"
    raw_items = load_raw_sessions(path, max_sessions=max_sessions)
    return clean_sessions(raw_items, site=site)


def clean_sessions(
    raw_items: Iterable[dict],
    site: str,
) -> tuple[list[Session], CleaningReport]:
    """Clean an iterable of raw session dicts and return ``(sessions, report)``."""
    report = CleaningReport(site=site)
    cleaned: list[Session] = []
    for raw in raw_items:
        sess = clean_session(raw, site=site, report=report)
        if sess is not None:
            cleaned.append(sess)
    return cleaned, report


def load_all_sites(
    sites: Sequence[str] = DEFAULT_SITES,
    data_dir: Path | str = DEFAULT_DATA_DIR,
    *,
    max_sessions_per_site: int | None = None,
) -> tuple[dict[str, list[Session]], dict[str, CleaningReport]]:
    """Load and clean all requested sites."""
    by_site: dict[str, list[Session]] = {}
    reports: dict[str, CleaningReport] = {}
    for site in sites:
        sessions, rep = load_site(site, data_dir=data_dir, max_sessions=max_sessions_per_site)
        by_site[site] = sessions
        reports[site] = rep
    return by_site, reports


def eligible_site_days(
    sessions: Sequence[Session],
    *,
    min_sessions: int = MIN_SESSIONS_PER_DAY,
) -> list[SiteDay]:
    """Return weekday site-days with at least ``min_sessions`` cleaned sessions, sorted."""
    counts: dict[tuple[str, date], int] = defaultdict(int)
    tz_by_key: dict[tuple[str, date], str] = {}
    for s in sessions:
        key = (s.site, s.local_date)
        counts[key] += 1
        tz_by_key.setdefault(key, s.timezone)
    days: list[SiteDay] = []
    for (site, d), cnt in counts.items():
        if d.weekday() < 5 and cnt >= int(min_sessions):
            days.append(SiteDay(site=site, local_date=d, timezone=tz_by_key[(site, d)],
                                n_cleaned_sessions=cnt))
    days.sort(key=lambda sd: (sd.site, sd.local_date))
    return days


def sessions_connected_at(sessions: Sequence[Session], t_ts: float) -> list[Session]:
    """Return sessions connected at ``t_ts`` (``connection_ts <= t_ts < disconnect_ts``)."""
    return [s for s in sessions if s.connection_ts <= t_ts < s.disconnect_ts]
