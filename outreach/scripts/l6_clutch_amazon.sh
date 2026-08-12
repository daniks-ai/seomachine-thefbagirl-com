#!/bin/bash
# Layer 6: TARGETED on-ICP Clutch scrape — Amazon PPC / ecommerce agencies only
# (national deep pages + by-city Amazon pages, which surface agencies the
# national list misses). memo23~apify-clutch-cheerio, 30 items/run, listing URL
# per run. Stops at BUDGET_STOP (default $18) so it can't blow past your cap.
#
# Run AFTER raising the Apify monthly cap in Console -> Billing.
#   BUDGET_STOP=18 bash outreach/scripts/l6_clutch_amazon.sh
set -u
cd "$(dirname "$0")/../.."
APIFY_TOKEN=$(grep -E '^APIFY_TOKEN=' data_sources/config/.env | cut -d= -f2 | tr -d ' "')
OUT=outreach/data/layer6_clutch_raw.jsonl
BUDGET_STOP="${BUDGET_STOP:-18}"

URLS=()
# National Amazon PPC — extend beyond the pages L4 already took (1-8)
for p in $(seq 9 20); do URLS+=("https://clutch.co/us/agencies/ppc/amazon?page=$p"); done
# By-city Amazon consultants (distinct agencies vs the national list)
for c in new-york los-angeles chicago dallas houston miami atlanta boston \
         seattle denver austin san-francisco san-diego phoenix philadelphia \
         minneapolis nashville portland las-vegas charlotte tampa orlando \
         detroit salt-lake-city raleigh columbus; do
  URLS+=("https://clutch.co/agencies/ppc/amazon/$c")
done
# Ecommerce marketing category (Amazon-adjacent, on-ICP)
for p in $(seq 1 10); do URLS+=("https://clutch.co/us/agencies/digital/ecommerce?page=$p"); done

echo "planned ${#URLS[@]} listing URLs, budget stop \$$BUDGET_STOP"
for u in "${URLS[@]}"; do
  echo "=== $u"
  RESP=$(curl -s -X POST "https://api.apify.com/v2/acts/memo23~apify-clutch-cheerio/run-sync-get-dataset-items?token=$APIFY_TOKEN&timeout=300" \
    -H "Content-Type: application/json" \
    -d "{\"startUrls\":[{\"url\":\"$u\"}],\"maxItems\":30,\"maxCostUsd\":1,\"includeCompanyReviews\":false,\"enrichEmails\":false,\"maxConcurrency\":10}")
  N=$(echo "$RESP" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('ERR'); raise SystemExit
if isinstance(d,list):
    with open('$OUT','a') as f:
        for it in d: f.write(json.dumps(it,ensure_ascii=False)+'\n')
    print(len(d))
else:
    print('BLOCK:'+str(d.get('error',{}).get('type','?')))
")
  USED=$(curl -s "https://api.apify.com/v2/users/me/limits?token=$APIFY_TOKEN" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['current']['monthlyUsageUsd'])")
  echo "  got $N | usage \$$USED"
  case "$N" in BLOCK:*) echo "  >> Apify blocked (cap not raised or payment). Stopping."; break;; esac
  STOP=$(python3 -c "print(1 if float('$USED') > $BUDGET_STOP else 0)")
  if [ "$STOP" = "1" ]; then echo "BUDGET STOP at \$$USED"; break; fi
done
echo "DONE. raw lines: $(wc -l < $OUT 2>/dev/null)"
echo "Next: normalize (dedup vs L1-5) -> harvest emails -> build CSV -> load."
