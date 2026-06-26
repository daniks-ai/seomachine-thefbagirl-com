#!/usr/bin/env python3
"""
GSC Index Status & Sitemap Submitter

Diagnoses why thefbagirl.com pages are/aren't in Google's index:
  1. Verifies API access and lists properties the service account can see.
  2. (Re)submits the sitemap and prints submitted-vs-indexed URL counts.
  3. Pulls 90-day Search Analytics totals + top queries/pages (esp. "daniks").
  4. URL-inspects a priority list and prints each page's coverage verdict.

Prereqs (one-time, owner action):
  - Enable "Google Search Console API" in the Cloud project that owns the
    service account:
    https://console.developers.google.com/apis/api/searchconsole.googleapis.com/overview
  - In Search Console, add the service account email as a property user.

Run from repo root:  python3 gsc_index_status.py
"""

import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()
load_dotenv('data_sources/config/.env')

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    sys.exit("Missing deps. Run: pip install -r data_sources/requirements.txt")

SITE = os.getenv('GSC_SITE_URL', 'https://thefbagirl.com/')
CREDS_PATH = os.getenv('GSC_CREDENTIALS_PATH', 'credentials/gsc-credentials.json')
# The configured key (claude-gsc-readonly) is read-only, so default to the
# read-only scope and skip the sitemap submit. Set GSC_ALLOW_WRITE=1 with a
# read-write key/permission to (re)submit the sitemap.
ALLOW_WRITE = os.getenv('GSC_ALLOW_WRITE') == '1'
SITEMAP = 'https://thefbagirl.com/sitemap-index.xml'
SCOPES = (['https://www.googleapis.com/auth/webmasters'] if ALLOW_WRITE
          else ['https://www.googleapis.com/auth/webmasters.readonly'])

# Inspection URLs must be real https URLs (not the sc-domain: property id).
BASE = 'https://thefbagirl.com'
PRIORITY = [
    f"{BASE}/daniks",
    f"{BASE}/reviews/daniks-ai-review/",
    f"{BASE}/blog/daniks-ai-review-stopped-managing-amazon-ppc-manually/",
    f"{BASE}/blog/daniks-ai-vs-helium-10-adtomic-amazon-ppc-2026/",
    f"{BASE}/blog/daniks-ai-vs-scale-insights-amazon-ppc-2026/",
    f"{BASE}/blog/daniks-ai-vs-pacvue-amazon-ppc-2026/",
    f"{BASE}/blog/daniks-ai-vs-perpetua-amazon-ppc-2026/",
    f"{BASE}/blog/daniks-ai-vs-quartile-amazon-ppc-2026/",
    f"{BASE}/blog/daniks-ai-vs-manual-amazon-ppc-fornel-case-study/",
    f"{BASE}/blog/daniks-brand-story-from-zero-to-top-seller/",
]

ENABLE_HINT = (
    "\n>>> Google Search Console API is not enabled (or not yet propagated).\n"
    ">>> Enable it here, then re-run:\n"
    ">>> https://console.developers.google.com/apis/api/searchconsole.googleapis.com/overview\n"
)


def client():
    if not os.path.exists(CREDS_PATH):
        sys.exit(f"Credentials not found at {CREDS_PATH}")
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    return build('searchconsole', 'v1', credentials=creds, cache_discovery=False)


def guard(e: HttpError):
    msg = str(e)
    if 'accessNotConfigured' in msg or 'has not been used' in msg:
        sys.exit(ENABLE_HINT)
    raise e


def main():
    print(f"Property: {SITE}")
    sc = client()

    # 1) access + property visibility
    try:
        sites = sc.sites().list().execute()
    except HttpError as e:
        guard(e)
    entries = sites.get('siteEntry', [])
    print("\n[1] Properties visible to service account:")
    if not entries:
        print("    NONE — add the service account as a user on the property in Search Console.")
        return
    for s in entries:
        print(f"    {s.get('siteUrl')}  ({s.get('permissionLevel')})")
    owned = {s.get('siteUrl') for s in entries}
    if SITE not in owned:
        print(f"    ! GSC_SITE_URL {SITE} not among visible properties — check exact form (trailing slash / sc-domain:).")

    # 2) (optionally submit) + read sitemaps
    print("\n[2] Sitemap:")
    if ALLOW_WRITE:
        try:
            sc.sitemaps().submit(siteUrl=SITE, feedpath=SITEMAP).execute()
            print(f"    submitted {SITEMAP}")
        except HttpError as e:
            print(f"    submit failed: {str(e)[:160]}")
    else:
        print("    (read-only key — skipping submit; set GSC_ALLOW_WRITE=1 to submit)")
    try:
        sm = sc.sitemaps().list(siteUrl=SITE).execute()
        for s in sm.get('sitemap', []):
            print(f"    {s.get('path')} | lastDownloaded={s.get('lastDownloaded')} "
                  f"warnings={s.get('warnings')} errors={s.get('errors')}")
            for c in s.get('contents', []):
                print(f"        {c.get('type')}: submitted={c.get('submitted')} indexed={c.get('indexed')}")
        if not sm.get('sitemap'):
            print("    none listed")
    except HttpError as e:
        print(f"    list failed: {str(e)[:160]}")

    # 3) search analytics, 90d
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=90)

    def q(dims):
        return sc.searchanalytics().query(siteUrl=SITE, body={
            'startDate': str(start), 'endDate': str(end),
            'dimensions': dims, 'rowLimit': 15}).execute()

    print(f"\n[3] Search Analytics {start}..{end}:")
    try:
        rows = q([]).get('rows', [])
        if rows:
            r = rows[0]
            print(f"    TOTAL clicks={r['clicks']} impressions={r['impressions']}")
        else:
            print("    TOTAL: 0 clicks / 0 impressions (nothing surfacing in search)")
        print("    top queries:")
        for r in q(['query']).get('rows', []):
            print(f"        {int(r['impressions']):>6} impr {int(r['clicks']):>4} clk  {r['keys'][0]}")
        print("    top pages:")
        for r in q(['page']).get('rows', [])[:10]:
            print(f"        {int(r['impressions']):>6} impr  {r['keys'][0]}")
    except HttpError as e:
        print(f"    query failed: {str(e)[:160]}")

    # 4) URL inspection on priority pages
    print("\n[4] URL inspection (priority pages):")
    for url in PRIORITY:
        try:
            res = sc.urlInspection().index().inspect(body={
                'inspectionUrl': url, 'siteUrl': SITE}).execute()
            r = res.get('inspectionResult', {}).get('indexStatusResult', {})
            print(f"    {r.get('coverageState', '?'):<35} {url}")
        except HttpError as e:
            print(f"    inspect failed ({str(e)[:80]}) {url}")


if __name__ == '__main__':
    main()
