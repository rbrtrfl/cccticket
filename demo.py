"""Runs test_server.py and ticket_checker.py together (~1 minute)."""

import subprocess
import sys
import time
from datetime import datetime, timedelta

opens = (datetime.now().astimezone() + timedelta(seconds=10)).replace(microsecond=0).isoformat()
server = subprocess.Popen(
    [sys.executable, "test_server.py", "--open-at", opens, "--queue-rate", "0.05", "--sold-after", "60"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
try:
    time.sleep(2)
    subprocess.run([sys.executable, "ticket_checker.py", opens,
                    "--url", "http://127.0.0.1:8765/40c3/", "--minutes", "1.2"])
finally:
    server.terminate()
