"""
Unit tests for CCC Ticket Shop Cookie Checker
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import requests

# Import the ticket checker module
import sys

sys.path.insert(0, "/home/claude")
from ticket_checker import TicketChecker, CookieInfo


class TestCookieInfo(unittest.TestCase):
    """Tests for CookieInfo dataclass."""

    def test_cookie_info_creation(self):
        """Test creating a CookieInfo object."""
        # Given: A timestamp and cookie details
        now = datetime.now()

        # When: Creating a CookieInfo object
        cookie = CookieInfo(
            name="__QXSESSION",
            value="abc123",
            thread_id=0,
            collected_at=now,
            wait_time=None
        )

        # Then: All fields should be set correctly
        self.assertEqual(cookie.name, "__QXSESSION")
        self.assertEqual(cookie.value, "abc123")
        self.assertEqual(cookie.thread_id, 0)
        self.assertEqual(cookie.collected_at, now)
        self.assertIsNone(cookie.wait_time)


class TestTicketChecker(unittest.TestCase):
    """Tests for TicketChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_url = "http://127.0.0.1:5000/"
        self.shop_open_time = datetime.now() + timedelta(seconds=1)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Clean up any cookies files created
        for f in ["cookies_all.txt"]:
            Path(f).unlink(missing_ok=True)

    def test_initialization(self):
        """Test TicketChecker initialization."""
        # Given: Configuration parameters for ticket checker
        # (setup in setUp method provides test_url and shop_open_time)

        # When: Creating a TicketChecker instance
        checker = TicketChecker(
            url=self.test_url,
            shop_open_time=self.shop_open_time,
            num_threads=3,
            request_delay=0.05,
            start_before_seconds=0.5,
        )

        # Then: All configuration should be stored correctly
        self.assertEqual(checker.url, self.test_url)
        self.assertEqual(checker.shop_open_time, self.shop_open_time)
        self.assertEqual(checker.num_threads, 3)
        self.assertEqual(checker.request_delay, 0.05)
        self.assertEqual(checker.start_before_seconds, 0.5)
        # And: Internal data structures should be initialized
        self.assertIsInstance(checker.thread_cookies, dict)
        self.assertFalse(checker.stop_collecting.is_set())

    def test_wait_until_start_time_already_passed(self):
        """Test wait_until_start_time when start time already passed."""
        # Given: A shop open time that's already in the past
        past_time = datetime.now() - timedelta(seconds=1)
        checker = TicketChecker(
            url=self.test_url,
            shop_open_time=past_time,
            num_threads=1,
            request_delay=0.05,
            start_before_seconds=0.5,
        )

        # When: Waiting for start time
        start = datetime.now()
        checker.wait_until_start_time()
        elapsed = (datetime.now() - start).total_seconds()

        # Then: Should return immediately without waiting
        self.assertLess(elapsed, 0.1)

    @patch("requests.get")
    def test_collect_cookie_success(self, mock_get):
        """Test successful cookie collection."""
        # Given: A mocked response that returns a cookie
        mock_cookie = Mock()
        mock_cookie.name = "__QXSESSION"
        mock_cookie.value = "abc123"

        mock_response = Mock()
        mock_response.cookies = [mock_cookie]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=1
        )

        # When: Attempting to collect a cookie
        cookie_info = checker.collect_cookie(thread_id=0)

        # Then: Should successfully return cookie info
        self.assertIsNotNone(cookie_info)
        if cookie_info is not None:
            self.assertEqual(cookie_info.name, "__QXSESSION")
            self.assertEqual(cookie_info.value, "abc123")
            self.assertEqual(cookie_info.thread_id, 0)
            self.assertIsNone(cookie_info.wait_time)

    @patch("requests.get")
    def test_collect_cookie_no_cookies(self, mock_get):
        """Test collection when no cookies returned (shop closed)."""
        # Given: A mocked response with no cookies (shop still closed)
        mock_response = Mock()
        mock_response.cookies = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=1
        )

        # When: Attempting to collect a cookie
        cookie_info = checker.collect_cookie(thread_id=0)

        # Then: Should return None (will retry later)
        self.assertIsNone(cookie_info)

    @patch("requests.get")
    def test_collect_cookie_network_error(self, mock_get):
        """Test collection when network error occurs."""
        # Given: A mocked network error
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=1
        )

        # When: Attempting to collect a cookie during network failure
        cookie_info = checker.collect_cookie(thread_id=0)

        # Then: Should return None (will retry later)
        self.assertIsNone(cookie_info)

    @patch("requests.get")
    def test_collect_cookie_http_error(self, mock_get):
        """Test collection when HTTP error occurs (503, etc)."""
        # Given: A mocked HTTP 503 error (server overloaded)
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "503 Server Error"
        )
        mock_get.return_value = mock_response

        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=1
        )

        # When: Attempting to collect a cookie during server error
        cookie_info = checker.collect_cookie(thread_id=0)

        # Then: Should return None (will retry later)
        self.assertIsNone(cookie_info)

    @patch("requests.get")
    def test_collect_cookie_timeout(self, mock_get):
        """Test collection when request times out."""
        # Given: A mocked timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=1
        )

        # When: Attempting to collect a cookie during timeout
        cookie_info = checker.collect_cookie(thread_id=0)

        # Then: Should return None (will retry later)
        self.assertIsNone(cookie_info)

    def test_save_all_cookies(self):
        """Test saving cookies to file."""
        # Given: A checker and test cookies
        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=1
        )

        now = datetime.now()
        cookies = [
            CookieInfo("__QXSESSION", "abc123", 0, now, None),
            CookieInfo("__QXSESSION", "def456", 1, now, None),
            CookieInfo("__QXSESSION", "ghi789", 2, now, None),
        ]

        # When: Saving cookies to file
        checker.save_all_cookies(cookies)

        # Then: File should exist and contain all cookie data
        self.assertTrue(Path("cookies_all.txt").exists())

        content = Path("cookies_all.txt").read_text()
        self.assertIn("abc123", content)
        self.assertIn("def456", content)
        self.assertIn("ghi789", content)
        self.assertIn("Thread 0", content)
        self.assertIn("Thread 1", content)
        self.assertIn("Thread 2", content)

    @patch("ticket_checker.TicketChecker.collect_cookie")
    def test_collector_thread_success(self, mock_collect):
        """Test collector thread successfully collects cookie."""
        # Given: A mock that returns a cookie on first try
        now = datetime.now()
        mock_cookie = CookieInfo("__QXSESSION", "abc123", 0, now, None)
        mock_collect.return_value = mock_cookie

        checker = TicketChecker(
            url=self.test_url,
            shop_open_time=datetime.now() - timedelta(seconds=1),  # Already open
            num_threads=1,
            request_delay=0.01,
        )

        # When: Running the collector thread
        checker.collector_thread(0)

        # Then: Cookie should be stored in thread_cookies dict
        self.assertIn(0, checker.thread_cookies)
        self.assertIsNotNone(checker.thread_cookies[0])
        if checker.thread_cookies[0] is not None:
            self.assertEqual(checker.thread_cookies[0].value, "abc123")

    @patch("ticket_checker.TicketChecker.collect_cookie")
    def test_collector_thread_retry_then_success(self, mock_collect):
        """Test collector thread retries then succeeds."""
        # Given: Mock returns None twice (shop closed), then returns cookie
        now = datetime.now()
        mock_cookie = CookieInfo("__QXSESSION", "abc123", 0, now, None)
        mock_collect.side_effect = [None, None, mock_cookie]

        checker = TicketChecker(
            url=self.test_url,
            shop_open_time=datetime.now() - timedelta(seconds=1),
            num_threads=1,
            request_delay=0.01,
        )

        # When: Running the collector thread (will retry)
        checker.collector_thread(0)

        # Then: Cookie should be eventually stored
        self.assertIn(0, checker.thread_cookies)
        self.assertIsNotNone(checker.thread_cookies[0])
        if checker.thread_cookies[0] is not None:
            self.assertEqual(checker.thread_cookies[0].value, "abc123")
        # And: Should have retried 3 times total
        self.assertEqual(mock_collect.call_count, 3)

    @patch("ticket_checker.TicketChecker.collect_cookie")
    def test_collector_thread_stops_on_signal(self, mock_collect):
        """Test collector thread stops when stop signal is set."""
        # Given: Mock always returns None (never gets cookie)
        mock_collect.return_value = None

        checker = TicketChecker(
            url=self.test_url,
            shop_open_time=datetime.now() - timedelta(seconds=1),
            num_threads=1,
            request_delay=0.01,
        )

        # And: A thread that will set stop signal after short delay
        import threading

        def set_stop():
            import time

            time.sleep(0.05)
            checker.stop_collecting.set()

        stop_thread = threading.Thread(target=set_stop)
        stop_thread.start()

        # When: Running collector thread (will be stopped externally)
        checker.collector_thread(0)

        stop_thread.join()

        # Then: Thread should have stored None (didn't get cookie)
        self.assertIn(0, checker.thread_cookies)
        self.assertIsNone(checker.thread_cookies[0])

    def test_thread_cookies_lock_free(self):
        """Test that different threads write to different dict keys."""
        # Given: A checker with thread_cookies dict
        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=3
        )

        # When: Simulating threads writing to their own keys
        now = datetime.now()
        checker.thread_cookies[0] = CookieInfo("__QXSESSION", "abc123", 0, now, None)
        checker.thread_cookies[1] = CookieInfo("__QXSESSION", "def456", 1, now, None)
        checker.thread_cookies[2] = CookieInfo("__QXSESSION", "ghi789", 2, now, None)

        # Then: All should be stored correctly with no collisions
        self.assertEqual(len(checker.thread_cookies), 3)
        self.assertEqual(checker.thread_cookies[0].value, "abc123")
        self.assertEqual(checker.thread_cookies[1].value, "def456")
        self.assertEqual(checker.thread_cookies[2].value, "ghi789")

    def test_multiple_threads_unique_keys(self):
        """Test that each thread gets a unique key."""
        # Given: A checker with 5 threads
        checker = TicketChecker(
            url=self.test_url, shop_open_time=self.shop_open_time, num_threads=5
        )

        # Then: Initially no keys should be present
        for i in range(5):
            self.assertNotIn(i, checker.thread_cookies)

        # When: Simulating threads writing
        now = datetime.now()
        for i in range(5):
            checker.thread_cookies[i] = CookieInfo(
                "__QXSESSION", f"cookie{i}", i, now, None
            )

        # Then: All should be stored with no collisions
        self.assertEqual(len(checker.thread_cookies), 5)
        for i in range(5):
            self.assertIsNotNone(checker.thread_cookies[i])
            if checker.thread_cookies[i] is not None:
                self.assertEqual(checker.thread_cookies[i].value, f"cookie{i}")


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_url = "http://127.0.0.1:5000/"

    def tearDown(self):
        """Clean up test files."""
        for f in ["cookies_all.txt"]:
            Path(f).unlink(missing_ok=True)

    @patch("requests.get")
    def test_full_collection_workflow(self, mock_get):
        """Test complete workflow with 3 threads collecting cookies."""

        # Given: Mock that simulates shop opening after a few requests
        def mock_response(*args, **kwargs):
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()

            # First 6 requests (2 per thread) return no cookies
            if mock_get.call_count <= 6:
                mock_resp.cookies = []
            else:
                # Return unique cookie for each thread
                cookie_num = (mock_get.call_count - 7) % 3
                mock_resp.cookies = [
                    Mock(name="__QXSESSION", value=f"cookie{cookie_num}")
                ]
            return mock_resp

        mock_get.side_effect = mock_response

        # And: Checker with shop that "opens" soon
        checker = TicketChecker(
            url=self.test_url,
            shop_open_time=datetime.now() + timedelta(milliseconds=100),
            num_threads=3,
            request_delay=0.01,
            start_before_seconds=0.05,
        )

        # When: Running the complete collection workflow
        checker.run()

        # Then: Cookies should have been collected
        cookies = [c for c in checker.thread_cookies.values() if c is not None]
        self.assertGreater(len(cookies), 0)

        # And: Output file should have been created
        self.assertTrue(Path("cookies_all.txt").exists())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_zero_threads(self):
        """Test with zero threads (should handle gracefully)."""
        # Given: A checker configured with zero threads
        checker = TicketChecker(
            url="http://127.0.0.1:5000/",
            shop_open_time=datetime.now() + timedelta(seconds=1),
            num_threads=0,
        )

        # When: Running the checker
        checker.run()

        # Then: Should complete without errors and no cookies collected
        self.assertEqual(len(checker.thread_cookies), 0)

    def test_very_short_delay(self):
        """Test with very short request delay."""
        # Given: A checker with very short delay (1ms)
        checker = TicketChecker(
            url="http://127.0.0.1:5000/",
            shop_open_time=datetime.now() + timedelta(seconds=1),
            num_threads=1,
            request_delay=0.001,
        )

        # Then: Configuration should be accepted
        self.assertEqual(checker.request_delay, 0.001)

    def test_past_shop_open_time(self):
        """Test when shop open time is in the past."""
        # Given: Shop open time that's already in the past
        checker = TicketChecker(
            url="http://127.0.0.1:5000/",
            shop_open_time=datetime.now() - timedelta(hours=1),
            num_threads=1,
            start_before_seconds=0.5,
        )

        # When: Waiting for start time
        start = datetime.now()
        checker.wait_until_start_time()
        elapsed = (datetime.now() - start).total_seconds()

        # Then: Should start immediately
        self.assertLess(elapsed, 0.1)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCookieInfo))
    suite.addTests(loader.loadTestsFromTestCase(TestTicketChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success/failure
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
