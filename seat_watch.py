"""Pull seats from Banner's public class search and write seats.json. No login, read-only.
Usage: python seat_watch.py all_schedules.json seats.json
"""
import http.cookiejar, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

BASE = "https://banssb9.villanova.edu/StudentRegistrationSsb/ssb/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TERM = "202730"

tracked = {s[2]: s[0].split()[0] for s in json.load(open(sys.argv[1], encoding="utf-8"))["sections"]}
subjects = sorted(set(tracked.values()))
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
tok = None

def call(path, data=None):
    h = {"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"}
    if tok: h["X-Synchronizer-Token"] = tok
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    with op.open(urllib.request.Request(BASE + path, data=body, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "replace")

m = re.search(r'name="synchronizerToken"\s+content="([^"]+)"', call("term/termSelection?mode=search"))
tok = m.group(1) if m else None
sid = "pub" + str(int(time.time() * 1000))
call("term/search?mode=search", dict(term=TERM, studyPath="", studyPathText="", startDatepicker="", endDatepicker="", uniqueSessionId=sid))

seats = {}
for sub in subjects:
    call("classSearch/resetDataForm", {})
    off, tot = 0, 1
    while off < tot:
        j = json.loads(call(f"searchResults/searchResults?txt_subject={sub}&txt_term={TERM}&startDatepicker=&endDatepicker=&uniqueSessionId={sid}&pageOffset={off}&pageMaxSize=200&sortColumn=subjectDescription&sortDirection=asc"))
        tot = j.get("totalCount") or 0
        d = j.get("data") or []
        if not d: break
        for s in d:
            c = s["courseReferenceNumber"]
            if c in tracked: seats[c] = [s["maximumEnrollment"], s["seatsAvailable"]]
        off += len(d)

missing = [c for c in tracked if c not in seats]
if missing: sys.exit(f"Banner did not return {len(missing)} tracked sections, for example {missing[:5]}")
json.dump({"asOfIso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "seats": seats}, open(sys.argv[2], "w"), separators=(",", ":"))
print("ok", len(seats))
