#!/usr/bin/env python3
"""$BULLCOIN terminal - read-only dashboard for the autoposter."""
import json, random, os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from flask import Flask, Response, request
from functools import wraps

R = Path(__file__).parent
TZ = ZoneInfo("America/New_York")
SLOTS = [("morning", 8, 0, 40), ("midday", 12, 30, 45),
         ("evening", 18, 20, 50), ("night", 22, 15, 45)]
app = Flask(__name__)
USER, PW = os.getenv("DASH_USER"), os.getenv("DASH_PASS")


def auth(f):
    @wraps(f)
    def i(*a, **k):
        if USER and PW:
            c = request.authorization
            if not c or c.username != USER or c.password != PW:
                return Response("auth", 401, {"WWW-Authenticate": "Basic realm=b"})
        return f(*a, **k)
    return i


def load(n, d):
    p = R / n
    return json.loads(p.read_text()) if p.exists() else d


def rnd(day, salt):
    return random.Random(f"{day}|{salt}|bullcoin")


def plan(day, now):
    n = rnd(day, "count").choice([3, 3, 4, 4, 4, 5])
    slots = list(SLOTS)
    if n < 4:
        drop = rnd(day, "drop").sample([s for s in slots if s[0] != "morning"], 4 - n)
        slots = [s for s in slots if s not in drop]
    out = []
    for name, h, m, j in slots:
        t = now.replace(hour=h, minute=m, second=0, microsecond=0)
        out.append((name, t + timedelta(minutes=rnd(day, name).randint(0, j))))
    if n == 5:
        r = rnd(day, "bonus")
        h = r.choice([10, 11, 15, 16, 21])
        out.append(("bonus", now.replace(hour=h, minute=r.randint(0, 59),
                                         second=0, microsecond=0)))
    return sorted(out, key=lambda x: x[1])


CSS = """
:root{--ink:#0A0B0D;--pan:#101317;--rule:#1F2630;--gold:#E6B93B;--cr:#F3EEE2;
--up:#25C08B;--mut:#69737F}
*{box-sizing:border-box}body{margin:0;background:var(--ink);color:var(--cr);
font:13px/1.5 'IBM Plex Mono',ui-monospace,Menlo,monospace;padding:0 0 50px}
.w{max-width:960px;margin:0 auto;padding:0 18px}
.top{border-bottom:1px solid var(--rule);background:#12161C}
.top .w{display:flex;align-items:center;gap:12px;height:58px}
.wm{font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:15px}
.wm span{color:var(--gold)}.desk{font-size:10px;letter-spacing:.2em;color:var(--mut);
text-transform:uppercase}.live{margin-left:auto;color:var(--up);font-size:10px;
letter-spacing:.18em;text-transform:uppercase}
.hero{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--rule);
background:var(--pan);margin:24px 0 16px}
.hero>div{padding:24px}.hero>div+div{border-left:1px solid var(--rule)}
.eb{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--mut);
margin-bottom:10px}
.big{font-size:64px;font-weight:700;line-height:.9;letter-spacing:-.02em}
.big small{font-size:18px;color:var(--mut);margin-left:8px}
.gold{color:var(--gold)}.sub{color:var(--mut);margin-top:10px;font-size:12px}
.q{margin-top:14px;padding:12px;background:var(--ink);border:1px solid var(--rule);
border-left:2px solid var(--gold)}
.p{border:1px solid var(--rule);background:var(--pan);margin-bottom:16px}
.p h2{font-size:12px;font-weight:700;margin:0;padding:14px 18px;letter-spacing:.16em;
text-transform:uppercase;border-bottom:1px solid var(--rule)}
table{width:100%;border-collapse:collapse}
th{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--mut);
text-align:left;font-weight:500;padding:9px 18px;border-bottom:1px solid var(--rule)}
td{padding:10px 18px;border-bottom:1px solid rgba(31,38,48,.5)}
.dim{color:var(--mut)}.ok{color:var(--up)}.due{color:var(--gold)}
.bars{display:flex;align-items:flex-end;gap:3px;height:64px;padding:18px;
border-bottom:1px solid var(--rule)}
.bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:2px}
.blk{height:6px;background:var(--gold);opacity:.85}
.bar.t .blk{background:var(--up)}.bar.e{border-bottom:1px solid #E2504B}
@media(max-width:700px){.hero{grid-template-columns:1fr}
.hero>div+div{border-left:0;border-top:1px solid var(--rule)}.big{font-size:48px}}
"""


@app.route("/")
@auth
def index():
    now = datetime.now(TZ)
    day = now.date().isoformat()
    st = load("state.json", {})
    banks = load("content.json", {})
    done = st.get("done", {}).get(day, [])
    pl = plan(day, now)
    nxt = next((p for p in pl if p[0] not in done and p[1] >= now), None)
    nt = f"{nxt[1]:%H:%M}" if nxt else "--:--"
    left = ""
    if nxt:
        s = int((nxt[1] - now).total_seconds())
        left = f"in {s//3600}h {s%3600//60}m" if s >= 3600 else f"in {s//60}m"

    rows = ""
    for name, t in pl:
        cls, lab = ("ok", "posted") if name in done else \
            (("due", "scheduled") if t >= now else ("dim", "window closed"))
        rows += f"<tr><td>{t:%H:%M}</td><td>{name}</td><td class={cls}>{lab}</td></tr>"

    cnt = {}
    for e in st.get("log", []):
        cnt[e["when"][:10]] = cnt.get(e["when"][:10], 0) + 1
    bars = ""
    for i in range(29, -1, -1):
        d = (now.date() - timedelta(days=i)).isoformat()
        n = cnt.get(d, 0)
        c = "bar t" if i == 0 else ("bar e" if n == 0 else "bar")
        bars += f"<div class='{c}' title='{d}: {n}'>" + "<div class=blk></div>" * n + "</div>"

    log = list(reversed(st.get("log", [])))[:10]
    hist = "".join(f"<tr><td class=dim>{l['when'][5:16].replace('T',' ')}</td>"
                   f"<td>{l['text']}</td><td class=dim>{l.get('to','')}</td></tr>"
                   for l in log)
    active = len([1 for i in range(30)
                  if cnt.get((now.date() - timedelta(days=i)).isoformat())])

    return f"""<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>$BULLCOIN terminal</title><style>{CSS}</style>
<div class=top><div class=w><div><div class=wm><span>$</span>bullcoin</div>
<div class=desk>autopost terminal</div></div><div class=live>&#9679; posting</div></div></div>
<div class=w>
<div class=hero>
<div><div class=eb>consecutive days posted</div><div class="big gold">{st.get('streak',0)}<small>days</small></div>
<div class=sub>{st.get('total',0)} posts published &middot; {len(done)} of {len(pl)} today</div></div>
<div><div class=eb>next post</div><div class=big>{nt}<small>{left}</small></div>
<div class=q>{nxt[0] if nxt else 'last post of the day'}</div></div>
</div>
<div class=p><h2>Activity &middot; {active} of last 30 days</h2><div class=bars>{bars}</div></div>
<div class=p><h2>Today</h2><table><tr><th>time</th><th>slot</th><th>status</th></tr>{rows}</table></div>
<div class=p><h2>Published</h2><table><tr><th>when</th><th>post</th><th>sent</th></tr>
{hist or '<tr><td colspan=3 class=dim>nothing yet</td></tr>'}</table></div>
<div class=sub>{sum(len(v) for v in banks.values())} lines in rotation &middot;
{' &middot; '.join(f'{k} {len(v)}' for k,v in banks.items())}</div>
</div>"""


app.run(host="127.0.0.1", port=8080)
