"""
CCC Ticket Shop Cookie Checker
Multi-threaded checker that starts before shop opens and collects multiple cookies.
"""

import requests
import time
import sys
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional


@dataclass
class CookieInfo:
    """Information about a collected cookie."""

    name: str
    value: str
    thread_id: int
    collected_at: datetime
    wait_time: Optional[int] = None


class TicketChecker:
    """Multi-threaded ticket shop checker."""

    def __init__(
        self,
        url: str,
        shop_open_time: datetime,
        num_threads: int = 3,
        request_delay: float = 0.5,
        start_before_seconds: float = 5,
    ):
        """
        Initialize the ticket checker.

        Args:
            url: The main shop URL
            shop_open_time: DateTime when shop opens
            num_threads: Number of parallel threads
            request_delay: Delay between requests in seconds
            start_before_seconds: Start checking N seconds before shop opens
        """
        self.url = url
        self.shop_open_time = shop_open_time
        self.num_threads = num_threads
        self.request_delay = request_delay
        self.start_before_seconds = start_before_seconds

        # Use separate variables for each thread (no locks needed!)
        self.thread_cookies: dict[int, Optional[CookieInfo]] = {}
        self.stop_collecting = threading.Event()

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) "
                "Gecko/20100101 Firefox/131.0"
            )
        }

    def wait_until_start_time(self):
        """Wait until it's time to start checking."""
        start_time = self.shop_open_time - timedelta(seconds=self.start_before_seconds)

        # Use timezone-aware now() if shop_open_time has timezone info
        if self.shop_open_time.tzinfo is not None:
            from datetime import timezone

            now = datetime.now(timezone.utc).astimezone(self.shop_open_time.tzinfo)
        else:
            now = datetime.now()

        if now < start_time:
            wait_seconds = (start_time - now).total_seconds()
            if wait_seconds < 1.0:
                print(
                    f"[{now.isoformat()}] Waiting {wait_seconds*1000:.0f}ms until start time..."
                )
            else:
                print(
                    f"[{now.isoformat()}] Waiting {wait_seconds:.1f}s until start time..."
                )
            print(f"Shop opens at: {self.shop_open_time.isoformat()}")
            print(f"Starting checks at: {start_time.isoformat()}")
            time.sleep(wait_seconds)

    def collect_cookie(self, thread_id: int) -> Optional[CookieInfo]:
        """
        Try to collect a cookie from the shop.
        Returns None if:
        - Shop is still closed (no cookies in response)
        - Request fails (network error, timeout, HTTP error)

        Args:
            thread_id: ID of the current thread

        Returns:
            CookieInfo if cookie was collected, None otherwise
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()

            if response.cookies:
                for cookie in response.cookies:
                    cookie_info = CookieInfo(
                        name=cookie.name,
                        value=cookie.value or "",
                        thread_id=thread_id,
                        collected_at=datetime.now(),
                        wait_time=None,  # Server doesn't return wait time
                    )
                    return cookie_info

            # Shop responded successfully but no cookies yet (still closed)
            return None

        except requests.exceptions.RequestException as e:
            # Request failed (network, timeout, HTTP error) - will retry
            print(f"[Thread {thread_id}] Request error: {e}", file=sys.stderr)
            return None

    def collector_thread(self, thread_id: int):
        """
        Thread function to collect cookies.
        Each thread stores its result in self.thread_cookies[thread_id] - no locks needed!
        Keeps retrying until a cookie is collected.

        Args:
            thread_id: ID of this thread
        """
        print(f"[Thread {thread_id}] Started")
        request_count = 0

        while not self.stop_collecting.is_set():
            request_count += 1
            now = datetime.now()

            print(f"[Thread {thread_id}] Request #{request_count} at {now.isoformat()}")

            cookie_info = self.collect_cookie(thread_id)

            if cookie_info:
                # Store directly in thread-specific variable (no lock needed!)
                self.thread_cookies[thread_id] = cookie_info
                print(
                    f"[Thread {thread_id}] ✓ Cookie collected: {cookie_info.value[:8]}..."
                )
                # Stop this thread after collecting one cookie
                break
            else:
                # No cookie yet (shop still closed or request failed), retry after delay
                print(
                    f"[Thread {thread_id}] No cookie yet, retrying in {self.request_delay}s..."
                )

            time.sleep(self.request_delay)

        # If no cookie collected (shouldn't happen unless stopped externally), store None
        if thread_id not in self.thread_cookies:
            self.thread_cookies[thread_id] = None

        print(f"[Thread {thread_id}] Finished")

    def run(self):
        """Main execution function."""
        print("=" * 70)
        print("CCC Ticket Shop Multi-Threaded Cookie Checker")
        print("=" * 70)

        # Wait until start time
        self.wait_until_start_time()

        print(f"\n🚀 Starting {self.num_threads} collector threads...")
        print(f"Request delay: {self.request_delay}s between requests\n")

        # Start collector threads
        threads = []
        for i in range(self.num_threads):
            thread = threading.Thread(target=self.collector_thread, args=(i,))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect all cookies from thread-specific variables
        collected_cookies = [
            cookie for cookie in self.thread_cookies.values() if cookie is not None
        ]

        print(f"\n{'=' * 70}")
        print(f"✓ Collection complete! Collected {len(collected_cookies)} cookies")
        print(f"{'=' * 70}\n")

        if not collected_cookies:
            print("❌ No cookies were collected!")
            return

        # Save all collected cookies
        self.save_all_cookies(collected_cookies)

        # Display all cookies
        print("\n📋 Collected Cookies:")
        print("-" * 70)
        for cookie in collected_cookies:
            print(f"Thread {cookie.thread_id}: {cookie.name}={cookie.value}")
            print(f"  Collected at: {cookie.collected_at.isoformat()}")
        print("-" * 70)

        print("\n✓ All cookies saved to cookies_all.txt")
        print("💡 Test each cookie manually to find the best queue position")

    def save_all_cookies(self, cookies: list[CookieInfo]):
        """Save all collected cookies to a file."""
        filepath = Path("cookies_all.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            for i, cookie_info in enumerate(cookies):
                f.write(f"# Cookie {i+1} (Thread {cookie_info.thread_id})\n")
                f.write(f"{cookie_info.name}={cookie_info.value}\n")
                f.write(f"# Collected at: {cookie_info.collected_at.isoformat()}\n")
                f.write("\n")
        print(f"💾 All cookies saved to {filepath}")


def main():
    """Main function."""
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="CCC Ticket Shop Multi-Threaded Cookie Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with local server
  python ticket_checker.py http://127.0.0.1:5000/
  
  # Production use
  python ticket_checker.py https://example.com/
  
  # With custom parameters
  python ticket_checker.py https://example.com/ --threads 5 --delay 0.1
        """,
    )

    parser.add_argument(
        "url",
        nargs="?",
        default="http://127.0.0.1:5000/",
        help="Shop URL to monitor (default: http://127.0.0.1:5000/)",
    )

    parser.add_argument(
        "--threads", type=int, default=3, help="Number of parallel threads (default: 3)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="Delay between requests in seconds (default: 0.05)",
    )

    parser.add_argument(
        "--start-before",
        type=float,
        default=0.5,
        dest="start_before",
        help="Start checking N seconds before shop opens (default: 0.5)",
    )

    parser.add_argument(
        "--open-time",
        type=str,
        default=None,
        dest="open_time",
        help="Shop open time in ISO format (default: 10 seconds from now)",
    )

    args = parser.parse_args()

    # Configuration from arguments
    url = args.url

    # Shop open time
    if args.open_time:
        # Parse ISO format datetime
        from dateutil import parser as date_parser

        shop_open_time = date_parser.isoparse(args.open_time)
    else:
        # Default: opens in 10 seconds from now (for testing)
        shop_open_time = datetime.now() + timedelta(seconds=10)

    print(f"Target URL: {url}")
    print(f"Threads: {args.threads}")
    print(f"Request delay: {args.delay}s")
    print(f"Start before: {args.start_before}s")
    print(f"Open time: {shop_open_time.isoformat()}")
    print()

    checker = TicketChecker(
        url=url,
        shop_open_time=shop_open_time,
        num_threads=args.threads,
        request_delay=args.delay,
        start_before_seconds=args.start_before,
    )

    try:
        checker.run()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        checker.stop_collecting.set()
        sys.exit(0)


if __name__ == "__main__":
    main()
