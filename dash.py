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
.p h2{font-size:12px;font
