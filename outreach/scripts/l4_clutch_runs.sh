#!/bin/bash
# Layer 4: Clutch.co via memo23~apify-clutch-cheerio, one listing URL per run
# (actor free tier caps 30 items per run). Appends all items to
# outreach/data/layer4_clutch_all.jsonl
set -u
cd "$(dirname "$0")/../.."
APIFY_TOKEN=$(grep -E '^APIFY_TOKEN=' data_sources/config/.env | cut -d= -f2 | tr -d ' "')
OUT=outreach/data/layer4_clutch_all.jsonl
URLS=()
for p in 2 3 4 5 6 7 8; do URLS+=("https://clutch.co/us/agencies/ppc/amazon?page=$p"); done
for p in $(seq 1 16); do URLS+=("https://clutch.co/us/agencies/ppc?page=$p"); done

for u in "${URLS[@]}"; do
  echo "=== $u"
  RESP=$(curl -s -X POST "https://api.apify.com/v2/acts/memo23~apify-clutch-cheerio/run-sync-get-dataset-items?token=$APIFY_TOKEN&timeout=300" \
    -H "Content-Type: application/json" \
    -d "{\"startUrls\":[{\"url\":\"$u\"}],\"maxItems\":30,\"maxCostUsd\":1,\"includeCompanyReviews\":false,\"enrichEmails\":false,\"maxConcurrency\":10}")
  N=$(echo "$RESP" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print(0); raise SystemExit
if isinstance(d,list):
    with open('$OUT','a') as f:
        for it in d: f.write(json.dumps(it,ensure_ascii=False)+'\n')
    print(len(d))
else:
    print(0)
")
  echo "  got $N items"
  # stop if the monthly cap is nearly reached
  USED=$(curl -s "https://api.apify.com/v2/users/me/limits?token=$APIFY_TOKEN" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['current']['monthlyUsageUsd'])")
  echo "  usage: $USED"
  python3 - <<PY
used=float("$USED")
import sys
sys.exit(1 if used > 4.5 else 0)
PY
  if [ $? -ne 0 ]; then echo "BUDGET STOP at $USED"; break; fi
done
echo "DONE. total lines: $(wc -l < $OUT 2>/dev/null)"
