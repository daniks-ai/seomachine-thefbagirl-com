#!/usr/bin/env python3
"""Daily MX-seller collection orchestrator (repo-relative, no scratchpad).

Pipeline after the browser burst drains new sellers:
  stdin JSON = {"mx": [{s,n,biz,country,addr}, ...], "seen": ["A1..","A2.."]}

Steps:
  1. append `seen` seller-IDs -> data/seen_sellers.txt   (for next run's dedup seed)
  2. append `mx` sellers      -> data/mx_sellers_raw.jsonl (dedup by seller id)
  3. mirror all raw sellers   -> mx_sellers_mx.jsonl      (input for the two scripts)
  4. run domain_discovery.py  (resumable; only new sellers)
  5. run ../scripts/2b_email_harvest.py on discovered domains
  6. run build_mx_csv.py      -> data/instantly_MX_SELLERS.csv (strict-validated)
  7. print NEW emails not yet in data/campaign_added_emails.txt, between markers

The caller (daily routine) imports the printed NEW emails into the Instantly
campaign, THEN appends them to data/campaign_added_emails.txt.

Usage:
  python3 daily_collect.py < drained.json
  python3 daily_collect.py --status            # just print current totals
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)
RAW = DATA / "mx_sellers_raw.jsonl"
SEEN = DATA / "seen_sellers.txt"
ASIN_POOL = DATA / "asin_pool.txt"
ASIN_CURSOR = DATA / "asin_cursor.txt"
MIRROR = HERE / "mx_sellers_mx.jsonl"
DOMAINS_TXT = HERE / "mx_domains.txt"
CSV = DATA / "instantly_MX_SELLERS.csv"
ADDED = DATA / "campaign_added_emails.txt"
HARVEST = HERE.parents[1] / "outreach/scripts/2b_email_harvest.py"


def load_raw():
    seen, recs = set(), []
    if RAW.exists():
        for l in RAW.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                if r["s"] not in seen:
                    seen.add(r["s"]); recs.append(r)
    return recs, seen


def status():
    recs, _ = load_raw()
    n_csv = 0
    if CSV.exists():
        n_csv = max(0, len(CSV.read_text().splitlines()) - 1)
    n_added = len({x.strip().lower() for x in ADDED.read_text().splitlines() if x.strip()}) if ADDED.exists() else 0
    print(f"raw_sellers={len(recs)} validated_csv_leads={n_csv} campaign_added={n_added}")


def next_asins(n):
    """Print the next N unprocessed ASINs from the diverse pool and advance the
    cursor. Lets the daily routine work progressively through ~23k pre-harvested
    products (far more diverse than re-crawling bestsellers, which saturates)."""
    if not ASIN_POOL.exists():
        return
    pool = [x.strip() for x in ASIN_POOL.read_text().splitlines() if x.strip()]
    cur = 0
    if ASIN_CURSOR.exists():
        try: cur = int(ASIN_CURSOR.read_text().strip() or "0")
        except ValueError: cur = 0
    if cur >= len(pool):
        cur = 0  # wrap around; by now bestsellers have rotated anyway
    chunk = pool[cur:cur + n]
    ASIN_CURSOR.write_text(str(cur + len(chunk)))
    for a in chunk:
        print(a)


def main():
    if "--status" in sys.argv:
        status(); return
    if "--next-asins" in sys.argv:
        i = sys.argv.index("--next-asins")
        n = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 2500
        next_asins(n); return
    payload = json.loads(sys.stdin.read() or "{}")
    new_mx = payload.get("mx", [])
    new_seen = payload.get("seen", [])

    # 1. seen ids
    seen_ids = set()
    if SEEN.exists():
        seen_ids = {x.strip() for x in SEEN.read_text().splitlines() if x.strip()}
    added_seen = [s for s in new_seen if s and s not in seen_ids]
    if added_seen:
        with SEEN.open("a") as f:
            for s in added_seen:
                f.write(s + "\n")

    # 2. raw sellers (dedup by id)
    recs, have = load_raw()
    n_new_sellers = 0
    with RAW.open("a") as f:
        for r in new_mx:
            if r.get("s") and r["s"] not in have:
                have.add(r["s"]); recs.append(r); n_new_sellers += 1
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 3. mirror for the two scripts
    with MIRROR.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 4-6. pipeline
    py = sys.executable or "python3"
    def run(cmd):
        try:
            subprocess.run(cmd, cwd=str(HERE), timeout=900, check=False)
        except Exception as e:
            print(f"[warn] {cmd}: {e}", file=sys.stderr)
    run([py, str(HERE / "domain_discovery.py")])
    if DOMAINS_TXT.exists():
        run([py, str(HARVEST), "--domains-file", str(DOMAINS_TXT), "--workers", "10"])
    run([py, str(HERE / "build_mx_csv.py")])

    # 7. new emails delta
    csv_emails = []
    if CSV.exists():
        import csv as _csv
        for row in _csv.DictReader(CSV.open(encoding="utf-8", errors="ignore")):
            e = (row.get("email") or "").strip().lower()
            # skip the known bad brand-collision lead
            if e and "eeni-edit.com" not in e:
                csv_emails.append(e)
    added = {x.strip().lower() for x in ADDED.read_text().splitlines() if x.strip()} if ADDED.exists() else set()
    new_emails = [e for e in dict.fromkeys(csv_emails) if e not in added]

    print(f"[daily] new_sellers_this_run={n_new_sellers} total_raw={len(recs)} "
          f"validated_leads={len(csv_emails)} already_in_campaign={len(added)} "
          f"NEW_to_add={len(new_emails)}")
    print("=== NEW_EMAILS_TO_ADD ===")
    for e in new_emails:
        print(e)
    print("=== END ===")


if __name__ == "__main__":
    main()
