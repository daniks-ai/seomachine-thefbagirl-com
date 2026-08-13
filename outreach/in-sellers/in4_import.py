#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 4: import the CSV into Instantly.

Instantly has no bulk-lead endpoint — `POST /api/v2/leads` takes one lead per
call — and the in-app internal API authenticates by session cookie, which is why
the first 1,972 leads had to be pushed from a browser tab. With an API key
(Settings -> Integrations, value shown once at creation) the same thing runs
here instead, which keeps the lead list out of any browser/model round-trip.

Dedupe is server-side: `skip_if_in_workspace` / `skip_if_in_campaign` mean the
whole CSV can be re-sent safely. A lead that already existed comes back 200 with
a `campaign` field that is *not* our campaign id — that is how added vs skipped
is counted (there is no distinct status code for it).

The key is read from a file, never from argv, so it stays out of shell history
and the process list. Nothing here writes the key anywhere.

Usage:
    python3 outreach/in-sellers/in4_import.py --key-file ~/.instantly_key \
        --csv data/instantly_IN_SELLERS.csv --campaign <uuid>
    python3 outreach/in-sellers/in4_import.py ... --verify   # count only
"""
import argparse
import concurrent.futures as cf
import csv
import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.instantly.ai/api/v2"
CAMPAIGN = "637c42b4-96a0-4d21-8abd-537dc9fe173f"   # Daniks.AI — Amazon Sellers India

_lock = threading.Lock()


def request(path, key, payload=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method or ("POST" if data else "GET"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "Accept": "application/json",
                 # api.instantly.ai sits behind Cloudflare and 403s the default
                 # python-urllib agent outright
                 "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0 Safari/537.36")})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read() or b"{}")


def company_from(domain):
    label = re.sub(r"\.(co\.in|com|in|net|org|shop|store|online|life|co|me|"
                   r"biz|tech|pro)$", "", domain).split(".")[-1]
    return re.sub(r"[-_.]+", " ", label).title()[:55]


def count_leads(key, campaign):
    total, after = 0, None
    while True:
        body = {"campaign": campaign, "limit": 100}
        if after:
            body["starting_after"] = after
        _s, j = request("/leads/list", key, body)
        total += len(j.get("items") or [])
        after = j.get("next_starting_after")
        if not after:
            return total


def campaign_emails(key, campaign):
    """(email, id) for every lead in the campaign."""
    out, after = [], None
    while True:
        body = {"campaign": campaign, "limit": 100}
        if after:
            body["starting_after"] = after
        _s, j = request("/leads/list", key, body)
        for it in j.get("items") or []:
            out.append((it["email"].lower(), it["id"]))
        after = j.get("next_starting_after")
        if not after:
            return out


def prune(key, campaign, pool_csv, apply):
    """Drop leads the current filter set would no longer accept.

    The first 1,972 leads went in before the truncated-local / typo-domain /
    enterprise-queue filters existed, so the campaign holds addresses that are
    not in the pool any more. The pool CSV is every address that survives every
    filter, so "in the campaign but not in the pool" is exactly the reject list.
    """
    p = Path(pool_csv)
    if not p.is_absolute():
        p = HERE / p
    pool = {r["email"].strip().lower() for r in csv.DictReader(p.open(encoding="utf-8"))}
    leads = campaign_emails(key, campaign)
    stale = [(e, i) for e, i in leads if e not in pool]
    print(f"{len(leads)} in campaign, {len(pool)} in pool -> "
          f"{len(stale)} to remove")
    for e, _i in stale[:15]:
        print("   ", e)
    if not apply or not stale:
        print("(dry run — pass --apply to delete)" if stale else "nothing to do")
        return
    removed = 0
    for chunk in [stale[i:i + 100] for i in range(0, len(stale), 100)]:
        _s, j = request("/leads", key,
                        {"campaign_id": campaign, "ids": [i for _e, i in chunk]},
                        method="DELETE")
        removed += j.get("count", 0)
    print(f"removed {removed}; campaign now holds {count_leads(key, campaign)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--prune-against")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--csv", default="data/instantly_IN_SELLERS.csv")
    ap.add_argument("--campaign", default=CAMPAIGN)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    key = Path(args.key_file).expanduser().read_text().strip()
    if args.verify:
        print(f"campaign holds {count_leads(key, args.campaign)} leads")
        return
    if args.prune_against:
        return prune(key, args.campaign, args.prune_against, args.apply)

    p = Path(args.csv)
    if not p.is_absolute():
        p = HERE / p
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} rows from {p.name} -> campaign {args.campaign}",
          flush=True)

    stat = {"added": 0, "skipped": 0, "err": 0, "done": 0}

    def push(row):
        email = row["email"].strip()
        dom = email.split("@")[1]
        payload = {"campaign": args.campaign, "email": email,
                   "company_name": row.get("company_name") or company_from(dom),
                   "website": row.get("website") or f"https://{dom}",
                   "skip_if_in_workspace": True, "skip_if_in_campaign": True}
        try:
            _s, j = request("/leads", key, payload)
            key_name = "added" if j.get("campaign") == args.campaign else "skipped"
        except urllib.error.HTTPError as ex:
            key_name = "err"
            if stat["err"] < 5:
                print(f"  {email}: HTTP {ex.code} {ex.read()[:120]}", flush=True)
        except Exception as ex:
            key_name = "err"
            if stat["err"] < 5:
                print(f"  {email}: {str(ex)[:100]}", flush=True)
        with _lock:
            stat[key_name] += 1
            stat["done"] += 1
            if stat["done"] % 250 == 0:
                print(f"  {stat['done']}/{len(rows)} | added {stat['added']} "
                      f"skipped {stat['skipped']} err {stat['err']}", flush=True)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(push, rows))

    print(f"\nadded {stat['added']}, already present {stat['skipped']}, "
          f"errors {stat['err']}")
    print(f"campaign now holds {count_leads(key, args.campaign)} leads")


if __name__ == "__main__":
    main()
