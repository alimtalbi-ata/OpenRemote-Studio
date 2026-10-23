"""Opt-in, read-only NetBox device inventory client. Author: Abdelhalim Talbi.

No persistence, imports, or network access at module import time. Never log tokens.
"""
import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener


class NetBoxError(RuntimeError):
    """Public, stable error code. Underlying exceptions are never displayed."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _endpoint(origin):
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/') or
            any(ord(c) < 33 for c in origin)):
        raise NetBoxError('netbox_invalid_https_origin')
    try:
        port = parsed.port
    except ValueError:
        raise NetBoxError('netbox_invalid_https_origin') from None
    if port is not None and not (1 <= port <= 65535):
        raise NetBoxError('netbox_invalid_https_origin')
    return f'https://{parsed.netloc}/api/dcim/devices/'


def _clean(value):
    if not isinstance(value, str):
        return ''
    return ''.join(c for c in value if ord(c) >= 32 and ord(c) != 127)[:160]


def _name(value):
    if isinstance(value, dict):
        return _clean(value.get('name') or value.get('display') or value.get('label') or value.get('value') or value.get('address'))
    return _clean(value)


def _device(item):
    if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] <= 0:
        raise NetBoxError('netbox_invalid_device')
    name = _clean(item.get('name') or item.get('display'))
    if not name:
        raise NetBoxError('netbox_invalid_device')
    return {'id': item['id'], 'name': name, 'site': _name(item.get('site')),
            'status': _name(item.get('status')), 'device_type': _name(item.get('device_type')),
            'primary_ip4': _name(item.get('primary_ip4'))}


class NetBoxReadOnly:
    """Explicit GET-only NetBox adapter; no writes, redirects or hidden fallback."""

    def __init__(self, origin, token='', *, opener=None, timeout=5, page_size=100,
                 max_pages=10, max_devices=500):
        self.endpoint = _endpoint(origin)
        if not (0 < timeout <= 30 and 1 <= page_size <= 100 and
                1 <= max_pages <= 50 and 1 <= max_devices <= 5000):
            raise NetBoxError('netbox_invalid_limits')
        self._token = token
        self._opener = opener or build_opener(_RejectRedirects()).open
        self.timeout = timeout
        self.page_size = page_size
        self.max_pages = max_pages
        self.max_devices = max_devices

    def __repr__(self):
        return '<NetBoxReadOnly redacted>'

    def _next_url(self, url, previous_offset):
        candidate = urljoin(self.endpoint, url)
        base, parsed = urlsplit(self.endpoint), urlsplit(candidate)
        if (parsed.scheme != 'https' or parsed.netloc != base.netloc or
                parsed.path != base.path or parsed.fragment or parsed.username or parsed.password):
            raise NetBoxError('netbox_unsafe_pagination')
        params = parse_qs(parsed.query, keep_blank_values=True)
        if set(params) - {'limit', 'offset'} or any(len(v) != 1 for v in params.values()):
            raise NetBoxError('netbox_unsafe_pagination')
        try:
            offset = int(params['offset'][0])
            limit = int(params['limit'][0])
        except (ValueError, KeyError):
            raise NetBoxError('netbox_unsafe_pagination') from None
        if not (offset > previous_offset and 1 <= limit <= self.page_size):
            raise NetBoxError('netbox_unsafe_pagination')
        return candidate, offset

    def devices(self, *, online=False):
        if not online:
            return {'state': 'offline', 'devices': [], 'pages': 0, 'read_only': True}
        if not isinstance(self._token, str) or not self._token or any(c in self._token for c in '\r\n\x00'):
            raise NetBoxError('netbox_token_required')
        url = self.endpoint + f'?limit={self.page_size}&offset=0'
        offset = 0
        results = []
        seen_ids = set()
        for page in range(1, self.max_pages + 1):
            request = Request(url, headers={'Authorization': 'Token ' + self._token,
                                            'Accept': 'application/json'}, method='GET')
            try:
                with self._opener(request, timeout=self.timeout) as response:
                    if getattr(response, 'status', 200) != 200:
                        raise NetBoxError('netbox_http_failure')
                    payload = response.read(2 * 1024 * 1024 + 1)
            except NetBoxError:
                raise
            except (HTTPError, URLError, OSError, TimeoutError, ValueError):
                raise NetBoxError('netbox_network_unavailable') from None
            if len(payload) > 2 * 1024 * 1024:
                raise NetBoxError('netbox_response_too_large')
            try:
                data = json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                raise NetBoxError('netbox_invalid_json') from None
            if not isinstance(data, dict) or not isinstance(data.get('results'), list):
                raise NetBoxError('netbox_invalid_response')
            for item in data['results']:
                device = _device(item)
                if device['id'] in seen_ids:
                    raise NetBoxError('netbox_duplicate_device')
                seen_ids.add(device['id'])
                results.append(device)
                if len(results) > self.max_devices:
                    raise NetBoxError('netbox_device_limit')
            following = data.get('next')
            if following is None:
                return {'state': 'ok', 'devices': results, 'pages': page, 'read_only': True}
            if not isinstance(following, str):
                raise NetBoxError('netbox_unsafe_pagination')
            url, offset = self._next_url(following, offset)
        raise NetBoxError('netbox_page_limit')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only NetBox inventory; offline by default')
    parser.add_argument('--origin', required=True, help='NetBox HTTPS origin (no path or credentials)')
    parser.add_argument('--online', action='store_true', help='Explicitly enable GET requests')
    args = parser.parse_args(argv)
    try:
        client = NetBoxReadOnly(args.origin, os.environ.get('OPENREMOTE_NETBOX_TOKEN', ''))
        result = client.devices(online=args.online)
    except NetBoxError as error:
        print(json.dumps({'state': 'error', 'code': str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
