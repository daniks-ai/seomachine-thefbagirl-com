#!/usr/bin/env python3
"""
Tiny localhost file server with CORS, so the Instantly tab can pull the built
sequences and lead CSVs directly instead of having them re-typed into a
javascript_tool call.

Instantly campaigns are created from a logged-in `app.instantly.ai` tab (the
internal API needs the session cookie). The payloads — two 5-step sequences plus
~1-2k lead rows — are far too big to paste into a browser eval by hand, and any
hand-transcription of a lead list is exactly the mistake that
`instantly-lead-paste-safety` exists to prevent. So the page fetches them.

Binds 127.0.0.1 only, serves this vertical's data/ directory read-only.

Usage:
    python3 outreach/ar-sellers/ar8_serve.py            # port 8931
    python3 outreach/ar-sellers/ar8_serve.py --port 9000
"""
import argparse
import functools
import http.server
import socketserver
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"


class CORS(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")
        # Chrome's Private Network Access blocks a public https page from
        # reaching 127.0.0.1 unless both the preflight and the response opt in.
        # Without this the fetch just hangs until it is aborted.
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8931)
    args = ap.parse_args()
    handler = functools.partial(CORS, directory=str(DATA))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"serving {DATA} at http://127.0.0.1:{args.port}/ (ctrl-c to stop)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
