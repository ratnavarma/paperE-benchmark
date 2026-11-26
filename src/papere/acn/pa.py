"""City of Palo Alto EV charge session loading and cleaning (amendment 4).

Implements ``acn/PROTOCOL_ACN_AMENDMENT_4.md``:
- Read ``acn/data_pa/pa_download.bin`` (CSV export of data.paloalto.gov dataset 194693,
  portal-wide Open Data Commons PDDL).
- Window: sessions starting ``2019-11-01`` to ``2020-02-29`` local (``America/Los_Angeles``).
- Timestamps: built using ``Start Time Zone`` / ``End Time Zone`` when present
  (``PST``, ``PDT``, ``UTC``, ``GMT``, or IANA zone names), otherwise treated as local
  wall time in ``America/Los_Angeles`` (with DST fold handling).
- Site: ``Address 1`` (street address; stations at the same address form one site).
- Energy need: ``Energy (kWh)``, ``need_source = "delivered"``, linear delivered energy
  over ``[connection_ts, disconnect_ts]``, and empty pilot/current series.
- Cleaning (in order):
  1. Parse start timestamp; drop if missing/unparseable (counted).
  2. Filter to local start date in ``[2019-11-01, 2020-02-29]`` (out-of-window counted).
  3. Parse end timestamp and ``Energy (kWh)``; drop if end, energy, or site is
     missing/invalid (counted).
  4. Drop if ``end <= start``.
  5. Drop if ``duration > 24 h``.
  6. Drop if ``Energy (kWh) < 0.1``.
  7. Drop exact duplicate rows (all CSV fields equal).
- Produces ``papere.acn.load.Session`` records usable directly by T1 and T2 code.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np

from .load import MAX_DURATION_S, MIN_KWH_DELIVERED, Session

DEFAULT_PA_CSV = Path(__file__).resolve().parents[3] / "acn" / "data_pa" / "pa_download.bin"
DEFAULT_AMENDMENT_3_PATH = Path(__file__).resolve().parents[3] / "acn" / "PROTOCOL_ACN_AMENDMENT_3.md"
DEFAULT_AMENDMENT_4_PATH = Path(__file__).resolve().parents[3] / "acn" / "PROTOCOL_ACN_AMENDMENT_4.md"

PA_TIMEZONE = "America/Los_Angeles"
PA_TZ = ZoneInfo(PA_TIMEZONE)
PA_WINDOW_START = date(2019, 11, 1)
PA_WINDOW_END = date(2020, 2, 29)

# Amendment 4 seed, bootstrap seed, and T2 eligibility gate defaults.
PA_DEFAULT_SEEDS = "730000-730199"
PA_T1_BOOT_SEED = 730_500
PA_T2_BOOT_SEED = 731_000
PA_MIN_T2_SITE_DAYS = 20

_FIXED_TZ_OFFSETS: dict[str, timezone] = {
    "PST": timezone(timedelta(hours=-8)),
    "PDT": timezone(timedelta(hours=-7)),
    "UTC": timezone.utc,
    "GMT": timezone.utc,
}

_DT_FORMATS: tuple[str, ...] = (
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)

_EMPTY_F64 = np.empty(0, dtype=np.float64)
_EMPTY_F64.flags.writeable = False
_ZERO_CUM = np.zeros(1, dtype=np.float64)
_ZERO_CUM.flags.writeable = False


def _parse_naive_datetime(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    if "T" in s:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
        except ValueError:
            return None
    return None


def parse_pa_timestamp(
    dt_str: str | None,
    tz_str: str | None = None,
    *,
    tz: ZoneInfo = PA_TZ,
    fold: int = 0,
) -> float | None:
    """Parse a Palo Alto date-time string and optional time-zone tag to UTC epoch seconds.

    Uses ``tz_str`` (``PST``, ``PDT``, ``UTC``, ``GMT``, or an IANA zone name) when
    present; otherwise interprets ``dt_str`` as local wall time in ``tz``.
    """
    dt_naive = _parse_naive_datetime(dt_str)
    if dt_naive is None:
        return None
    tz_raw = (tz_str or "").strip()
    if not tz_raw:
        return dt_naive.replace(tzinfo=tz, fold=int(fold)).timestamp()
    fixed = _FIXED_TZ_OFFSETS.get(tz_raw.upper())
    if fixed is not None:
        return dt_naive.replace(tzinfo=fixed).timestamp()
    try:
        z = ZoneInfo(tz_raw)
    except ZoneInfoNotFoundError:
        return None
    return dt_naive.replace(tzinfo=z, fold=int(fold)).timestamp()


def parse_pa_start_end(
    start_str: str | None,
    start_tz: str | None,
    end_str: str | None,
    end_tz: str | None,
    *,
    tz: ZoneInfo = PA_TZ,
) -> tuple[float | None, float | None]:
    """Parse Palo Alto start and end timestamps to UTC epoch seconds.

    If ``end_tz`` is empty (local wall time fallback) and ``end(fold=0) <= start``,
    retries ``end`` with ``fold=1`` for ambiguous DST fall-back hours.
    """
    start_ts = parse_pa_timestamp(start_str, start_tz, tz=tz, fold=0)
    end_ts = parse_pa_timestamp(end_str, end_tz, tz=tz, fold=0)
    if (
        start_ts is not None
        and end_ts is not None
        and end_ts <= start_ts
        and not (end_tz or "").strip()
    ):
        end_ts_fold1 = parse_pa_timestamp(end_str, end_tz, tz=tz, fold=1)
        if end_ts_fold1 is not None and end_ts_fold1 != end_ts and end_ts_fold1 > start_ts:
            end_ts = end_ts_fold1
    return start_ts, end_ts


@dataclass
class PACleaningReport:
    """Counts of Palo Alto rows kept and dropped at each cleaning step."""

    site: str
    raw_count: int = 0
    dropped_missing_or_invalid_start: int = 0
    dropped_outside_window: int = 0
    dropped_missing_or_invalid_end: int = 0
    dropped_missing_or_invalid_energy: int = 0
    dropped_missing_site: int = 0
    dropped_end_le_start: int = 0
    dropped_duration_gt_24h: int = 0
    dropped_kwh_lt_0_1: int = 0
    dropped_exact_duplicate: int = 0
    kept_count: int = 0

    @property
    def in_window_count(self) -> int:
        return (
            self.raw_count
            - self.dropped_missing_or_invalid_start
            - self.dropped_outside_window
        )

    @property
    def dropped_missing_start_end_or_energy(self) -> int:
        return (
            self.dropped_missing_or_invalid_start
            + self.dropped_missing_or_invalid_end
            + self.dropped_missing_or_invalid_energy
        )

    @property
    def after_end_gt_start(self) -> int:
        return (
            self.in_window_count
            - self.dropped_missing_or_invalid_end
            - self.dropped_missing_or_invalid_energy
            - self.dropped_missing_site
            - self.dropped_end_le_start
        )

    @property
    def after_duration_le_24h(self) -> int:
        return self.after_end_gt_start - self.dropped_duration_gt_24h

    @property
    def after_kwh_ge_0_1(self) -> int:
        return self.after_duration_le_24h - self.dropped_kwh_lt_0_1

    def add(self, other: PACleaningReport) -> None:
        """Accumulate counts from ``other`` into this report."""
        self.raw_count += other.raw_count
        self.dropped_missing_or_invalid_start += other.dropped_missing_or_invalid_start
        self.dropped_outside_window += other.dropped_outside_window
        self.dropped_missing_or_invalid_end += other.dropped_missing_or_invalid_end
        self.dropped_missing_or_invalid_energy += other.dropped_missing_or_invalid_energy
        self.dropped_missing_site += other.dropped_missing_site
        self.dropped_end_le_start += other.dropped_end_le_start
        self.dropped_duration_gt_24h += other.dropped_duration_gt_24h
        self.dropped_kwh_lt_0_1 += other.dropped_kwh_lt_0_1
        self.dropped_exact_duplicate += other.dropped_exact_duplicate
        self.kept_count += other.kept_count

    def as_dict(self) -> dict[str, int | str]:
        return {
            "site": self.site,
            "raw_count": self.raw_count,
            "dropped_missing_or_invalid_start": self.dropped_missing_or_invalid_start,
            "dropped_outside_window": self.dropped_outside_window,
            "in_window_count": self.in_window_count,
            "dropped_missing_or_invalid_end": self.dropped_missing_or_invalid_end,
            "dropped_missing_or_invalid_energy": self.dropped_missing_or_invalid_energy,
            "dropped_missing_start_end_or_energy": self.dropped_missing_start_end_or_energy,
            "dropped_missing_site": self.dropped_missing_site,
            "dropped_end_le_start": self.dropped_end_le_start,
            "after_end_gt_start": self.after_end_gt_start,
            "dropped_duration_gt_24h": self.dropped_duration_gt_24h,
            "after_duration_le_24h": self.after_duration_le_24h,
            "dropped_kwh_lt_0_1": self.dropped_kwh_lt_0_1,
            "after_kwh_ge_0_1": self.after_kwh_ge_0_1,
            "dropped_exact_duplicate": self.dropped_exact_duplicate,
            "kept_count": self.kept_count,
        }


def _row_dedup_key(
    row: Mapping[str, str | None],
    fieldnames: tuple[str, ...] | None,
) -> tuple[tuple[str, str], ...] | tuple[str, ...]:
    if fieldnames is not None:
        return tuple((row.get(k) or "").strip() for k in fieldnames)
    return tuple((k, (row.get(k) or "").strip()) for k in sorted(row.keys()))


def clean_pa_rows(
    rows: Iterable[Mapping[str, str | None]],
    *,
    fieldnames: Sequence[str] | None = None,
    sites: Sequence[str] | None = None,
    window_start: date = PA_WINDOW_START,
    window_end: date = PA_WINDOW_END,
    tz_name: str = PA_TIMEZONE,
) -> tuple[dict[str, list[Session]], dict[str, PACleaningReport]]:
    """Clean raw Palo Alto CSV row dicts and group ``Session`` objects by ``Address 1``.

    Returns ``(sessions_by_site, reports_by_site)`` where ``sessions_by_site`` contains
    every non-empty site with at least one in-window row, and ``reports_by_site`` tracks
    counts for all encountered sites so ``summarize_pa_cleaning(reports_by_site)``
    accounts for every input row.
    """
    tz = ZoneInfo(tz_name)
    site_filter = {s.strip() for s in sites} if sites is not None else None
    dedup_fields = tuple(fieldnames) if fieldnames is not None else None
    sessions_by_site: dict[str, list[Session]] = defaultdict(list)
    reports_by_site: dict[str, PACleaningReport] = {}
    seen_keys: set[tuple] = set()

    for idx, row in enumerate(rows, start=1):
        site = (row.get("Address 1") or "").strip()
        if site_filter is not None and site not in site_filter:
            continue
        rep = reports_by_site.get(site)
        if rep is None:
            rep = PACleaningReport(site=site)
            reports_by_site[site] = rep
        rep.raw_count += 1

        # 1. Parse Start Date + Start Time Zone
        start_tz_raw = row.get("Start Time Zone")
        conn_ts = parse_pa_timestamp(row.get("Start Date"), start_tz_raw, tz=tz, fold=0)
        if conn_ts is None:
            rep.dropped_missing_or_invalid_start += 1
            continue

        # 2. Local window filter (2019-11-01..2020-02-29 America/Los_Angeles)
        local_d = datetime.fromtimestamp(conn_ts, tz=tz).date()
        if not (window_start <= local_d <= window_end):
            rep.dropped_outside_window += 1
            continue

        # 3. Missing/invalid end, energy, or site
        end_tz_raw = row.get("End Time Zone")
        disc_ts = parse_pa_timestamp(row.get("End Date"), end_tz_raw, tz=tz, fold=0)
        if disc_ts is None:
            rep.dropped_missing_or_invalid_end += 1
            continue
        if disc_ts <= conn_ts and not (end_tz_raw or "").strip():
            disc_ts_fold1 = parse_pa_timestamp(row.get("End Date"), end_tz_raw, tz=tz, fold=1)
            if disc_ts_fold1 is not None and disc_ts_fold1 != disc_ts and disc_ts_fold1 > conn_ts:
                disc_ts = disc_ts_fold1

        kwh_raw = (row.get("Energy (kWh)") or "").strip()
        if not kwh_raw:
            rep.dropped_missing_or_invalid_energy += 1
            continue
        try:
            kwh = float(kwh_raw)
        except ValueError:
            kwh = math.nan
        if not math.isfinite(kwh):
            rep.dropped_missing_or_invalid_energy += 1
            continue

        if not site:
            rep.dropped_missing_site += 1
            continue

        # 4. Base §0: disconnect <= connection
        if disc_ts <= conn_ts:
            rep.dropped_end_le_start += 1
            continue

        # 5. Base §0: duration > 24 h
        if (disc_ts - conn_ts) > MAX_DURATION_S:
            rep.dropped_duration_gt_24h += 1
            continue

        # 6. Base §0: kWh delivered < 0.1
        if kwh < MIN_KWH_DELIVERED:
            rep.dropped_kwh_lt_0_1 += 1
            continue

        # 7. Exact duplicate rows (all CSV fields equal)
        key = _row_dedup_key(row, dedup_fields)
        if key in seen_keys:
            rep.dropped_exact_duplicate += 1
            continue
        seen_keys.add(key)

        station = (row.get("Station Name") or "").strip()
        ev_id = (row.get("Plug In Event Id") or "").strip()
        if station and ev_id:
            sid = f"{station}:{ev_id}"
        elif ev_id:
            sid = ev_id
        else:
            sid = f"pa_{idx}"

        uid_raw = (row.get("User ID") or "").strip()
        uid = uid_raw if uid_raw else None

        rep.kept_count += 1
        sessions_by_site[site].append(
            Session(
                site=site,
                session_id=sid,
                user_id=uid,
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

    active_sites = sorted(
        s for s, rep in reports_by_site.items() if s and rep.in_window_count > 0
    )
    out_sessions = {s: sessions_by_site.get(s, []) for s in active_sites}
    out_reports = {s: reports_by_site[s] for s in sorted(reports_by_site.keys())}
    return out_sessions, out_reports


def summarize_pa_cleaning(reports: Mapping[str, PACleaningReport]) -> PACleaningReport:
    """Aggregate per-site ``PACleaningReport`` objects into a single pooled report."""
    total = PACleaningReport(site="pooled")
    for rep in reports.values():
        total.add(rep)
    return total


def iter_pa_csv(
    path: Path | str = DEFAULT_PA_CSV,
    *,
    max_rows: int | None = None,
) -> Iterator[dict[str, str]]:
    """Stream raw rows from the Palo Alto CSV file."""
    p = Path(path)
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for n, row in enumerate(reader, start=1):
            yield dict(row)
            if max_rows is not None and n >= int(max_rows):
                break


def read_pa_csv(
    path: Path | str = DEFAULT_PA_CSV,
    *,
    max_rows: int | None = None,
) -> list[dict[str, str]]:
    """Read raw rows from the Palo Alto CSV file into a list."""
    return list(iter_pa_csv(path, max_rows=max_rows))


def load_pa_sites(
    csv_path: Path | str = DEFAULT_PA_CSV,
    *,
    sites: Sequence[str] | None = None,
    window_start: date = PA_WINDOW_START,
    window_end: date = PA_WINDOW_END,
    max_rows: int | None = None,
    max_sessions_per_site: int | None = None,
) -> tuple[dict[str, list[Session]], dict[str, PACleaningReport]]:
    """Load and clean Palo Alto sessions from ``csv_path``, grouped by ``Address 1``."""
    p = Path(csv_path)
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or ())
        if max_rows is None:
            row_iter: Iterable[dict[str, str]] = reader
        else:
            limit = int(max_rows)
            row_iter = (row for i, row in enumerate(reader) if i < limit)
        by_site, reports = clean_pa_rows(
            row_iter,
            fieldnames=fieldnames if fieldnames else None,
            sites=sites,
            window_start=window_start,
            window_end=window_end,
        )
    if max_sessions_per_site is not None:
        cap = int(max_sessions_per_site)
        by_site = {s: sess[:cap] for s, sess in by_site.items()}
    return by_site, reports
