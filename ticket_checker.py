"""
CCC ticket queue checker. Start ~5 minutes before the sale:

    uv run ticket_checker.py 2026-11-11T18:00:00+01:00

Opens shop sessions, gets them into the queue the moment it opens, keeps them
there (the queue drops sessions that don't check in at least once a minute)
and alerts when one gets its turn or the sale is sold out.
"""

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

COOKIE = "__QXSESSION"
POLL = 0.5       # seconds between requests around the opening
CHECK_IN = 30    # seconds between check-ins while queued (the queue wants one per minute)
GIVE_UP = 120    # seconds after the opening without any change
SOLD_OUT = re.compile(r"(?i)sold out|tickets on sale today are sold|ausverkauft|sind verkauft")
QUEUE_LINE = re.compile(r"(?i)(position|minute|platz|warte).*\d")


def fetch(session, url):
    """Return (response, title, fingerprint of the visible text, queue/sold-out line)."""
    r = session.get(url, timeout=10)
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", r.text)
    title = " ".join(html.unescape(match.group(1)).split()) if match else ""
    body = re.sub(r"(?is)<(script|style|title)[^>]*>.*?</\1>", " ", r.text)
    body = re.sub(r"(?i)</?(p|div|h[1-6]|li|br|section)\b[^>]*>", "\n", body)
    lines = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", l)).split()) for l in body.splitlines()]
    text = hashlib.sha256(" ".join(lines).encode()).hexdigest()
    hint = next((l for l in lines if SOLD_OUT.search(l) or QUEUE_LINE.search(l)), "")
    return r, title, text, hint


def alert(message):
    print(f"\a{datetime.now():%H:%M:%S} {message}", flush=True)
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification {json.dumps(message)} '
                        'with title "Tickets" sound name "Glass"'], capture_output=True)


def worker(n, url, opens, minutes):
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0"
    log = lambda msg: print(f"[{n}] {datetime.now():%H:%M:%S} {msg}", flush=True)
    now = lambda: datetime.now(timezone.utc)

    # 1. Remember the closed shop page; the second request is past any intro redirect
    before = None
    while before is None and now() < opens - timedelta(seconds=2):
        try:
            fetch(s, url)
            r, title, text, _ = fetch(s, url)
        except requests.RequestException as e:
            log(f"shop not reachable ({e}), retrying")
            time.sleep(5)
            continue
        before = (r.url, title, text)
        skew = (now() - parsedate_to_datetime(r.headers["Date"])).total_seconds() if "Date" in r.headers else 0
        log(f'closed shop: HTTP {r.status_code} "{title}", your clock vs shop {skew:+.1f}s (±1s)')

    # 2. From 1 s before opening, poll every 0.5 s until the queue cookie appears or the page changes
    while (wait := (opens - timedelta(seconds=1) - now()).total_seconds()) > 0:
        time.sleep(min(wait, 30))
    while now() < opens + timedelta(seconds=GIVE_UP):
        had = s.cookies.get(COOKIE)
        try:
            r, title, text, hint = fetch(s, url)
            if before is None and now() < opens:  # started too late for step 1
                before = (r.url, title, text)
            elif s.cookies.get(COOKIE) != had or (r.status_code < 429 and (r.url, title, text) != before):
                break
        except requests.RequestException:
            pass
        time.sleep(POLL)
    else:
        log(f"no change {GIVE_UP}s after opening, giving up")
        return

    alert(f"Session {n} is in the queue")
    log(f'browser: document.cookie="{COOKIE}={s.cookies.get(COOKIE)}; path=/; max-age=2592000"')

    # 3. Check in every 30 s; alert when the page changes (your turn) or it's sold out
    last = (title, hint)
    end = time.monotonic() + minutes * 60
    while time.monotonic() < end:
        time.sleep(CHECK_IN)
        try:
            r, title, _, hint = fetch(s, url)
        except requests.RequestException as e:
            log(f"check failed ({e})")
            continue
        if (title, hint) != last:
            log(f'"{title}" {hint}')
            if title != last[0] or SOLD_OUT.search(hint):
                alert(f"Session {n}: {title} {hint}".strip())
            last = (title, hint)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("opens", help="sale start with offset, e.g. 2026-11-11T18:00:00+01:00")
    parser.add_argument("--url", default="https://tickets.events.ccc.de/40c3/")
    parser.add_argument("--sessions", type=int, default=2)
    parser.add_argument("--minutes", type=float, default=60, help="how long to stay in the queue")
    args = parser.parse_args()

    opens = datetime.fromisoformat(args.opens)
    if opens.tzinfo is None:
        sys.exit("give the time with its offset, e.g. 2026-11-11T18:00:00+01:00")
    print(f"Sale opens {opens:%Y-%m-%d %H:%M:%S %Z}, {args.sessions} sessions. Ctrl-C to stop.")

    threads = [threading.Thread(target=worker, args=(n, args.url, opens, args.minutes), daemon=True)
               for n in range(args.sessions)]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
