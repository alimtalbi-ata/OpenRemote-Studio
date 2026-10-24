"""R76: cancellation between HTTPS pages, no implicit retries or disclosure."""
import io
import json
import threading
import unittest
from netbox_readonly import NetBoxReadOnly, NetBoxError


class _Response(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class NetBoxCancellationR76Tests(unittest.TestCase):
    def test_offline_never_consults_cancellation_or_transport(self):
        client = NetBoxReadOnly('https://netbox.example', 'token', opener=lambda *_a, **_k: self.fail('network'))
        self.assertEqual(client.devices(online=False, cancelled=lambda: self.fail('callback'))['state'], 'offline')

    def test_pre_cancelled_never_sends_request(self):
        calls = []
        client = NetBoxReadOnly('https://netbox.example', 'token', opener=lambda *_a, **_k: calls.append(1))
        with self.assertRaisesRegex(NetBoxError, '^netbox_request_cancelled$'):
            client.devices(online=True, cancelled=lambda: True)
        self.assertEqual(calls, [])

    def test_invalid_cancel_callback_fails_closed(self):
        client = NetBoxReadOnly('https://netbox.example', 'token')
        with self.assertRaisesRegex(NetBoxError, '^netbox_invalid_cancellation$'):
            client.devices(online=True, cancelled='invalid')

    def test_cancelled_after_first_page_never_fetches_second(self):
        revoked = threading.Event()
        calls = []
        def opener(request, *, timeout):
            calls.append(request.full_url)
            revoked.set()
            return _Response(json.dumps({'results': [{'id': 1, 'name': 'srv-one'}],
                'next': 'https://netbox.example/api/dcim/devices/?limit=100&offset=100'}).encode())
        client = NetBoxReadOnly('https://netbox.example', 'token', opener=opener)
        with self.assertRaisesRegex(NetBoxError, '^netbox_request_cancelled$'):
            client.devices(online=True, cancelled=revoked.is_set)
        self.assertEqual(len(calls), 1)

    def test_cancelled_before_next_page_never_fetches_second(self):
        calls = []
        def opener(request, *, timeout):
            calls.append(request.full_url)
            return _Response(json.dumps({'results': [{'id': 1, 'name': 'srv-one'}],
                'next': 'https://netbox.example/api/dcim/devices/?limit=100&offset=100'}).encode())
        client = NetBoxReadOnly('https://netbox.example', 'token', opener=opener)
        checks = [False, False, False, True]
        def cancelled():
            return checks.pop(0) if checks else True
        with self.assertRaisesRegex(NetBoxError, '^netbox_request_cancelled$'):
            client.devices(online=True, cancelled=cancelled)
        self.assertEqual(len(calls), 1)

    def test_normal_pagination_still_returns_devices(self):
        calls = []
        def opener(request, *, timeout):
            calls.append(request.full_url)
            return _Response(json.dumps({'results': [{'id': 1, 'name': 'srv-one'}], 'next': None}).encode())
        client = NetBoxReadOnly('https://netbox.example', 'token', opener=opener)
        result = client.devices(online=True, cancelled=lambda: False)
        self.assertEqual([d['name'] for d in result['devices']], ['srv-one'])
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
