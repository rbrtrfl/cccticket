"""
Test web server that simulates CCC ticket shop behavior.
Returns "shop closed" initially, then switches to queue page with cookies.
"""

from flask import Flask, make_response
from datetime import datetime, timedelta
import hashlib
import argparse

app = Flask(__name__)

# Default: Shop opens in 10 seconds from server start
SHOP_OPEN_TIME = datetime.now() + timedelta(seconds=10)

CLOSED_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CCCV ticket shop</title>
</head>
<body>
<div class="main">
    <h1>CCCV ticket shop</h1>
<p>
    The ticket sale has not started yet.
</p>
<p>
    Please be back here on time at 20:00:00.
</p>

</div>
</body>
</html>
"""

QUEUE_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>CCC Ticket Shop - Queue</title>
</head>
<body>
    <h1>You are now in our queue!</h1>
    <p>Please wait while we process your request.</p>
    <p>Session ID: {session_id}</p>
    <p>Do not close this page.</p>
</body>
</html>
"""


def generate_cookie_value():
    """Generate a unique cookie value."""
    random_data = f"{datetime.now().isoformat()}"
    return hashlib.md5(random_data.encode()).hexdigest()


@app.route("/")
def index():
    current_time = datetime.now()

    if current_time >= SHOP_OPEN_TIME:
        # Shop is open - return queue page with cookie
        cookie_value = generate_cookie_value()

        response = make_response(QUEUE_PAGE.format(session_id=cookie_value[:16]))
        response.set_cookie("__QXSESSION", cookie_value)

        print(
            f"[{current_time.isoformat()}] Shop OPEN - Cookie sent: {cookie_value[:8]}..."
        )
        return response
    else:
        # Shop is closed - no cookie
        response = make_response(
            CLOSED_PAGE.format(
                time=current_time.isoformat(), open_time=SHOP_OPEN_TIME.isoformat()
            )
        )
        time_until_open = (SHOP_OPEN_TIME - current_time).total_seconds()
        print(
            f"[{current_time.isoformat()}] Shop CLOSED - Opens in {time_until_open:.1f}s"
        )
        return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test web server for CCC ticket shop simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: opens in 10 seconds
  python test_server.py
  
  # Open after specific delay
  python test_server.py --open-in 5
  
  # Open at specific time
  python test_server.py --open-at "2025-12-27T15:00:00"
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--open-in",
        type=float,
        default=None,
        help="Open shop in N seconds from now (default: 10)",
    )

    group.add_argument(
        "--open-at",
        type=str,
        default=None,
        help="Open shop at specific time (ISO 8601 format)",
    )

    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run server on (default: 5000)"
    )

    args = parser.parse_args()

    # Set shop open time based on arguments
    if args.open_at:
        # Parse ISO format datetime
        from dateutil import parser as date_parser

        SHOP_OPEN_TIME = date_parser.isoparse(args.open_at)
        print(f"Test server starting...")
        print(f"Shop will open at: {SHOP_OPEN_TIME.isoformat()} (specified time)")
    elif args.open_in:
        SHOP_OPEN_TIME = datetime.now() + timedelta(seconds=args.open_in)
        print(f"Test server starting...")
        print(f"Shop will open in {args.open_in} seconds")
        print(f"Shop will open at: {SHOP_OPEN_TIME.isoformat()}")
    else:
        # Default: 10 seconds
        SHOP_OPEN_TIME = datetime.now() + timedelta(seconds=10)
        print(f"Test server starting...")
        print(f"Shop will open in 10 seconds (default)")
        print(f"Shop will open at: {SHOP_OPEN_TIME.isoformat()}")

    print(f"After opening, / will return queue page with cookie")
    print(f"Running on http://127.0.0.1:{args.port}/")

    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)
