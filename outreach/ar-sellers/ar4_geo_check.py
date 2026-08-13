#!/usr/bin/env python3
"""
Argentina lead engine, step 4: prove each non-.ar domain is actually Argentine.

Why this exists: a Google SERP run with `location_name: Argentina` still returns
Spanish and Mexican sites at the top for "vender en amazon…" queries — the
Spanish-language Amazon-consulting SERP is dominated by Spain. Mailing those
inside an Argentina campaign is both a relevance miss and a copy mismatch (the
sequence talks pesos, AFIP and exporting *from* Argentina).

`.ar`/`.com.ar` domains are self-evidently Argentine and skipped for free.
Everything else gets one homepage fetch and is scored on hard signals:
  +54 phone codes, CUIT/CUIL/AFIP/IVA/monotributo, provinces and AMBA place
  names, ARS pricing, "Argentina" itself.
Negative signals (Spain/Mexico markers: +34, +52, NIF/CIF, RFC, CDMX, euros)
subtract, so a Spanish agency whose blog merely *mentions* Argentina fails.

Output: data/ar_geo.json  {domain: {"ar": bool, "score": int, "hits": [...]}}

Usage:
    python3 outreach/ar-sellers/ar4_geo_check.py
    python3 outreach/ar-sellers/ar4_geo_check.py --workers 24 --recheck
"""
import argparse
import concurrent.futures as cf
import gzip
import json
import re
import ssl
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
LEADS = DATA / "ar_leads.jsonl"
OUT = DATA / "ar_geo.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

POS = [
    (3, re.compile(r"\+ ?54[\s\-\.\(]", re.I)),
    (3, re.compile(r"\b(cuit|cuil|monotribut|afip|arca\.gob\.ar)\b", re.I)),
    (2, re.compile(r"\bargentina\b", re.I)),
    (2, re.compile(r"\b(caba|c\.a\.b\.a|capital federal|"
                   r"ciudad aut[oó]noma de buenos aires)\b", re.I)),
    (2, re.compile(r"\$ ?ars|\bpesos argentinos\b|\bARS\b")),
    (1, re.compile(r"\b(buenos aires|c[oó]rdoba|rosario|mendoza|la plata|"
                   r"mar del plata|tucum[aá]n|salta|neuqu[eé]n|bariloche|"
                   r"santa fe|bah[ií]a blanca|quilmes|vicente l[oó]pez|"
                   r"san isidro|palermo|belgrano|microcentro)\b", re.I)),
    (1, re.compile(r"\b(mercado ?libre|mercado ?pago|tienda ?nube|"
                   r"andreani|oca ?e-?pak|correo argentino)\b", re.I)),
]
NEG = [
    (3, re.compile(r"\+ ?34[\s\-\.\(]")),
    (3, re.compile(r"\+ ?52[\s\-\.\(]")),
    (2, re.compile(r"\b(nif|cif|iva incluido en espa|seguridad social|"
                   r"\brfc\b|sat\.gob\.mx|cdmx|ciudad de m[eé]xico)\b", re.I)),
    (2, re.compile(r"€\s?\d|\bIVA 21%|\bmadrid\b|\bbarcelona\b|"
                   r"\bvalencia\b|\bguadalajara\b|\bmonterrey\b", re.I)),
]

_lock = threading.Lock()


def fetch(url, timeout=14):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-AR,es;q=0.9", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(1_500_000)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "ignore")


def score(html):
    hits, s = [], 0
    for w, rx in POS:
        if rx.search(html):
            s += w
            hits.append("+" + rx.pattern[:18])
    for w, rx in NEG:
        if rx.search(html):
            s -= w
            hits.append("-" + rx.pattern[:18])
    return s, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--recheck", action="store_true")
    ap.add_argument("--threshold", type=int, default=3)
    args = ap.parse_args()

    leads = [json.loads(l) for l in LEADS.read_text().splitlines() if l.strip()]
    store = json.loads(OUT.read_text()) if OUT.exists() and not args.recheck else {}

    todo = []
    for r in leads:
        d = r["domain"]
        if d in store:
            continue
        if d.endswith(".ar"):
            store[d] = {"ar": True, "score": 99, "hits": ["ar_tld"]}
        else:
            todo.append(d)
    print(f"{len(leads)} leads | {sum(1 for v in store.values() if v['score']==99)}"
          f" .ar TLD auto-pass | {len(todo)} to fetch")

    done = [0]

    def run(d):
        s, hits, ok = -99, ["unreachable"], False
        for scheme in ("https://", "http://"):
            try:
                html = fetch(scheme + d)
                s, hits = score(html)
                ok = True
                break
            except Exception:
                continue
        with _lock:
            store[d] = {"ar": bool(ok and s >= args.threshold),
                        "score": s, "hits": hits[:8]}
            done[0] += 1
            if done[0] % 100 == 0:
                OUT.write_text(json.dumps(store, ensure_ascii=False))
                print(f"  {done[0]}/{len(todo)}")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    OUT.write_text(json.dumps(store, ensure_ascii=False))

    ar = sum(1 for v in store.values() if v["ar"])
    dead = sum(1 for v in store.values() if v["score"] == -99)
    print(f"\nArgentine: {ar}/{len(store)} | unreachable {dead} -> {OUT}")


if __name__ == "__main__":
    main()
