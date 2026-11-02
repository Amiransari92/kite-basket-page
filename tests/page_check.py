"""Headless-browser check of index.html. Offline: serves the repo locally, intercepts Kite's endpoint.

  python tests/page_check.py   (needs playwright + the services.publisher package on sys.path)
Exits 0 only if: a valid link auto-POSTs the right api_key/orders to Kite's basket URL; an expired
link and a garbage link are refused with a clear message and send nothing.
"""

import datetime
import functools
import http.server
import json
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, r"D:\amir\codeBase\AnalyticalWorkbench\autoTrading\multi-broker-trading")

from playwright.sync_api import sync_playwright  # noqa: E402

from services.publisher.basket import build_order, encode_link  # noqa: E402

PORT = 8765
PAGE = f"http://127.0.0.1:{PORT}"


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def run_case(browser, link, wait_ms=2600):
    posts = []
    ctx = browser.new_context()
    page = ctx.new_page()

    def handle(route):
        posts.append(route.request.post_data or "")
        route.fulfill(status=200, content_type="text/html", body="<h1>kite stub</h1>")

    page.route("https://kite.zerodha.com/**", handle)
    page.goto(link)
    page.wait_for_timeout(700)  # before the 1.5 s auto-submit navigates away
    status = page.locator("#status").inner_text()
    rows = page.locator("#orders tbody tr").count()
    page.wait_for_timeout(wait_ms)  # let the auto-submit (if any) fire and be intercepted
    ctx.close()
    return posts, status, rows


def main() -> int:
    ok = True
    now = datetime.datetime.now(datetime.timezone.utc)
    orders = [
        build_order("WELCORP", "SELL", 1, 2282.9, 0.10),
        build_order("RUBICON", "BUY", 2, 1707.7, 0.10),
    ]
    good = encode_link(PAGE, "TESTKEY123456789", orders, now + datetime.timedelta(hours=1))
    expired = encode_link(PAGE, "TESTKEY123456789", orders, now - datetime.timedelta(minutes=1))
    srv = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        posts, status, rows = run_case(browser, good)
        if len(posts) != 1:
            print("FAIL valid link: expected exactly 1 POST to Kite, got", len(posts)); ok = False
        else:
            form = parse_qs(posts[0])
            sent = json.loads(form["data"][0])
            checks = {
                "api_key": form.get("api_key") == ["TESTKEY123456789"],
                "2 rows shown": rows == 2,
                "2 orders sent": len(sent) == 2,
                "WELCORP leg": sent[0] == orders[0],
                "RUBICON leg": sent[1] == orders[1],
            }
            for name, passed in checks.items():
                print(("PASS " if passed else "FAIL ") + "valid link:", name)
                ok &= passed
        for label, link, needle in (("expired", expired, "expired"), ("garbage", PAGE + "/#d=!!!", "")):
            posts, status, rows = run_case(browser, link)
            passed = not posts and rows == 0 and (needle in status.lower())
            print(("PASS " if passed else "FAIL ") + f"{label} link refused (status: {status!r})")
            ok &= passed
        browser.close()
    srv.shutdown()
    print("ALL OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
