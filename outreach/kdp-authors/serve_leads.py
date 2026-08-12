#!/usr/bin/env python3
"""
Tiny CORS file server so the Instantly tab can pull the lead files directly.

Why: the UI CSV upload commits only a handful of rows, and injecting thousands
of leads through javascript_tool hits the payload limit and burns context. The
internal API (POST /api/v2/leads) works fine from the page — it just needs the
data. So the page fetches it from here instead of having it pasted in.

Serves outreach/kdp-authors/data/*.json on 127.0.0.1 only.

Usage:
    python3 outreach/kdp-authors/serve_leads.py --port 8765
"""
import argparse
import functools
import http.server
import socketserver
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    handler = functools.partial(Handler, directory=str(DATA))
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"serving {DATA} on http://127.0.0.1:{args.port}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
