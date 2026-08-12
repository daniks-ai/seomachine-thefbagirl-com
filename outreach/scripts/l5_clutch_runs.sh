#!/bin/bash
# Layer 5 wave: more Clutch categories/pages via memo23~apify-clutch-cheerio
# (30 items per run, free-tier cap). Appends to layer5_clutch_raw.jsonl.
set -u
cd "$(dirname "$0")/../.."
APIFY_TOKEN=$(grep -E '^APIFY_TOKEN=' data_sources/config/.env | cut -d= -f2 | tr -d ' "')
OUT=outreach/data/layer5_clutch_raw.jsonl
URLS=()
# PPC category continues past page 16 (verified page 17 live)
for p in 18 19 20 21 22 23 24 25; do URLS+=("https://clutch.co/us/agencies/ppc?page=$p"); done
# digital-marketing US — big category, highly relevant for white-label
for p in $(seq 1 14); do URLS+=("https://clutch.co/us/agencies/digital-marketing?page=$p"); done
# digital/ecommerce marketing adjacents
for p in 1 2 3 4; do URLS+=("https://clutch.co/us/agencies/digital/ecommerce?page=$p"); done

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
  USED=$(curl -s "https://api.apify.com/v2/users/me/limits?token=$APIFY_TOKEN" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['current']['monthlyUsageUsd'])")
  echo "  got $N | usage $USED"
  STOP=$(python3 -c "print(1 if float('$USED') > 4.85 else 0)")
  if [ "$STOP" = "1" ]; then echo "BUDGET STOP at $USED"; break; fi
done
echo "DONE lines: $(wc -l < $OUT 2>/dev/null)"
