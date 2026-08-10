#!/usr/bin/env bash
# Purge Cloudflare cache for thefbagirl.com.
# Usage:
#   export CF_API_TOKEN=<your token with Zone->Cache Purge permission>
#   bash cf_purge_thefbagirl.sh            # purge everything (recommended after the prune)
#   bash cf_purge_thefbagirl.sh urls.txt   # purge only URLs listed in urls.txt (one per line)
set -euo pipefail
: "${CF_API_TOKEN:?export CF_API_TOKEN first}"

# resolve zone id from the domain
ZONE_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=thefbagirl.com" \
  -H "Authorization: Bearer $CF_API_TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"][0]["id"])')
echo "zone id: $ZONE_ID"

if [ "${1:-}" = "" ]; then
  echo "Purging EVERYTHING..."
  BODY='{"purge_everything":true}'
else
  echo "Purging URLs from $1 ..."
  BODY=$(python3 -c 'import sys,json;print(json.dumps({"files":[l.strip() for l in open(sys.argv[1]) if l.strip()]}))' "$1")
fi

curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" \
  --data "$BODY" | python3 -m json.tool
