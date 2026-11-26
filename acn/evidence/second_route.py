"""Second-route check (PROTOCOL_ACN section 4), written independently of src/papere/acn.

Recomputes, from raw files and the row file only, with the standard library:
  1. the H1 share point estimate (M=3, delta=2 slots, rho=0.95);
  2. T1 pooled share of sessions in the regime at e=17:00, delta=30 min;
  3. T3 pooled failure-to-resume rate.
Usage: python3 -I second_route.py DATA_DIR RUN_DIR
"""
import datetime as dt
import gzip
import json
import math
import sys
from zoneinfo import ZoneInfo

GMT = "%a, %d %b %Y %H:%M:%S GMT"


def ts(s):
    return dt.datetime.strptime(s, GMT).replace(tzinfo=dt.timezone.utc).timestamp()


def clean(rows):
    out = []
    for r in rows:
        c, d = ts(r["connectionTime"]), ts(r["disconnectTime"])
        if d <= c or d - c > 86400 or (r.get("kWhDelivered") or 0) < 0.1:
            continue
        p, i = r.get("pilotSignal"), r.get("chargingCurrent")
        if not p or not i or not p.get("pilot") or not i.get("current"):
            continue
        out.append(r)
    return out


def need(r):
    for u in reversed(r.get("userInputs") or []):
        v = u.get("kWhRequested")
        if isinstance(v, (int, float)) and math.isfinite(v):
            return float(v), "requested"
    return float(r["kWhDelivered"]), "delivered"


def grid(times, vals, c, d):
    """1-minute grid from c, last value carried forward; None before the first sample."""
    pts = sorted(zip(times, vals))
    out, j, cur, t = [], 0, None, c
    while t < d:
        while j < len(pts) and pts[j][0] <= t:
            cur = pts[j][1]
            j += 1
        out.append((t, min(t + 60, d) - t, cur))
        t += 60
    return out


def series(r, key, field):
    s = r[key]
    return [ts(x) if isinstance(x, str) else float(x) for x in s["timestamps"]], [float(v) for v in s[field]]


def h1(run_dir):
    cell = "F0R_M3_dA2_db0_rho0.95_r0.3"
    by = {}
    for line in open(f"{run_dir}/t2_rows.jsonl"):
        r = json.loads(line)
        if r.get("cell_id") == cell and r.get("variant", "t2") == "t2" and r["policy"] in ("ce_llf", "pop_mpc", "guarded_mpc_e1"):
            by.setdefault(r["seed"], {})[r["policy"]] = r["R_avoid_kwh_per100"]
    seeds = [s for s in by if len(by[s]) == 3]
    m = {p: sum(by[s][p] for s in seeds) / len(seeds) for p in ("ce_llf", "pop_mpc", "guarded_mpc_e1")}
    return len(seeds), (m["ce_llf"] - m["pop_mpc"]) / (m["ce_llf"] - m["guarded_mpc_e1"])


def t1_and_t3(data_dir):
    tz = ZoneInfo("America/Los_Angeles")
    pop = reg = 0
    events = fails = 0
    for site in ("caltech", "jpl", "office001"):
        rows = clean(json.load(gzip.open(f"{data_dir}/acn_{site}.json.gz", "rt")))
        days = {}
        for r in rows:
            loc = dt.datetime.fromtimestamp(ts(r["connectionTime"]), tz)
            days.setdefault(loc.date(), []).append(r)
        eligible = {k for k, v in days.items() if k.weekday() < 5 and len(v) >= 10}
        # T1: sessions connected at 17:00 on an eligible site-day (any connection day)
        for day in eligible:
            e = dt.datetime.combine(day, dt.time(17, 0), tz).timestamp()
            for r in rows:
                c, d = ts(r["connectionTime"]), ts(r["disconnectTime"])
                if not (c <= e < d):
                    continue
                t, cur = series(r, "chargingCurrent", "current")
                g = grid(t, cur, c, d)
                tot = sum(w * (v or 0.0) for _, w, v in g)
                upto = sum(w * (v or 0.0) for s, w, v in g if s < e and s + w <= e) + sum(
                    (e - s) * (v or 0.0) for s, w, v in g if s < e < s + w)
                delivered = r["kWhDelivered"] * (upto / tot) if tot > 0 else r["kWhDelivered"] * (e - c) / (d - c)
                rem = need(r)[0] - delivered
                if rem < 0.25:
                    continue
                pop += 1
                if d - e < 30 * 60 + 15 * 60:
                    reg += 1
        # T3: resume events on all cleaned sessions
        for r in rows:
            n, src = need(r)
            if src != "requested":
                continue
            c, d = ts(r["connectionTime"]), ts(r["disconnectTime"])
            gp = grid(*series(r, "pilotSignal", "pilot"), c, d)
            gc = grid(*series(r, "chargingCurrent", "current"), c, d)
            tot = sum(w * (v or 0.0) for _, w, v in gc)
            cum, low, paused = [], 0, False
            acc = 0.0
            for (_, w, v) in gc:
                cum.append(acc)
                acc += w * (v or 0.0)
            k = 0
            while k < len(gp):
                p = gp[k][2]
                if p is not None and p <= 6:
                    low += 1
                    if low >= 15:
                        paused = True
                    k += 1
                    continue
                if paused and p is not None and p >= 8:
                    delivered = r["kWhDelivered"] * (cum[k] / tot) if tot > 0 else 0.0
                    win = range(k, k + 15)
                    ok = (gp[k][0] + 15 * 60 <= d and k + 15 <= len(gp)
                          and all(gp[j][2] is not None and gp[j][2] >= 8 for j in win))
                    if n - delivered >= 1 and ok:
                        events += 1
                        if all((gc[j][2] or 0.0) <= 1 for j in win):
                            fails += 1
                    paused, low = False, 0
                elif p is None or p > 6:
                    if not paused:
                        low = 0
                k += 1
    return pop, reg, events, fails


if __name__ == "__main__":
    data_dir, run_dir = sys.argv[1], sys.argv[2]
    n, share = h1(run_dir)
    pop, reg, ev, fa = t1_and_t3(data_dir)
    out = {"h1_seeds": n, "h1_share": round(share, 4), "t1_pop": pop, "t1_regime_30min": reg,
           "t1_share_30min": round(reg / pop, 4) if pop else None, "t3_events": ev, "t3_failures": fa,
           "t3_rate": round(fa / ev, 4) if ev else None}
    print(json.dumps(out, indent=1))
