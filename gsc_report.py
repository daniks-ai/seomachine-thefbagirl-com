#!/usr/bin/env python3
"""
GSC Performance Report (read-only)

Richer Search Analytics report for thefbagirl.com:
  A. Trend (recent 28d vs previous 28d, + 90d total)
  B. Top queries by impressions (CTR + avg position)
  C. Brand cluster: 'daniks' queries and 'daniks' pages
  D. Opportunity: high-impression queries stuck at poor positions
  E. Cannibalization: queries where >1 page ranks (split signals)
  F. Top pages by impressions (with avg position)

Read-only. Uses GSC_SITE_URL (sc-domain:thefbagirl.com) and GSC_CREDENTIALS_PATH
from env. Run from repo root:  python3 gsc_report.py
"""

import os
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()
load_dotenv('data_sources/config/.env')

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SITE = os.getenv('GSC_SITE_URL', 'sc-domain:thefbagirl.com')
CREDS = os.getenv('GSC_CREDENTIALS_PATH', './credentials/claude-gsc-readonly-key.json')
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']


def short(url, n=70):
    u = url.replace('https://thefbagirl.com', '')
    return u if len(u) <= n else u[:n - 1] + '…'


def main():
    creds = service_account.Credentials.from_service_account_file(CREDS, scopes=SCOPES)
    sc = build('searchconsole', 'v1', credentials=creds, cache_discovery=False)

    def run(start, end, dims=None, rl=25, filt=None):
        body = {'startDate': str(start), 'endDate': str(end), 'rowLimit': rl}
        if dims:
            body['dimensions'] = dims
        if filt:
            body['dimensionFilterGroups'] = [{'filters': filt}]
        try:
            return sc.searchanalytics().query(siteUrl=SITE, body=body).execute().get('rows', [])
        except HttpError as e:
            print('  query error:', str(e)[:160])
            return []

    last = date.today() - timedelta(days=1)
    s90 = last - timedelta(days=90)

    # A. Trend
    e1, s1 = last, last - timedelta(days=27)
    e0 = s1 - timedelta(days=1)
    s0 = e0 - timedelta(days=27)

    def tot(s, e):
        r = run(s, e)
        return (int(r[0]['clicks']), int(r[0]['impressions'])) if r else (0, 0)

    c1, i1 = tot(s1, e1)
    c0, i0 = tot(s0, e0)
    c9, i9 = tot(s90, last)
    print('=== A. TREND ===')
    print(f'  90d total          : {c9:>4} clk  {i9:>6} impr')
    print(f'  prev 28d {s0}..{e0}: {c0:>4} clk  {i0:>6} impr')
    print(f'  last 28d {s1}..{e1}: {c1:>4} clk  {i1:>6} impr   ({i1-i0:+d} impr)')

    # B. Top queries
    print('\n=== B. TOP QUERIES 90d (impr / clk / CTR / pos) ===')
    for r in run(s90, last, ['query'], 20):
        print(f"  {int(r['impressions']):>5} {int(r['clicks']):>3} {r['ctr']*100:>5.1f}% pos{r['position']:>5.1f}  {r['keys'][0]}")

    # C. Brand cluster
    print("\n=== C1. 'daniks' QUERIES 90d ===")
    daniks_q = run(s90, last, ['query'], 50, [{'dimension': 'query', 'operator': 'contains', 'expression': 'daniks'}])
    if not daniks_q:
        print('  (none)')
    for r in daniks_q:
        print(f"  {int(r['impressions']):>5} {int(r['clicks']):>3} pos{r['position']:>5.1f}  {r['keys'][0]}")
    print("\n=== C2. 'daniks' PAGES 90d ===")
    for r in run(s90, last, ['page'], 50, [{'dimension': 'page', 'operator': 'contains', 'expression': 'daniks'}]):
        print(f"  {int(r['impressions']):>5} {int(r['clicks']):>3} pos{r['position']:>5.1f}  {short(r['keys'][0])}")

    # D. Opportunity: high impressions, poor position
    print('\n=== D. OPPORTUNITY 90d: impr>=15, pos>20 (ranks far, has demand) ===')
    opp = [r for r in run(s90, last, ['query'], 500) if r['impressions'] >= 15 and r['position'] > 20]
    opp.sort(key=lambda r: -r['impressions'])
    for r in opp[:20]:
        print(f"  {int(r['impressions']):>5} impr pos{r['position']:>5.1f}  {r['keys'][0]}")
    if not opp:
        print('  (none)')

    # E. Cannibalization: same query, multiple ranking pages
    print('\n=== E. CANNIBALIZATION 90d: queries with >1 ranking page ===')
    pairs = run(s90, last, ['query', 'page'], 1000)
    byq = {}
    for r in pairs:
        q, p = r['keys']
        byq.setdefault(q, []).append((int(r['impressions']), r['position'], p))
    flagged = {q: v for q, v in byq.items() if len(v) > 1}
    flagged = sorted(flagged.items(), key=lambda kv: -sum(x[0] for x in kv[1]))
    for q, v in flagged[:12]:
        print(f"  '{q}'  ({len(v)} pages):")
        for impr, pos, p in sorted(v, key=lambda x: -x[0]):
            print(f"        {impr:>4} impr pos{pos:>5.1f}  {short(p)}")
    if not flagged:
        print('  (none)')

    # F. Top pages
    print('\n=== F. TOP PAGES 90d (impr / clk / pos) ===')
    for r in run(s90, last, ['page'], 20):
        print(f"  {int(r['impressions']):>5} {int(r['clicks']):>3} pos{r['position']:>5.1f}  {short(r['keys'][0])}")


if __name__ == '__main__':
    main()
