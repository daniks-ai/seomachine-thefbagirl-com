#!/usr/bin/env python3
"""
Pre-send deliverability triage for the [AU] lists: which domains cannot receive
mail at all?

A domain with no MX record (and no A-record fallback) hard-bounces every message
sent to it. Bounces on warmed sending domains are the expensive kind of mistake,
so this runs before the campaign works through the list — it is pure DNS, no
SMTP handshake, so it costs nothing and cannot be mistaken for spam probing.

Reads data/instantly_AU.csv + data/instantly_AU2.csv, resolves each unique email
domain with `dig`, writes:
  data/au_mx_dead.txt   — domains with no mail route (emails here will bounce)
  data/au_mx_report.json — full per-domain verdict for later reference

Usage:
    python3 outreach/scripts/au3_mx_check.py [--workers 30]
"""
import argparse
import csv
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
SOURCES = ("instantly_AU.csv", "instantly_AU2.csv")


def dig(domain, rrtype, patient=False):
    """Return answer lines for one record type, or [] on failure/timeout."""
    timing = ["+time=8", "+tries=3"] if patient else ["+time=3", "+tries=1"]
    try:
        out = subprocess.run(
            ["dig", "+short", *timing, rrtype, domain],
            capture_output=True, text=True, timeout=30 if patient else 12).stdout
    except (subprocess.TimeoutExpired, OSError):
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]


def verdict(domain, patient=False):
    mx = [l for l in dig(domain, "MX", patient) if not l.startswith(";")]
    if mx:
        return {"domain": domain, "status": "mx", "records": mx[:3]}
    # RFC 5321: with no MX, senders fall back to the A/AAAA record
    a = dig(domain, "A", patient)
    if a:
        return {"domain": domain, "status": "a_fallback", "records": a[:2]}
    # A fast parallel sweep times out on healthy domains often enough that the
    # first "dead" verdict is not trustworthy (measured: 5 of 8 were false).
    # Anything that looks dead gets one patient, serial re-check.
    if not patient:
        return verdict(domain, patient=True)
    ns = dig(domain, "NS", patient=True)
    return {"domain": domain, "status": "dead",
            "records": [], "has_ns": bool(ns)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=30)
    args = ap.parse_args()

    emails_by_domain = {}
    for name in SOURCES:
        p = DATA / name
        if not p.exists():
            continue
        for r in csv.DictReader(p.open(encoding="utf-8")):
            dom = r["email"].split("@", 1)[1].lower()
            emails_by_domain.setdefault(dom, []).append(r["email"])

    domains = sorted(emails_by_domain)
    print(f"checking MX for {len(domains)} domains "
          f"({sum(len(v) for v in emails_by_domain.values())} addresses)")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(verdict, domains))

    dead = [r for r in results if r["status"] == "dead"]
    fallback = [r for r in results if r["status"] == "a_fallback"]
    (DATA / "au_mx_report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    (DATA / "au_mx_dead.txt").write_text(
        "\n".join(e for r in dead for e in emails_by_domain[r["domain"]]), encoding="utf-8")

    print(f"  mx ok:      {len(results) - len(dead) - len(fallback)}")
    print(f"  a-fallback: {len(fallback)} (accepts mail, unusual setup)")
    print(f"  DEAD:       {len(dead)} domains "
          f"= {sum(len(emails_by_domain[r['domain']]) for r in dead)} addresses will bounce")
    for r in dead:
        print(f"    {r['domain']}: {', '.join(emails_by_domain[r['domain']])}")


if __name__ == "__main__":
    main()
