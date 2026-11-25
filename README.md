# CCC Ticket Checker

Gets shop sessions into the CCC ticket queue the moment it opens, keeps them there, and alerts when one gets its turn.

## Use

```bash
uv sync
caffeinate -i uv run ticket_checker.py 2026-11-11T18:00:00+01:00   # or 2026-11-19T20:00:00+01:00
```

1. Sync the clock (`sudo sntp -sS time.apple.com`), turn off Focus mode, have payment ready.
2. Start ~5 minutes before. It prints `closed shop: HTTP 200` and your clock offset (should be within ±1 s).
3. Also open https://tickets.events.ccc.de/40c3/ in Chrome and reload at :00 exactly, then leave the tab alone.
4. When the checker alerts a page change for a session (e.g. "40th Chaos Communication Congress"), it's that session's turn. If your own tab isn't in yet, open the shop in a **second Chrome profile**, paste that session's `document.cookie=…` line into the DevTools console (Cmd+Option+J), and reload.

Cookies belong to the browser profile, not the tab: pasting into your own profile replaces its queue place. Keep the checker running while you wait; it checks in every 30 s, and the queue drops sessions that don't check in once a minute.

## Local test

```bash
uv run demo.py                  # test server + checker, ~1 minute
uv run test_ticket_checker.py   # unit tests
```

`test_server.py` simulates the shop: holding page, queue, turn, sold out (`uv run test_server.py --help`).
