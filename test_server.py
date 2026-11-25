"""
Local stand-in for the CCC ticket shop: before opening a holding page without
cookies; at opening the first request gets the __QXSESSION cookie and the
queue page; sessions get their turn (the shop page) in order of arrival;
later the queue page says sold out.

    uv run test_server.py --open-in 10
"""

import argparse
import secrets
import threading
from datetime import datetime, timedelta

from flask import Flask, make_response, request

app = Flask(__name__)
OPEN = datetime.now() + timedelta(seconds=10)
QUEUE_RATE = 0.1   # sessions let into the shop per second
SOLD_AFTER = 120   # seconds after opening
_arrivals: dict[str, int] = {}
_lock = threading.Lock()

PAGE = '<!DOCTYPE html><html><head><title>{}</title></head><body><div class="main">{}</div></body></html>'
CLOSED = "<h1>CCCV ticket shop</h1><p>The ticket sale has not started yet.</p><p>Please be back here on time at {}.</p>"
QUEUE = "<h1>CCCV ticket shop</h1>{}<p>You are now in our queue!</p><p>Please do not close this page until it is your turn.</p>"
SOLD = '<div class="alert">All tickets on sale today are sold. / Alle Tickets der heutigen Verkaufsrunde sind verkauft.</div>'
SHOP = "<h1>40th Chaos Communication Congress</h1><p>Standard 200,00 EUR</p>"


@app.route("/40c3/")
def shop():
    opened = (datetime.now() - OPEN).total_seconds()
    if opened < 0:
        return PAGE.format("CCCV ticket shop", CLOSED.format(f"{OPEN:%H:%M:%S}"))
    if opened >= SOLD_AFTER:
        return PAGE.format("CCCV ticket shop", QUEUE.format(SOLD))

    session = request.cookies.get("__QXSESSION") or secrets.token_hex(16)
    with _lock:
        position = _arrivals.setdefault(session, len(_arrivals) + 1)
    if opened * QUEUE_RATE >= position:
        response = make_response(PAGE.format("40th Chaos Communication Congress", SHOP))
    else:
        response = make_response(PAGE.format("CCCV ticket shop", QUEUE.format("")))
    response.set_cookie("__QXSESSION", session, max_age=2592000)
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--open-in", type=float, default=10, help="seconds until opening")
    parser.add_argument("--open-at", help="opening time, ISO 8601 (overrides --open-in)")
    parser.add_argument("--queue-rate", type=float, default=QUEUE_RATE, help="sessions let in per second")
    parser.add_argument("--sold-after", type=float, default=SOLD_AFTER, help="seconds after opening")
    parser.add_argument("--port", type=int, default=8765, help="not 5000: macOS AirPlay uses it")
    args = parser.parse_args()

    OPEN = (datetime.fromisoformat(args.open_at).astimezone().replace(tzinfo=None) if args.open_at
            else datetime.now() + timedelta(seconds=args.open_in))
    QUEUE_RATE, SOLD_AFTER = args.queue_rate, args.sold_after
    print(f"Shop opens at {OPEN:%H:%M:%S}: http://127.0.0.1:{args.port}/40c3/")
    app.run(port=args.port, threaded=True)
