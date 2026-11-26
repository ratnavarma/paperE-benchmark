"""POST HOC diagnostic (not registered): for T3 resume events, does the vehicle draw current later,
and how does delivered energy compare with the request? Explains, never carries a claim."""
import json, gzip, sys
sys.path.insert(0, ".")
from second_route import clean, need, grid, series, ts
later = never = 0; ratio = []
for site in ("caltech", "jpl", "office001"):
    for r in clean(json.load(gzip.open(f"data/acn_{site}.json.gz", "rt"))):
        n, src = need(r)
        if src != "requested": continue
        c, d = ts(r["connectionTime"]), ts(r["disconnectTime"])
        gp = grid(*series(r, "pilotSignal", "pilot"), c, d); gc = grid(*series(r, "chargingCurrent", "current"), c, d)
        tot = sum(w * (v or 0) for _, w, v in gc); cum, acc = [], 0.0
        for _, w, v in gc: cum.append(acc); acc += w * (v or 0)
        low = 0; paused = False; k = 0
        while k < len(gp):
            p = gp[k][2]
            if p is not None and p <= 6:
                low += 1; paused = paused or low >= 15; k += 1; continue
            if paused and p is not None and p >= 8:
                delivered = r["kWhDelivered"] * (cum[k] / tot) if tot > 0 else 0.0
                win = range(k, k + 15)
                ok = gp[k][0] + 900 <= d and k + 15 <= len(gp) and all(gp[j][2] is not None and gp[j][2] >= 8 for j in win)
                if n - delivered >= 1 and ok and all((gc[j][2] or 0) <= 1 for j in win):
                    if any((gc[j][2] or 0) > 1 for j in range(k + 15, len(gc))): later += 1
                    else: never += 1
                    ratio.append(r["kWhDelivered"] / n)
                paused, low = False, 0
            elif not paused: low = 0
            k += 1
ratio.sort()
print(json.dumps({"failures": later + never, "draws_later": later, "never_draws_again": never,
                  "delivered_over_requested_median": round(ratio[len(ratio)//2], 3),
                  "share_delivered_below_half_request": round(sum(x < 0.5 for x in ratio) / len(ratio), 3)}, indent=1))
