# CCC Ticket Shop Cookie Checker

Multi-threaded tool to collect session cookies from ticket shops. Runs 3 parallel threads to maximize chances of getting good queue positions.

## Quick Start

```bash
# Install
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Demo
uv run demo.py

# Production
uv run ticket_checker.py https://tickets.events.ccc.de/39c3/ --open-time "2025-11-17T20:00:00+01:00"
```

## Ticket Checker Usage

### Basic Commands

```bash
# Test mode (local server, opens in 10 seconds)
uv run ticket_checker.py

# Production
uv run ticket_checker.py https://tickets.events.ccc.de/39c3/

# With specific open time
uv run ticket_checker.py https://tickets.events.ccc.de/39c3/ --open-time "2025-12-27T15:00:00+01:00"
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `url` | `http://127.0.0.1:5000/` | Shop URL |
| `--open-time` | +10 seconds | Shop open time (ISO 8601) |
| `--threads` | 3 | Number of parallel threads |
| `--delay` | 0.05 | Seconds between requests |
| `--start-before` | 0.5 | Start N seconds before opening |

### Examples

```bash
# Standard
uv run ticket_checker.py https://tickets.events.ccc.de/39c3/ --open-time "2025-12-27T15:00:00+01:00"

# Aggressive (more threads, faster)
uv run ticket_checker.py https://tickets.events.ccc.de/39c3/ \
    --open-time "2025-12-27T15:00:00+01:00" \
    --threads 5 --delay 0.03

# Conservative (server-friendly)
uv run ticket_checker.py https://tickets.events.ccc.de/39c3/ \
    --open-time "2025-12-27T15:00:00+01:00" \
    --threads 2 --delay 0.5

```

## Test Server Usage

Simulates a ticket shop for testing.

### Basic Commands

```bash
# Default (opens in 10 seconds)
uv run test_server.py

# Open in 5 seconds
uv run test_server.py --open-in 5

# Open at specific time
uv run python test_server.py --open-at "2025-11-17T18:30:00"

# Custom port
uv run test_server.py --port 8080
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--open-in N` | 10 | Open in N seconds |
| `--open-at TIME` | - | Open at specific time (ISO 8601) |
| `--port` | 5000 | Server port |

### Testing Together

Match server and checker times:

```bash
# Terminal 1: Server
uv run test_server.py --open-in 30

# Terminal 2: Checker
uv run ticket_checker.py http://127.0.0.1:5000/
```

With specific time:

```bash
# Terminal 1: Server
uv run test_server.py --open-at "2025-12-27T15:00:00"

# Terminal 2: Checker
uv run ticket_checker.py http://127.0.0.1:5000/ \
    --open-time "2025-12-27T15:00:00"
```

## Demo

Automated demo that runs server and checker together.

```bash
uv run demo.py
```

What it does:
1. Starts test server (opens in 10 seconds)
2. Runs ticket checker with 3 threads
3. Shows real-time output
4. Displays collected cookies
5. Cleans up automatically

Duration: ~12 seconds

## Unit Tests

Run the test suite:

```bash
# Run all tests
uv run test_ticket_checker.py

# Expected output
Ran 18 tests in 0.234s
OK
```

Tests cover:
- Cookie collection (success/failure)
- Multi-threading
- Retry logic
- Error handling (network, HTTP, timeout)
- File operations
- Lock-free threading

## Output

### cookies_all.txt

All collected cookies with timestamps:

```
# Cookie 1 (Thread 0)
__QXSESSION=9b96856bf891fbaf111a6bb264784f26
# Collected at: 2025-11-16T15:00:00.001234

# Cookie 2 (Thread 1)
__QXSESSION=a3f7d92c1b4e8f5a9d3c2e7b6a1f4c8d
# Collected at: 2025-11-16T15:00:00.123456

# Cookie 3 (Thread 2)
__QXSESSION=5e8c1a4f7b2d9c3a6e1f8b4d7c2a5e9
# Collected at: 2025-11-16T15:00:00.234567
```

Test each cookie in your browser to find the best queue position.

## How It Works

1. **Waits** until 500ms before shop opens
2. **Starts 3 threads** that request simultaneously
3. **Retries** every 50ms until cookies received
4. **Saves** all cookies to `cookies_all.txt`

Each thread runs independently (lock-free) and stops after collecting one cookie.

## Files

- `ticket_checker.py` - Main checker script
- `test_server.py` - Test server for development
- `demo.py` - Automated demo
- `test_ticket_checker.py` - Unit tests (18 tests)
- `pyproject.toml` - Dependencies

## Requirements

- Python 3.11+
- requests
- flask (for test server)
- python-dateutil

Install with: `uv sync`

## Tips

- **Test first**: Always run `python demo.py` before production use
- **Exact timing**: Use precise shop open time with timezone
- **Start early**: Script waits automatically, no need to time it manually
- **Check output**: Review `cookies_all.txt` for all collected cookies
- **Test cookies**: Try each cookie to find best queue position


## Features

- **Multi-threaded**: 3 parallel requests for better coverage
- **Scheduled start**: Begins 500ms before shop opens
- **Auto-retry**: Continues until cookies received
- **Lock-free**: True parallel execution, no contention
- **CLI arguments**: Flexible configuration
- **Tested**: 18 unit tests included
- **Resilient**: Handles network errors, timeouts, HTTP errors

## Troubleshooting

### No cookies collected
- Verify URL is correct
- Check network connection
- Ensure shop open time hasn't passed

### Connection errors
- Check if server is running (for local tests)
- Verify firewall settings
- Test with `curl http://127.0.0.1:5000/`

