#!/usr/bin/env python3
"""Daily UK-seller collection orchestrator (repo-relative).

Pipeline after the browser burst drains new sellers:
  stdin JSON = {"uk": [{s,n,biz,country,addr}, ...], "seen": ["A1..","A2.."]}

Steps:
  1. append `seen` seller-IDs -> data/seen_sellers.txt   (for next run's dedup seed)
  2. append `uk` sellers      -> data/uk_sellers_raw.jsonl (dedup by seller id)
  3. mirror all raw sellers   -> uk_sellers_uk.jsonl      (input for the two scripts)
  4. run domain_discovery.py  (resumable; only new sellers)
  5. run ../scripts/2b_email_harvest.py on discovered domains
  6. run build_uk_csv.py      -> data/instantly_UK_SELLERS.csv (strict-validated)
  7. print NEW emails not yet in data/campaign_added_emails.txt, between markers

The caller imports the printed NEW emails into the Instantly campaign, THEN
appends them to data/campaign_added_emails.txt.

Usage:
  python3 daily_collect.py < drained.json
  python3 daily_collect.py --status            # just print current totals
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)
RAW = DATA / "uk_sellers_raw.jsonl"
SEEN = DATA / "seen_sellers.txt"
MIRROR = HERE / "uk_sellers_uk.jsonl"
DOMAINS_TXT = HERE / "uk_domains.txt"
CSV = DATA / "instantly_UK_SELLERS.csv"
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


def main():
    if "--status" in sys.argv:
        status(); return
    payload = json.loads(sys.stdin.read() or "{}")
    new_uk = payload.get("uk", [])
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
        for r in new_uk:
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
    run([py, str(HERE / "build_uk_csv.py")])

    # 7. new emails delta
    csv_emails = []
    if CSV.exists():
        import csv as _csv
        for row in _csv.DictReader(CSV.open(encoding="utf-8", errors="ignore")):
            e = (row.get("email") or "").strip().lower()
            if e:
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
