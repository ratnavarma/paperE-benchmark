"""POST HOC (explanatory, external review of draft 3), from the registered T2 rows only, reference cell (M=3, 30 min, rho 0.95):
(M4) site-day cluster bootstrap interval for the registered shared-rate share;
(B4) mean remaining need (obligation), residual as share of need, targeted gain per vehicle (kWh) and as share of need;
(M10) avoidable deadline misses per 100 (planner minus the clairvoyant bound row).
10,000 resamples, seed 750000."""
import json, random
R = "/Users/ratnavarma/08_Experiments/paperE/results/acn/"
CELL = "F0R_M3_dA2_db0_rho0.95_r0.3"; P3 = ("ce_llf", "pop_mpc", "guarded_mpc_e1")
def load(run):
    by = {}
    for l in open(R + run + "/t2_rows.jsonl"):
        r = json.loads(l)
        if r.get("cell_id") != CELL or r.get("variant", "t2") != "t2": continue
        d = by.setdefault(r["seed"], {"day": (r.get("site"), r.get("date"))})
        if r["policy"] in P3 + ("bound",): d[r["policy"]] = r
    return [v for v in by.values() if all(p in v for p in P3 + ("bound",))]
def share(rs):
    m = lambda p: sum(r[p]["R_avoid_kwh_per100"] for r in rs) / len(rs)
    return (m("ce_llf") - m("pop_mpc")) / (m("ce_llf") - m("guarded_mpc_e1"))
def ci(xs): xs = sorted(xs); return [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]]
rng = random.Random(750000); out = {}
for ds, run in (("acn", "registered_2026-11-26"), ("pa", "pa_registered_2026-11-26")):
    rows = load(run); days = {}
    for r in rows: days.setdefault(r["day"], []).append(r)
    keys = list(days)
    bs = [share([x for k in (rng.choice(keys) for _ in keys) for x in days[k]]) for _ in range(10000)]
    out[f"{ds}_share_cluster"] = {"value": share(rows), "interval": ci(bs), "n": len(keys)}
    n = len(rows)
    need = sum(r["bound"]["E_kwh_per100"] for r in rows) / n
    out[f"{ds}_need_kwh_per100"] = {"value": need, "interval": None}
    for p, nm in zip(P3, ("ce_llf", "shared", "targeted")):
        out[f"{ds}_resid_share_of_need_{nm}"] = {"value": sum(r[p]["R_avoid_kwh_per100"] for r in rows) / n / need, "interval": None}
        out[f"{ds}_avoidable_misses_{nm}"] = {"value": sum(r[p]["deadline_miss_count_per100"] - r["bound"]["deadline_miss_count_per100"] for r in rows) / n, "interval": None}
    g = sum(r["ce_llf"]["R_avoid_kwh"] - r["guarded_mpc_e1"]["R_avoid_kwh"] for r in rows) / sum(r["ce_llf"]["N"] for r in rows)
    out[f"{ds}_gain_targeted_kwh_per_vehicle"] = {"value": g, "interval": None}
    out[f"{ds}_gain_targeted_share_of_need"] = {"value": (sum(r["ce_llf"]["R_avoid_kwh_per100"] - r["guarded_mpc_e1"]["R_avoid_kwh_per100"] for r in rows) / n) / need, "interval": None}
json.dump(out, open("posthoc_round3.json", "w"), indent=1)
for k, v in out.items(): print(k, round(v["value"], 4), [round(x, 3) for x in v["interval"]] if v["interval"] else "")
