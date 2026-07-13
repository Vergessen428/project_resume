#!/usr/bin/env python3
"""Serve and request the static demo exactly as a static host would.

This intentionally uses only the standard library. It catches broken root-relative
asset paths and accidental external dependencies without pretending to be a browser
interaction test.
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATIC_ROOT = os.path.join(ROOT, "static_demo")


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return


def fetch(base_url, path, expected_status=200):
    try:
        with urlopen(base_url + path, timeout=5) as response:
            status = response.status
            body = response.read()
            content_type = response.headers.get_content_type()
    except HTTPError as exc:
        status = exc.code
        body = exc.read()
        content_type = exc.headers.get_content_type()
    if status != expected_status:
        raise AssertionError(f"{path}: expected HTTP {expected_status}, got {status}")
    return content_type, body


def main():
    handler = partial(QuietStaticHandler, directory=STATIC_ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        checks = {}
        for path in ("/", "/styles.css", "/demo_data.js", "/app.js"):
            content_type, body = fetch(base_url, path)
            if not body:
                raise AssertionError(f"{path}: empty response")
            checks[path] = {"content_type": content_type, "bytes": len(body)}
        _, index = fetch(base_url, "/")
        html = index.decode("utf-8")
        if "/demo_data.js" not in html or "/app.js" not in html:
            raise AssertionError("index.html does not load the demo data and app scripts")
        if html.index("/demo_data.js") > html.index("/app.js"):
            raise AssertionError("demo_data.js must load before app.js")
        _, missing = fetch(base_url, "/does-not-exist", expected_status=404)
        if not missing:
            raise AssertionError("missing asset response should contain an HTTP error page")
        print(json.dumps({"ok": True, "base": base_url, "checks": checks}, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
