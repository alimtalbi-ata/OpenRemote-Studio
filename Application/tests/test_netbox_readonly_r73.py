"""No external network: fake HTTPS transport, real JSON/pagination contracts."""
import io
import json
import unittest
from urllib.error import URLError
from netbox_readonly import NetBoxError, NetBoxReadOnly, main

ORIGIN = 'https://netbox.example.test'


class Reply(io.BytesIO):
    status = 200


class FakeOpen:
    def __init__(self, *pages):
        self.pages = list(pages)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        item = self.pages.pop(0)
        if isinstance(item, Exception):
            raise item
        return Reply(json.dumps(item).encode())


def page(ids, following=None):
    return {'results': [{'id': i, 'name': f'device-{i}', 'site': {'name': 'PAR'}} for i in ids],
            'next': following}


class NetBoxR73Tests(unittest.TestCase):
    def test_offline_never_calls_transport(self):
        fake = FakeOpen()
        result = NetBoxReadOnly(ORIGIN, opener=fake).devices()
        self.assertEqual(result['state'], 'offline')
        self.assertEqual(fake.requests, [])

    def test_https_and_credentialless_origin_required(self):
        for origin in ('http://netbox.example.test', 'https://u:p@netbox.example.test',
                       'https://netbox.example.test/api', 'https://netbox.example.test/?token=x',
                       'https://netbox.example.test/#x', 'https://netbox.example.test\n'):
            with self.subTest(origin=origin), self.assertRaises(NetBoxError):
                NetBoxReadOnly(origin)

    def test_two_pages_read_only_and_whitelist(self):
        fake = FakeOpen(page([1], '/api/dcim/devices/?limit=2&offset=2'), page([2]))
        result = NetBoxReadOnly(ORIGIN, 'sensitive', opener=fake, page_size=2).devices(online=True)
        self.assertEqual(result['pages'], 2)
        self.assertEqual([d['id'] for d in result['devices']], [1, 2])
        self.assertEqual(result['devices'][0]['site'], 'PAR')
        self.assertEqual(set(result['devices'][0]), {'id','name','site','status','device_type','primary_ip4'})
        self.assertEqual([r.get_method() for r, _ in fake.requests], ['GET', 'GET'])
        self.assertEqual(fake.requests[0][0].get_header('Authorization'), 'Token sensitive')

    def test_reject_cross_origin_token_and_redirect_like_next(self):
        for next_url in ('https://evil.test/api/dcim/devices/?limit=1&offset=1',
                         '/api/dcim/devices/?token=secret&offset=1&limit=1',
                         '/api/dcim/devices/?offset=0&limit=1',
                         '/api/dcim/devices/?offset=1&limit=200',
                         '/api/dcim/sites/?offset=1&limit=1'):
            with self.subTest(next_url=next_url), self.assertRaisesRegex(NetBoxError, 'unsafe_pagination'):
                NetBoxReadOnly(ORIGIN, 'token', opener=FakeOpen(page([1], next_url))).devices(online=True)

    def test_duplicate_id_and_device_limit_fail_closed(self):
        with self.assertRaisesRegex(NetBoxError, 'duplicate_device'):
            NetBoxReadOnly(ORIGIN, 'token', opener=FakeOpen(page([1, 1]))).devices(online=True)
        with self.assertRaisesRegex(NetBoxError, 'device_limit'):
            NetBoxReadOnly(ORIGIN, 'token', opener=FakeOpen(page([1, 2])), max_devices=1).devices(online=True)

    def test_page_limit_fails_without_partial_data(self):
        fake = FakeOpen(page([1], '/api/dcim/devices/?offset=1&limit=1'))
        with self.assertRaisesRegex(NetBoxError, 'page_limit'):
            NetBoxReadOnly(ORIGIN, 'token', opener=fake, max_pages=1).devices(online=True)

    def test_secret_never_in_error_or_repr(self):
        fake = FakeOpen(URLError('token=TOPSECRET network error'))
        client = NetBoxReadOnly(ORIGIN, 'TOPSECRET', opener=fake)
        with self.assertRaises(NetBoxError) as caught:
            client.devices(online=True)
        self.assertNotIn('TOPSECRET', str(caught.exception) + repr(client))
        self.assertEqual(str(caught.exception), 'netbox_network_unavailable')

    def test_token_missing_blocks_online(self):
        fake = FakeOpen()
        with self.assertRaisesRegex(NetBoxError, 'token_required'):
            NetBoxReadOnly(ORIGIN, opener=fake).devices(online=True)
        self.assertEqual(fake.requests, [])

    def test_malformed_json_and_payload(self):
        for value in ({'results': {}}, {'results': [{'id': True, 'name': 'bad'}]}):
            with self.subTest(value=value), self.assertRaises(NetBoxError):
                NetBoxReadOnly(ORIGIN, 'token', opener=FakeOpen(value)).devices(online=True)

    def test_cli_offline_default(self):
        from contextlib import redirect_stdout
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(['--origin', ORIGIN]), 0)
        self.assertEqual(json.loads(out.getvalue())['state'], 'offline')


if __name__ == '__main__':
    unittest.main()
