"""POST HOC (explanatory, not registered), round 2 of review:
(1) difference between the ACN and Palo Alto shared-rate shares at the reference cell, independent bootstrap over seeds;
(2) absolute paired gains (kWh per 100) of the shared-rate and targeted planners over CE-LLF at 15 and 60 minutes under the
tight limit, cluster bootstrap over site-days. 10,000 resamples, seed 740000."""
import json, random, sys
R = "/Users/ratnavarma/08_Experiments/paperE/results/acn/"
KEY = "R_avoid_kwh_per100"
def load(run, cell):
    by = {}
    for l in open(R + run + "/t2_rows.jsonl"):
        r = json.loads(l)
        if r.get("cell_id") == cell and r.get("variant", "t2") == "t2" and r["policy"] in ("ce_llf", "pop_mpc", "guarded_mpc_e1"):
            d = by.setdefault(r["seed"], {"day": (r.get("site"), r.get("date"))}); d[r["policy"]] = r[KEY]
    return [v for v in by.values() if len(v) == 4]
def share(rows):
    m = lambda p: sum(r[p] for r in rows) / len(rows)
    return (m("ce_llf") - m("pop_mpc")) / (m("ce_llf") - m("guarded_mpc_e1"))
def ci(xs): xs = sorted(xs); return [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]]
rng = random.Random(740000); B = 10000; out = {}
ref = "F0R_M3_dA2_db0_rho0.95_r0.3"
a, p = load("registered_2026-11-26", ref), load("pa_registered_2026-11-26", ref)
diffs = [share([rng.choice(p) for _ in p]) - share([rng.choice(a) for _ in a]) for _ in range(B)]
out["site_diff_pa_minus_acn"] = {"value": share(p) - share(a), "interval": ci(diffs)}
for ds, run in (("acn", "registered_2026-11-26"), ("pa", "pa_registered_2026-11-26")):
    for dA, mins in ((1, 15), (4, 60)):
        rows = load(run, f"F0R_M3_dA{dA}_db0_rho1.15_r0.3")
        days = {}
        for r in rows: days.setdefault(r["day"], []).append(r)
        keys = list(days)
        def gains(rs):
            n = len(rs); return (sum(r["ce_llf"] - r["pop_mpc"] for r in rs) / n, sum(r["ce_llf"] - r["guarded_mpc_e1"] for r in rs) / n)
        bs = []
        for _ in range(B):
            rs = [x for k in (rng.choice(keys) for _ in keys) for x in days[k]]
            bs.append(gains(rs))
        g = gains(rows)
        out[f"{ds}_gain_shared_d{mins}"] = {"value": g[0], "interval": ci([b[0] for b in bs])}
        out[f"{ds}_gain_targeted_d{mins}"] = {"value": g[1], "interval": ci([b[1] for b in bs])}
        out[f"{ds}_n_sitedays_d{mins}"] = {"value": len(keys), "interval": None}
json.dump(out, open("posthoc_round2.json", "w"), indent=1)
print(json.dumps({k: (round(v["value"], 3), [round(x, 3) for x in v["interval"]] if v["interval"] else None) for k, v in out.items()}, indent=1))
