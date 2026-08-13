#!/usr/bin/env python3
"""
Argentina lead engine, layer B: Google organic SERP via DataForSEO.

Maps (ar1) finds businesses with a storefront/office pin. It misses exactly the
population that matters most here: Argentine Amazon operators are usually
remote-first — exporters, one-person consultancies, "vender en Amazon" trainers,
nearshore agencies selling to the US. Those live in SERPs and directories, not
on a map pin.

~$0.0035 per query. Same live/advanced gotcha as every other DFS script in this
repo: one task per POST, so queries are parallelised as individual requests and
`--retry-empty` re-runs whatever came back throttled.

Output: outreach/ar-sellers/data/ar_serp.jsonl {domain, company, tier, source}
Resumable cache: data/_ar_dfs_serp_progress.json

Usage:
    python3 outreach/ar-sellers/ar2_dfs_serp.py --dry-run
    python3 outreach/ar-sellers/ar2_dfs_serp.py
    python3 outreach/ar-sellers/ar2_dfs_serp.py --retry-empty
"""
import argparse
import base64
import concurrent.futures as cf
import json
import re
import sys
import threading
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "data"
ENV = ROOT / "data_sources" / "config" / ".env"
OUT = DATA / "ar_serp.jsonl"
PROGRESS = DATA / "_ar_dfs_serp_progress.json"

API = "https://api.dataforseo.com/v3"
COST_PER_QUERY = 0.0035
DEPTH = 100

# Tier A — Amazon named explicitly. This is the whole reason the layer exists.
QUERIES_A = [
    "vender en amazon desde argentina",
    "como vender en amazon argentina",
    "agencia amazon argentina",
    "consultoria amazon fba argentina",
    "amazon fba argentina",
    "curso amazon fba argentina",
    "agencia amazon ads argentina",
    "exportar a estados unidos amazon argentina",
    "asesor amazon seller argentina",
    "gestion de cuentas amazon argentina",
    "amazon seller central argentina",
    "vender en amazon usa desde argentina",
    "servicio amazon fba argentina empresa",
    "amazon vendor argentina agencia",
    "publicidad en amazon argentina",
    "consultor ecommerce internacional argentina amazon",
    "marca argentina vende en amazon",
    "pymes argentinas exportan amazon",
    "amazon global selling argentina",
    "empresa argentina amazon marketplace",
    # round 2 (2026-08-12): the Amazon-explicit tier is the best-fit segment and
    # the thinnest, so it gets the widest query net of the three.
    "vender en amazon fba argentina consultoria",
    "agencia de publicidad amazon argentina",
    "especialista amazon ppc argentina",
    "gestion amazon ads argentina empresa",
    "consultor marketplaces internacionales argentina",
    "exportar productos argentinos a amazon estados unidos",
    "empresa argentina exporta amazon usa caso",
    "marca argentina en amazon estados unidos",
    "vender en amazon desde buenos aires",
    "vender en amazon desde cordoba argentina",
    "curso vender en amazon argentina presencial",
    "mentoria amazon fba argentina",
    "agencia ecommerce internacional argentina amazon",
    "logistica para vender en amazon desde argentina",
    "cuenta de amazon seller para argentinos",
    "asesoramiento exportacion ecommerce argentina",
    "consultora comercio exterior ecommerce argentina",
    "argentina amazon fba emprendedores",
    "servicios de listing amazon en espanol argentina",
    "gestion de cuenta amazon para pymes argentinas",
]
# Tier B — agencies/consultancies that run marketplaces or paid media for others.
QUERIES_B = [
    "agencia ecommerce argentina",
    "mejores agencias ecommerce argentina",
    "agencia marketplace argentina",
    "agencia mercado libre argentina",
    "consultora de ecommerce argentina",
    "agencia de performance marketing argentina",
    "agencia de publicidad digital argentina",
    "agencia de marketing digital buenos aires",
    "agencias marketing digital cordoba argentina",
    "agencias marketing digital rosario",
    "agencia tiendanube partner argentina",
    "agencia shopify partner argentina",
    "agencia vtex partner argentina",
    "agencia retail media argentina",
    "consultora comercio electronico argentina",
    "agencia growth marketing argentina",
    "empresa desarrollo ecommerce argentina",
    "agencia digital nearshore argentina estados unidos",
    "agencia de medios digitales argentina",
    "gestion de marketplaces argentina",
    "mejores agencias de marketing digital argentina",
    "agencias de publicidad digital cordoba",
    "agencias digitales mendoza",
    "agencias marketing mar del plata",
    "agencias marketing digital tucuman salta",
    "agencia de medios performance buenos aires",
    "consultora marketing digital pymes argentina",
    "agencia de email marketing argentina",
    "agencia crm y automatizacion argentina",
    "partners tiendanube agencias argentina",
]
# Tier C — Argentine brands/exporters that could be sellers themselves.
QUERIES_C = [
    "empresas argentinas que exportan productos",
    "marcas argentinas venta online internacional",
    "exportadores argentinos productos de consumo",
    "fabricantes argentinos venta mayorista online",
    "empresas argentinas exportacion ecommerce",
    "directorio exportadores argentina",
    "marcas argentinas dtc tienda online",
    "camara argentina de comercio electronico socios",
    "startups ecommerce argentina",
    "empresas argentinas venden en estados unidos online",
]

# Directories, media, SaaS, marketplaces — never a lead.
JUNK = re.compile(
    r"(amazon\.|google\.|facebook|instagram|linkedin|twitter|youtube|tiktok|"
    r"pinterest|reddit|quora|medium\.com|wikipedia|"
    r"mercadolibre|tiendanube|shopify|vtex|woocommerce|wix\.|squarespace|"
    r"jumpseller|bigcommerce|prestashop|magento|"
    r"clutch\.co|sortlist|designrush|goodfirms|semrush|ahrefs|similarweb|"
    r"agencyspotter|expertise\.com|topdigital|superbcompanies|"
    r"infobae|clarin|lanacion|cronista|ambito|perfil\.com|pagina12|"
    r"iproup|iprofesional|forbesargentina|infotechnology|telam|"
    r"gob\.ar|gov\.ar|edu\.ar|\.gob\.|afip\.|inti\.gob|"
    r"computrabajo|indeed|zonajobs|bumeran|glassdoor|"
    r"paginasamarillas|cylex|opendi|infoisinfo|guiaempresas|"
    r"udemy|coursera|hotmart|domestika|crehana|platzi|"
    r"wordpress\.com|blogspot|medium|substack|"
    r"payoneer|paypal|stripe|dhl|fedex|ups\.com|correoargentino|"
    r"helium10|junglescout|sellerapp|perpetua|teikametrics|"
    r"instantly\.ai|apollo\.io|hunter\.io)", re.I)

RE_A = re.compile(r"amazon|\bfba\b", re.I)

_lock = threading.Lock()


def env():
    d = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def auth_header(e):
    tok = base64.b64encode(
        f"{e['DATAFORSEO_LOGIN']}:{e['DATAFORSEO_PASSWORD']}".encode()).decode()
    return "Basic " + tok


def post(endpoint, payload, hdr):
    req = urllib.request.Request(
        API + endpoint, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": hdr, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())


def balance(hdr):
    req = urllib.request.Request(API + "/appendix/user_data",
                                 headers={"Authorization": hdr})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["tasks"][0]["result"][0]["money"]["balance"]


def build_queries():
    return ([{"key": f"A|{q}", "q": q, "tier": "A"} for q in QUERIES_A]
            + [{"key": f"B|{q}", "q": q, "tier": "B"} for q in QUERIES_B]
            + [{"key": f"C|{q}", "q": q, "tier": "C"} for q in QUERIES_C])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    queries = build_queries()
    print(f"plan: {len(queries)} queries x top {DEPTH}, "
          f"est ${len(queries)*COST_PER_QUERY:.2f}")
    if args.dry_run:
        return

    e = env()
    hdr = auth_header(e)
    store = json.loads(PROGRESS.read_text()) if PROGRESS.exists() else {}
    if args.retry_empty:
        for k in [k for k, v in store.items() if not v.get("records")]:
            del store[k]
    todo = [q for q in queries if q["key"] not in store]
    if args.limit:
        todo = todo[: args.limit]

    bal = balance(hdr)
    need = len(todo) * COST_PER_QUERY
    print(f"{len(store)} cached, {len(todo)} to fetch | "
          f"balance ${bal:.2f}, need ~${need:.2f}")
    if need > bal:
        sys.exit(f"insufficient balance: need ${need:.2f}, have ${bal:.2f}")

    done, spent = [0], [0.0]

    def run(s):
        try:
            resp = post("/serp/google/organic/live/advanced", [{
                "keyword": s["q"], "location_name": "Argentina",
                "language_code": "es", "depth": DEPTH}], hdr)
            task = (resp.get("tasks") or [{}])[0]
            res = (task.get("result") or [{}])[0] if task.get("result") else {}
            recs = [{"domain": it.get("domain"), "title": it.get("title"),
                     "url": it.get("url")}
                    for it in (res.get("items") or [])
                    if it.get("type") == "organic" and it.get("domain")]
            cost = resp.get("cost") or 0.0
        except Exception as ex:
            recs, cost = [], 0.0
            print(f"  FAIL [{s['q'][:45]}]: {str(ex)[:60]}")
        with _lock:
            store[s["key"]] = {"tier": s["tier"], "q": s["q"], "records": recs}
            spent[0] += cost
            done[0] += 1
            if done[0] % 10 == 0:
                PROGRESS.write_text(json.dumps(store, ensure_ascii=False))
                print(f"  {done[0]}/{len(todo)} | spent ${spent[0]:.2f}")

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, todo))
    PROGRESS.write_text(json.dumps(store, ensure_ascii=False))

    by_dom = {}
    for v in store.values():
        for r in v["records"]:
            d = (r.get("domain") or "").lower()
            d = d[4:] if d.startswith("www.") else d
            if not d or "." not in d or JUNK.search(d):
                continue
            tier = "A" if (v["tier"] == "A" or RE_A.search(
                f"{r.get('title') or ''} {d}")) else v["tier"]
            prev = by_dom.get(d)
            if prev and prev["tier"] <= tier:
                continue
            by_dom[d] = {"domain": d, "company": (r.get("title") or d)[:80],
                         "tier": tier, "query": v["q"], "source": "serp_dfs"}
    with OUT.open("w", encoding="utf-8") as f:
        for r in by_dom.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tiers = {t: sum(1 for r in by_dom.values() if r["tier"] == t) for t in "ABC"}
    print(f"\n{len(by_dom)} unique domains {tiers} -> {OUT}")
    print(f"run cost ${spent[0]:.2f}")


if __name__ == "__main__":
    main()
