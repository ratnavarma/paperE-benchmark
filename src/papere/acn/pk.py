"""Perth & Kinross EV charge session loading and cleaning (amendments 1, 2, and 3).

Implements ``acn/PROTOCOL_ACN_AMENDMENT_1.md``, ``acn/PROTOCOL_ACN_AMENDMENT_2.md``,
and ``acn/PROTOCOL_ACN_AMENDMENT_3.md``:
- Read ``acn/data_pk/pk_2018_19.csv`` (ChargePlace Scotland, Open Government Licence v3.0).
- Local time ``Europe/London``; ``Start Date + Start Time`` and ``End Date + End Time`` are
  local wall times with DST resolved via ``zoneinfo.ZoneInfo("Europe/London")``.
- Cleaning in protocol order:
  1. Keep only AC destination charger models (amendment 2):
     ``"APT 22kW Dual Outlet"``, ``"APT 22kW Raption"``,
     ``"Siemens 7 kW Dual Outlet"``, ``"APT 7kW Dual Outlet"``.
  2. Date repair (amendment 3, applied to Start Date and End Date before building
     timestamps): if a parsed date lies outside ``2018-09-01..2019-08-31`` and its day is
     ``<= 12``, swap day and month; if the result is still outside the range, drop the
     session (counted). If a swap makes the end precede the start, drop the session
     (counted). Drop if start/end timestamps are missing/unparseable or ``end <= start``.
  3. Drop if ``duration > 24 h``.
  4. Drop if ``Total kWh < 0.1`` (or missing/non-finite).
  5. Drop exact duplicate rows (all nine amendment 1 data fields equal).
- Produce ``papere.acn.load.Session`` records usable directly by T1 (and T2 code):
  ``need_kwh = Total kWh``, ``need_source = "delivered"``, linear delivered energy over
  ``[connection_ts, disconnect_ts]``, and empty pilot/current series.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date, datetime
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np

from .load import MAX_DURATION_S, MIN_KWH_DELIVERED, Session

DEFAULT_PK_CSV = Path(__file__).resolve().parents[3] / "acn" / "data_pk" / "pk_2018_19.csv"
DEFAULT_AMENDMENT_1_PATH = Path(__file__).resolve().parents[3] / "acn" / "PROTOCOL_ACN_AMENDMENT_1.md"
DEFAULT_AMENDMENT_2_PATH = Path(__file__).resolve().parents[3] / "acn" / "PROTOCOL_ACN_AMENDMENT_2.md"
DEFAULT_AMENDMENT_3_PATH = Path(__file__).resolve().parents[3] / "acn" / "PROTOCOL_ACN_AMENDMENT_3.md"

PK_TIMEZONE = "Europe/London"
PK_TZ = ZoneInfo(PK_TIMEZONE)
PK_WINDOW_START = date(2018, 9, 1)
PK_WINDOW_END = date(2019, 8, 31)

PK_AC_MODELS: frozenset[str] = frozenset(
    {
        "APT 22kW Dual Outlet",
        "APT 22kW Raption",
        "Siemens 7 kW Dual Outlet",
        "APT 7kW Dual Outlet",
    }
)

# The nine fields named in PROTOCOL_ACN_AMENDMENT_1.md (excluding the synthetic CSV `_id`).
PK_DATA_FIELDS: tuple[str, ...] = (
    "CP ID",
    "Connector",
    "Start Date",
    "Start Time",
    "End Date",
    "End Time",
    "Total kWh",
    "Site",
    "Model",
)

# Amendment 1 seed and bootstrap seed defaults.
PK_DEFAULT_SEEDS = "720000-720199"
PK_T1_BOOT_SEED = 720_500
PK_T2_BOOT_SEED = 721_000

_EMPTY_F64 = np.empty(0, dtype=np.float64)
_EMPTY_F64.flags.writeable = False
_ZERO_CUM = np.zeros(1, dtype=np.float64)
_ZERO_CUM.flags.writeable = False


def _parse_local_date(raw: str | None) -> date | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    if "T" in s:
        s = s.split("T", 1)[0]
    elif " " in s:
        s = s.split(" ", 1)[0]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _parse_local_time(raw: str | None) -> tuple[int, int, int] | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    parts = s.split(":")
    if len(parts) not in (2, 3):
        return None
    try:
        hh = int(parts[0])
        mm = int(parts[1])
        ss = int(parts[2]) if len(parts) == 3 else 0
    except ValueError:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return None
    return hh, mm, ss


def repair_pk_date(
    d: date,
    *,
    window_start: date = PK_WINDOW_START,
    window_end: date = PK_WINDOW_END,
) -> tuple[date | None, bool]:
    """Repair a parsed PK date per amendment 3.

    If ``d`` lies outside ``[window_start, window_end]`` and ``d.day <= 12``, swap day
    and month. Returns ``(repaired_date, was_swapped)``, where ``repaired_date`` is
    ``None`` when the date (after swapping if applicable) remains outside the window.
    """
    if window_start <= d <= window_end:
        return d, False
    if d.day <= 12:
        try:
            swapped = date(d.year, d.day, d.month)
        except ValueError:
            return None, False
        if window_start <= swapped <= window_end:
            return swapped, True
        return None, True
    return None, False


def _local_dt_to_utc(
    d: date,
    t: tuple[int, int, int],
    *,
    tz: ZoneInfo = PK_TZ,
    fold: int = 0,
) -> float:
    hh, mm, ss = t
    return datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=tz, fold=int(fold)).timestamp()


def _build_utc_start_end(
    d_start: date,
    t_start: tuple[int, int, int],
    d_end: date,
    t_end: tuple[int, int, int],
    *,
    tz: ZoneInfo = PK_TZ,
) -> tuple[float, float]:
    """Convert parsed start/end local dates and times to UTC epoch seconds with DST fold handling."""
    start_ts = _local_dt_to_utc(d_start, t_start, tz=tz, fold=0)
    end_ts = _local_dt_to_utc(d_end, t_end, tz=tz, fold=0)
    if end_ts <= start_ts:
        end_ts_fold1 = _local_dt_to_utc(d_end, t_end, tz=tz, fold=1)
        if end_ts_fold1 != end_ts and end_ts_fold1 > start_ts:
            end_ts = end_ts_fold1
    return start_ts, end_ts


def parse_pk_local_timestamp(
    date_str: str | None,
    time_str: str | None,
    *,
    tz: ZoneInfo = PK_TZ,
    fold: int = 0,
) -> float | None:
    """Combine a PK local wall date and time into UTC epoch seconds via ``zoneinfo``."""
    d = _parse_local_date(date_str)
    t = _parse_local_time(time_str)
    if d is None or t is None:
        return None
    return _local_dt_to_utc(d, t, tz=tz, fold=fold)


def parse_pk_start_end(
    start_date: str | None,
    start_time: str | None,
    end_date: str | None,
    end_time: str | None,
    *,
    tz: ZoneInfo = PK_TZ,
) -> tuple[float, float] | None:
    """Parse local start and end wall times to UTC epoch seconds.

    Uses ``fold=0`` by default; if the end wall time falls in an ambiguous DST fall-back
    hour and ``end(fold=0) <= start(fold=0)``, retries ``end`` with ``fold=1`` so a
    session spanning the repeated hour resolves chronologically.
    """
    d_start = _parse_local_date(start_date)
    t_start = _parse_local_time(start_time)
    d_end = _parse_local_date(end_date)
    t_end = _parse_local_time(end_time)
    if d_start is None or t_start is None or d_end is None or t_end is None:
        return None
    return _build_utc_start_end(d_start, t_start, d_end, t_end, tz=tz)


@dataclass
class PKCleaningReport:
    """Counts of PK rows kept, repaired, and dropped at each cleaning step."""

    site: str
    raw_count: int = 0
    dropped_non_ac_model: int = 0
    dropped_missing_or_invalid_ts: int = 0
    repaired_date_rows: int = 0
    repaired_start_date: int = 0
    repaired_end_date: int = 0
    dropped_date_outside_range: int = 0
    dropped_swap_end_lt_start: int = 0
    dropped_end_le_start: int = 0
    dropped_duration_gt_24h: int = 0
    dropped_kwh_lt_0_1: int = 0
    dropped_exact_duplicate: int = 0
    kept_count: int = 0

    @property
    def after_ac_filter(self) -> int:
        return self.raw_count - self.dropped_non_ac_model

    @property
    def after_end_gt_start(self) -> int:
        return (
            self.after_ac_filter
            - self.dropped_missing_or_invalid_ts
            - self.dropped_date_outside_range
            - self.dropped_swap_end_lt_start
            - self.dropped_end_le_start
        )

    @property
    def after_duration_le_24h(self) -> int:
        return self.after_end_gt_start - self.dropped_duration_gt_24h

    @property
    def after_kwh_ge_0_1(self) -> int:
        return self.after_duration_le_24h - self.dropped_kwh_lt_0_1

    def add(self, other: PKCleaningReport) -> None:
        """Accumulate counts from ``other`` into this report."""
        self.raw_count += other.raw_count
        self.dropped_non_ac_model += other.dropped_non_ac_model
        self.dropped_missing_or_invalid_ts += other.dropped_missing_or_invalid_ts
        self.repaired_date_rows += other.repaired_date_rows
        self.repaired_start_date += other.repaired_start_date
        self.repaired_end_date += other.repaired_end_date
        self.dropped_date_outside_range += other.dropped_date_outside_range
        self.dropped_swap_end_lt_start += other.dropped_swap_end_lt_start
        self.dropped_end_le_start += other.dropped_end_le_start
        self.dropped_duration_gt_24h += other.dropped_duration_gt_24h
        self.dropped_kwh_lt_0_1 += other.dropped_kwh_lt_0_1
        self.dropped_exact_duplicate += other.dropped_exact_duplicate
        self.kept_count += other.kept_count

    def as_dict(self) -> dict[str, int | str]:
        return {
            "site": self.site,
            "raw_count": self.raw_count,
            "dropped_non_ac_model": self.dropped_non_ac_model,
            "after_ac_filter": self.after_ac_filter,
            "dropped_missing_or_invalid_ts": self.dropped_missing_or_invalid_ts,
            "repaired_date_rows": self.repaired_date_rows,
            "repaired_start_date": self.repaired_start_date,
            "repaired_end_date": self.repaired_end_date,
            "dropped_date_outside_range": self.dropped_date_outside_range,
            "dropped_swap_end_lt_start": self.dropped_swap_end_lt_start,
            "dropped_end_le_start": self.dropped_end_le_start,
            "after_end_gt_start": self.after_end_gt_start,
            "dropped_duration_gt_24h": self.dropped_duration_gt_24h,
            "after_duration_le_24h": self.after_duration_le_24h,
            "dropped_kwh_lt_0_1": self.dropped_kwh_lt_0_1,
            "after_kwh_ge_0_1": self.after_kwh_ge_0_1,
            "dropped_exact_duplicate": self.dropped_exact_duplicate,
            "kept_count": self.kept_count,
        }


def _row_dedup_key(row: Mapping[str, str | None]) -> tuple[str, ...]:
    return tuple((row.get(k) or "").strip() for k in PK_DATA_FIELDS)


def clean_pk_rows(
    rows: Iterable[Mapping[str, str | None]],
    *,
    allowed_models: frozenset[str] = PK_AC_MODELS,
    sites: Sequence[str] | None = None,
    tz_name: str = PK_TIMEZONE,
    repair_dates: bool = True,
    window_start: date = PK_WINDOW_START,
    window_end: date = PK_WINDOW_END,
) -> tuple[dict[str, list[Session]], dict[str, PKCleaningReport]]:
    """Clean raw Perth & Kinross CSV row dicts and group ``Session`` objects by site.

    Cleaning order per amendments 1, 2, and 3:
    1. Model in ``allowed_models`` (AC destination chargers).
    2. Parse local wall dates and times; apply amendment 3 date repair (swap day/month
       when outside ``[window_start, window_end]`` and ``day <= 12``; drop if still
       outside range or if a swap makes ``end < start``); drop if ``end <= start``.
    3. ``duration <= 24 h``.
    4. ``Total kWh >= 0.1`` (finite).
    5. Exact duplicate rows (all nine amendment 1 data fields equal).
    """
    tz = ZoneInfo(tz_name)
    site_filter = {s.strip() for s in sites} if sites is not None else None
    sessions_by_site: dict[str, list[Session]] = defaultdict(list)
    reports_by_site: dict[str, PKCleaningReport] = {}
    seen_keys: set[tuple[str, ...]] = set()

    for idx, row in enumerate(rows, start=1):
        site = (row.get("Site") or "").strip()
        if site_filter is not None and site not in site_filter:
            continue
        rep = reports_by_site.get(site)
        if rep is None:
            rep = PKCleaningReport(site=site)
            reports_by_site[site] = rep
        rep.raw_count += 1

        # 1. Amendment 2: AC destination charger model filter
        model = (row.get("Model") or "").strip()
        if model not in allowed_models:
            rep.dropped_non_ac_model += 1
            continue

        # 2. Local wall dates/times, amendment 3 date repair -> UTC epoch
        d_start = _parse_local_date(row.get("Start Date"))
        t_start = _parse_local_time(row.get("Start Time"))
        d_end = _parse_local_date(row.get("End Date"))
        t_end = _parse_local_time(row.get("End Time"))
        if d_start is None or t_start is None or d_end is None or t_end is None:
            rep.dropped_missing_or_invalid_ts += 1
            continue

        start_swapped = False
        end_swapped = False
        if repair_dates:
            d_start_rep, start_swapped = repair_pk_date(
                d_start, window_start=window_start, window_end=window_end
            )
            d_end_rep, end_swapped = repair_pk_date(
                d_end, window_start=window_start, window_end=window_end
            )
            if d_start_rep is None or d_end_rep is None:
                rep.dropped_date_outside_range += 1
                continue
            d_start, d_end = d_start_rep, d_end_rep
            if start_swapped:
                rep.repaired_start_date += 1
            if end_swapped:
                rep.repaired_end_date += 1
            if start_swapped or end_swapped:
                rep.repaired_date_rows += 1

        conn_ts, disc_ts = _build_utc_start_end(d_start, t_start, d_end, t_end, tz=tz)
        if (start_swapped or end_swapped) and disc_ts < conn_ts:
            rep.dropped_swap_end_lt_start += 1
            continue
        if disc_ts <= conn_ts:
            rep.dropped_end_le_start += 1
            continue

        # 3. duration > 24 h
        if (disc_ts - conn_ts) > MAX_DURATION_S:
            rep.dropped_duration_gt_24h += 1
            continue

        # 4. Total kWh < 0.1
        kwh_raw = (row.get("Total kWh") or "").strip()
        try:
            kwh = float(kwh_raw)
        except ValueError:
            kwh = math.nan
        if not math.isfinite(kwh) or kwh < MIN_KWH_DELIVERED:
            rep.dropped_kwh_lt_0_1 += 1
            continue

        # 5. Exact duplicate rows (all nine amendment 1 fields equal)
        key = _row_dedup_key(row)
        if key in seen_keys:
            rep.dropped_exact_duplicate += 1
            continue
        seen_keys.add(key)

        local_d = datetime.fromtimestamp(conn_ts, tz=tz).date()
        raw_id = (row.get("_id") or "").strip()
        sid = raw_id if raw_id else f"pk_{idx}"

        rep.kept_count += 1
        sessions_by_site[site].append(
            Session(
                site=site,
                session_id=sid,
                user_id=None,
                timezone=tz_name,
                connection_ts=conn_ts,
                disconnect_ts=disc_ts,
                local_date=local_d,
                kwh_delivered=kwh,
                need_kwh=kwh,
                need_source="delivered",
                grid_ts=_EMPTY_F64,
                dt_s=_EMPTY_F64,
                pilot_1m=_EMPTY_F64,
                current_1m=_EMPTY_F64,
                _cum_area=_ZERO_CUM,
                _total_area=0.0,
            )
        )

    sorted_sites = sorted(reports_by_site.keys())
    out_sessions = {s: sessions_by_site.get(s, []) for s in sorted_sites}
    out_reports = {s: reports_by_site[s] for s in sorted_sites}
    return out_sessions, out_reports


def summarize_pk_cleaning(reports: Mapping[str, PKCleaningReport]) -> PKCleaningReport:
    """Aggregate per-site ``PKCleaningReport`` objects into a single pooled report."""
    total = PKCleaningReport(site="pooled")
    for rep in reports.values():
        total.add(rep)
    return total


def read_pk_csv(path: Path | str = DEFAULT_PK_CSV, *, max_rows: int | None = None) -> list[dict[str, str]]:
    """Read raw rows from the Perth & Kinross CSV file."""
    p = Path(path)
    out: list[dict[str, str]] = []
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            out.append(dict(row))
            if max_rows is not None and len(out) >= int(max_rows):
                break
    return out


def load_pk_sites(
    csv_path: Path | str = DEFAULT_PK_CSV,
    *,
    sites: Sequence[str] | None = None,
    allowed_models: frozenset[str] = PK_AC_MODELS,
    repair_dates: bool = True,
    max_rows: int | None = None,
    max_sessions_per_site: int | None = None,
) -> tuple[dict[str, list[Session]], dict[str, PKCleaningReport]]:
    """Load and clean Perth & Kinross sessions from ``csv_path``, grouped by ``Site``."""
    raw_rows = read_pk_csv(csv_path, max_rows=max_rows)
    by_site, reports = clean_pk_rows(
        raw_rows,
        allowed_models=allowed_models,
        sites=sites,
        repair_dates=repair_dates,
    )
    if max_sessions_per_site is not None:
        cap = int(max_sessions_per_site)
        by_site = {s: sess[:cap] for s, sess in by_site.items()}
    return by_site, reports
