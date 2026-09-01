#!/usr/bin/env python3
"""$BULLCOIN autoposter - single file. Posts text to X and Telegram."""
import json, os, random, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).parent
TZ = ZoneInfo("America/New_York")
SLOTS = [("morning", 8, 0, 40), ("midday", 12, 30, 45),
         ("evening", 18, 20, 50), ("night", 22, 15, 45)]
BANNED = ["next runner", "don't miss out", "dont miss out", "guaranteed", "100x",
          "1000x", "to the moon", "moonshot", "easy money", "will pump",
          "about to run", "get in before", "last chance", "http", "www.", ".com"]


def load(p, d):
    return json.loads(p.read_text()) if p.exists() else d


def state():
    return load(R / "state.json", {"used": {}, "done": {}, "streak": 0,
                                   "last": None, "total": 0, "log": []})


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


def pick(bank, st, today):
    lines = load(R / "content.json", {})[bank]
    aged = []
    for l in lines:
        last = st["used"].get(l)
        age = 9999 if not last else (today - datetime.fromisoformat(last).date()).days
        aged.append((age, l))
    aged.sort(key=lambda x: -x[0])
    pool = [l for a, l in aged[:max(3, len(aged) // 3)] if a >= 20] or [aged[0][1]]
    return random.choice(pool)


def post_x(text):
    import tweepy
    c = tweepy.Client(consumer_key=os.getenv("X_API_KEY"),
                      consumer_secret=os.getenv("X_API_SECRET"),
                      access_token=os.getenv("X_ACCESS_TOKEN"),
                      access_token_secret=os.getenv("X_ACCESS_SECRET"))
    return c.create_tweet(text=text).data["id"]


def post_tg(text):
    import requests
    r = requests.post(
        f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
        data={"chat_id": os.getenv("TELEGRAM_CHAT_ID"), "text": text}, timeout=30)
    r.raise_for_status()
    return r.json()["result"]["message_id"]


def main():
    a = sys.argv[1:] or ["--plan"]
    now = datetime.now(TZ)
    day = now.date().isoformat()
    st = state()

    if "--lint" in a:
        c = load(R / "content.json", {})
        bad = [l for v in c.values() for l in v
               if any(b in l.lower() for b in BANNED)]
        print(f"{sum(len(v) for v in c.values())} lines, {len(bad)} flagged")
        for l in bad:
            print("  ", l)
        return

    if "--streak" in a:
        print(f"streak {st['streak']} days | {st['total']} posts | "
              f"today {st['done'].get(day, [])}")
        return

    if "--plan" in a:
        print(f"{day} ({len(plan(day, now))} posts):")
        for name, t in plan(day, now):
            mark = "done" if name in st["done"].get(day, []) else \
                   ("next" if t >= now else "passed")
            print(f"  {t:%H:%M}  {name:<8} {mark}")
        return

    force = "--force" in a
    slot = None
    for name, t in plan(day, now):
        if name in st["done"].get(day, []):
            continue
        if force or t <= now <= t + timedelta(minutes=90):
            slot = name
            break
    if not slot:
        print("no slot open")
        return

    bank = "midday" if slot == "bonus" else slot
    text = pick(bank, st, now.date())
    if any(b in text.lower() for b in BANNED):
        print("blocked:", text)
        return
    print(f"[{now:%H:%M}] {slot}: {text}")
    if "--post" not in a:
        print("(dry run - add --post to publish)")
        return

    sent = []
    for name, fn in (("x", post_x), ("telegram", post_tg)):
        try:
            print(f"  -> {name}: {fn(text)}")
            sent.append(name)
        except Exception as e:
            print(f"  !! {name} failed: {str(e)[:150]}")
    if not sent:
        return

    st["used"][text] = day
    st["done"].setdefault(day, []).append(slot)
    st["done"] = {k: v for k, v in st["done"].items()
                  if k >= (now.date() - timedelta(days=7)).isoformat()}
    if st["last"] != day:
        st["streak"] = st["streak"] + 1 if st["last"] == (
            now.date() - timedelta(days=1)).isoformat() else 1
        st["last"] = day
    st["total"] += 1
    st["log"] = (st["log"] + [{"when": now.isoformat(), "slot": slot,
                               "text": text, "to": ",".join(sent)}])[-200:]
    (R / "state.json").write_text(json.dumps(st, indent=2))


main()
EOF
