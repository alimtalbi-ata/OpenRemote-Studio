"""R113: bound blocking system DNS within the Zabbix HTTPS transaction deadline.

Tests use an injected resolver and local synchronization primitives only.
No external DNS service, Zabbix instance, or credential is used.
Author: Abdelhalim Talbi.
"""
import socket
import ssl
import threading
import time
import unittest
from unittest.mock import patch

from zabbix_readonly import (
    _ACTIVE_HTTP_DEADLINE,
    _DeadlineDNSResolver,
    _DeadlineHTTPSConnection,
)


class ZabbixBoundedDNSDeadlineR113Tests(unittest.TestCase):
    def test_expired_deadline_does_not_start_resolver_workers(self):
        pool = _DeadlineDNSResolver(
            resolver=lambda *_args, **_kwargs: self.fail("resolver must not run"),
            worker_count=1,
            queue_capacity=1,
        )
        try:
            with self.assertRaises(socket.timeout):
                pool.resolve("zabbix.invalid", 443, time.monotonic() - 1.0)
            self.assertEqual(pool._threads, [])
            self.assertEqual(pool._jobs.qsize(), 0)
        finally:
            pool.close()

    def test_successful_resolution_preserves_getaddrinfo_shape(self):
        expected = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                     "", ("127.0.0.1", 8443))]
        calls = []

        def resolver(host, port, *, type):
            calls.append((host, port, type))
            return expected

        pool = _DeadlineDNSResolver(resolver=resolver, worker_count=2, queue_capacity=2)
        try:
            found = pool.resolve("zabbix.invalid", 8443, time.monotonic() + 1.0)
            self.assertEqual(found, expected)
            self.assertEqual(calls, [("zabbix.invalid", 8443, socket.SOCK_STREAM)])
            self.assertEqual(len(pool._threads), 2)
            self.assertTrue(all(thread.daemon for thread in pool._threads))
        finally:
            pool.close()

    def test_tcp_connect_uses_bounded_resolver_pool_before_socket_connect(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        calls = []

        def resolver(host, requested_port, *, type):
            calls.append((host, requested_port, type))
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                     "", ("127.0.0.1", requested_port))]

        pool = _DeadlineDNSResolver(resolver=resolver, worker_count=1, queue_capacity=1)
        deadline = time.monotonic() + 1.0
        token = _ACTIVE_HTTP_DEADLINE.set(deadline)
        try:
            connection = _DeadlineHTTPSConnection(
                "zabbix.invalid", timeout=1.0, context=ssl.create_default_context()
            )
        finally:
            _ACTIVE_HTTP_DEADLINE.reset(token)
        client_sock = None
        accepted_sock = None
        try:
            with patch("zabbix_readonly._DNS_RESOLVER", pool):
                client_sock = connection._create_connection(
                    ("zabbix.invalid", port), timeout=1.0, source_address=None
                )
            accepted_sock, _address = listener.accept()
            self.assertEqual(calls, [("zabbix.invalid", port, socket.SOCK_STREAM)])
            self.assertEqual(client_sock.getpeername()[0], "127.0.0.1")
        finally:
            connection.close()
            pool.close()
            listener.close()
            if client_sock is not None:
                try:
                    client_sock.close()
                except OSError:
                    pass
            if accepted_sock is not None:
                accepted_sock.close()

    def test_stalled_system_resolver_cannot_hold_caller_past_deadline(self):
        entered = threading.Event()
        release = threading.Event()

        def blocked(_host, _port, *, type):
            entered.set()
            release.wait(1.0)
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                     "", ("127.0.0.1", 443))]

        pool = _DeadlineDNSResolver(resolver=blocked, worker_count=1, queue_capacity=1)
        started = time.monotonic()
        try:
            with self.assertRaises(socket.timeout):
                pool.resolve("blackhole.invalid", 443, started + 0.15)
            elapsed = time.monotonic() - started
            self.assertTrue(entered.is_set(), "the test must exercise a resolver blocked in the worker")
            self.assertGreaterEqual(elapsed, 0.10)
            self.assertLess(elapsed, 0.60, "DNS waiting must obey the caller's absolute deadline")
        finally:
            release.set()
            pool.close(timeout=1.0)

    def test_queued_lookup_expiring_while_worker_is_stuck_is_skipped(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []
        calls_lock = threading.Lock()

        def blocked(host, _port, *, type):
            with calls_lock:
                calls.append(host)
            entered.set()
            release.wait(1.0)
            return []

        pool = _DeadlineDNSResolver(resolver=blocked, worker_count=1, queue_capacity=2)
        first_result = {}

        def first_lookup():
            try:
                first_result["value"] = pool.resolve(
                    "first.invalid", 443, time.monotonic() + 0.50
                )
            except Exception as exc:
                first_result["error"] = exc

        first = threading.Thread(target=first_lookup, daemon=True)
        first.start()
        try:
            self.assertTrue(entered.wait(0.25), "first lookup should occupy the only resolver worker")
            with self.assertRaises(socket.timeout):
                pool.resolve("expired.invalid", 443, time.monotonic() + 0.08)
            release.set()
            first.join(timeout=0.30)
            self.assertFalse(first.is_alive(), "the first caller should finish after resolver release")
            end = time.monotonic() + 0.25
            while pool._jobs.unfinished_tasks and time.monotonic() < end:
                time.sleep(0.005)
            with calls_lock:
                self.assertEqual(calls, ["first.invalid"],
                                 "expired queued DNS work must not start a new OS resolver call")
            self.assertEqual(first_result.get("value"), [])
            self.assertNotIn("error", first_result)
        finally:
            release.set()
            first.join(timeout=0.30)
            pool.close(timeout=1.0)

    def test_worker_count_and_queue_remain_bounded_when_all_resolvers_stall(self):
        release = threading.Event()
        condition = threading.Condition()
        started_hosts = []

        def blocked(host, _port, *, type):
            with condition:
                started_hosts.append(host)
                condition.notify_all()
            release.wait(1.0)
            return []

        pool = _DeadlineDNSResolver(resolver=blocked, worker_count=2, queue_capacity=1)
        callers = []
        results = []

        def run_lookup(host):
            try:
                results.append((host, pool.resolve(host, 443, time.monotonic() + 0.45)))
            except Exception as exc:
                results.append((host, exc))

        try:
            for host in ("one.invalid", "two.invalid"):
                thread = threading.Thread(target=run_lookup, args=(host,), daemon=True)
                callers.append(thread)
                thread.start()
            with condition:
                ready = condition.wait_for(lambda: len(started_hosts) == 2, timeout=0.25)
            self.assertTrue(ready, "both fixed workers must be occupied before queue saturation")
            with self.assertRaises(socket.timeout):
                pool.resolve("queued.invalid", 443, time.monotonic() + 0.06)
            with self.assertRaises(socket.timeout):
                pool.resolve("overflow.invalid", 443, time.monotonic() + 0.05)
            self.assertEqual(len(pool._threads), 2, "requests must not create extra resolver threads")
            self.assertLessEqual(pool._jobs.qsize(), 1, "pending resolver jobs must stay within the configured cap")
        finally:
            release.set()
            for thread in callers:
                thread.join(timeout=0.40)
            pool.close(timeout=1.0)

        self.assertTrue(all(not thread.is_alive() for thread in callers))
        self.assertCountEqual(started_hosts, ["one.invalid", "two.invalid"])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(value == [] for _host, value in results))


if __name__ == "__main__":
    unittest.main()
