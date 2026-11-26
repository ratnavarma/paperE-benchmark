"""Pull ACN-Data sessions (with pilot and current time series) for the registered window.
Token: Keychain item 'acn-data', read at run time, never printed or stored."""
import base64, datetime as dt, gzip, hashlib, json, subprocess, sys, time, urllib.parse, urllib.request
SITES = ["caltech", "jpl", "office001"]
START, END = "Fri, 01 Nov 2019 00:00:00 GMT", "Sun, 01 Mar 2020 08:00:00 GMT"  # 2019-11-01 to 2020-02-29 local
def token():
    return subprocess.run(["/usr/bin/security", "find-generic-password", "-s", "acn-data", "-w"], capture_output=True, text=True, check=True).stdout.strip()
def get(url, tok):
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + base64.b64encode((tok + ":").encode()).decode(), "User-Agent": "paper-foundry/0.1"})
    for a in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and a < 5: time.sleep(10 * (a + 1)); continue
            raise RuntimeError(f"HTTP {e.code} for {url.split('?')[0]}") from None
def main(out):
    tok = token(); summary = {"pulled_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "window": [START, END], "sites": {}}
    for site in SITES:
        rows = []
        t0 = dt.datetime(2019, 11, 1, 7, tzinfo=dt.timezone.utc); tend = dt.datetime(2020, 3, 1, 8, tzinfo=dt.timezone.utc)
        weeks = []
        while t0 < tend:
            t1 = min(t0 + dt.timedelta(days=7), tend); weeks.append((t0, t1)); t0 = t1
        for w0, w1 in weeks:
          f = lambda x: x.strftime("%a, %d %b %Y %H:%M:%S GMT")
          where = f'connectionTime>="{f(w0)}" and connectionTime<"{f(w1)}"'
          url = f"https://ev.caltech.edu/api/v1/sessions/{site}/ts?" + urllib.parse.urlencode({"where": where, "max_results": 25})
          while url:
              d = get(url, tok); rows += d.get("_items", [])
              nxt = (d.get("_links") or {}).get("next", {}).get("href")
              if nxt:  # the API's next link is not URL-encoded: re-encode its query
                  path, _, q = nxt.partition("?")
                  url = "https://ev.caltech.edu/api/v1/" + path + "?" + urllib.parse.urlencode(urllib.parse.parse_qsl(q, keep_blank_values=True))
              else:
                  url = None
              print(site, len(rows), file=sys.stderr, flush=True)
        p = f"{out}/acn_{site}.json.gz"
        with gzip.open(p, "wt") as fh: json.dump(rows, fh)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        summary["sites"][site] = {"sessions": len(rows), "with_user_id": sum(1 for r in rows if r.get("userID")), "with_timeseries": sum(1 for r in rows if r.get("pilotSignal") and r.get("chargingCurrent")), "file": p.split("/")[-1], "sha256": h}
    json.dump(summary, open(f"{out}/PULL_SUMMARY.json", "w"), indent=1); print(json.dumps(summary, indent=1))
if __name__ == "__main__": main(sys.argv[1])
