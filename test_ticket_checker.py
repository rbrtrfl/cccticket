"""Tests for ticket_checker.py: page parsing and a full run against test_server.py."""

import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from werkzeug.serving import make_server

import test_server
import ticket_checker


def parse(page):
    session = Mock()
    session.get.return_value = Mock(text=page, url="u", status_code=200)
    return ticket_checker.fetch(session, "u")


class TestFetch(unittest.TestCase):
    def test_title_and_lines(self):
        _, title, _, hint = parse("<title> Queue &amp; co </title><p>Your position: <b>812</b></p>")
        self.assertEqual((title, hint), ("Queue & co", "Your position: 812"))

    def test_sold_out_line(self):
        self.assertIn("are sold", parse(test_server.PAGE.format("t", test_server.QUEUE.format(test_server.SOLD)))[3])

    def test_no_false_lines(self):
        for page in ["<p>Tickets will be sold on 2026-11-08 11:00</p>",
                     "<p>If this takes longer than a few minutes, contact us.</p>",
                     "<p>Dec. 27 – until 30, 2026</p>"]:
            self.assertEqual(parse(page)[3], "", page)

    def test_fingerprint_ignores_hidden_tokens_and_scripts(self):
        a = parse('<p>Voucher required</p><input type="hidden" value="t1">')[2]
        b = parse('<p>Voucher required</p><input type="hidden" value="t2"><script>x=2</script>')[2]
        c = parse('<p>Add to cart</p>')[2]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


@patch.multiple(ticket_checker, POLL=0.1, CHECK_IN=0.5, GIVE_UP=1)
class TestRun(unittest.TestCase):
    def setUp(self):
        self.server = make_server("127.0.0.1", 0, test_server.app, threaded=True)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/40c3/"
        self.opens = datetime.now(timezone.utc) + timedelta(seconds=3)
        test_server._arrivals.clear()
        test_server.OPEN = self.opens.astimezone().replace(tzinfo=None)
        test_server.QUEUE_RATE, test_server.SOLD_AFTER = 1.0, 2.5

    def tearDown(self):
        self.server.shutdown()

    def run_worker(self, opens):
        alerts = []
        with patch.object(ticket_checker, "alert", lambda m: alerts.append((datetime.now(timezone.utc), m))):
            ticket_checker.worker(0, self.url, opens, minutes=0.06)
        return alerts

    def test_queue_turn_sold_out(self):
        alerts = self.run_worker(self.opens)

        self.assertEqual([m.split(":")[0] for _, m in alerts],
                         ["Session 0 is in the queue", "Session 0", "Session 0"])
        self.assertGreaterEqual(alerts[0][0], self.opens)
        self.assertIn("40th Chaos Communication Congress", alerts[1][1])
        self.assertIn("are sold", alerts[2][1])

    def test_gives_up_when_nothing_changes(self):
        test_server.OPEN = datetime.now() + timedelta(hours=1)

        self.assertEqual(self.run_worker(self.opens), [])


if __name__ == "__main__":
    unittest.main()
