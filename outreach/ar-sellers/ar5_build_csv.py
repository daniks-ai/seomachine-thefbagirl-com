#!/usr/bin/env python3
"""
Argentina lead engine, step 5: harvested pages -> Instantly-ready CSVs.

Two segments come out, because one sequence cannot serve both:

  AR-AGENCIES  agencies, consultancies, marketplace/performance shops
               -> partner offer (25% lifetime / white-label)
  AR-SELLERS   brands, importers, exporters, online retailers
               -> product offer (free 2-week A/B trial, from $49/mo)

Everything below the harvest is defensive, because these mailboxes are shared
with every other live campaign and one spam complaint hurts all of them:
  * geo gate — a domain must have passed ar4_geo_check (or be a .ar TLD);
  * role/junk gate — hr@, prensa@, no-reply@, Sentry/Wix/placeholder addresses,
    and the `%20`-prefixed artifacts the harvester picks out of URL-encoded hrefs;
  * fake-name gate — "Hola", "Contacto", "Ventas" are greetings the harvester
    mistakes for people; blanking them makes {{firstName}} fall back cleanly;
  * off-domain gate — an address is kept only if it is on the site's own domain
    or on a consumer provider (AR SMBs really do run on gmail); anything on a
    *third* company's domain is someone else's address, not a lead;
  * 2 addresses per domain max;
  * email-level dedupe against every CSV ever imported into the workspace.

Usage:
    python3 outreach/ar-sellers/ar5_build_csv.py
    python3 outreach/ar-sellers/ar5_build_csv.py --max-per-domain 1
"""
import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SHARED = HERE.parents[0] / "data"

LEADS = DATA / "ar_leads.jsonl"
GEO = DATA / "ar_geo.json"
# Our own harvest cache first (ar_harvest.py keeps it private so parallel
# verticals can't clobber it), then the shared one as a fallback — some AR
# domains were already fetched by an earlier vertical and need no refetch.
HARVEST = DATA / "_harvest_progress.json"
HARVEST_SHARED = SHARED / "_harvest_progress.json"
OUT_AG = DATA / "instantly_AR_AGENCIES.csv"
OUT_SE = DATA / "instantly_AR_SELLERS.csv"
OUT_BULK_AG = DATA / "instantly_AR_AGENCIES_bulk.txt"
OUT_BULK_SE = DATA / "instantly_AR_SELLERS_bulk.txt"

FREE_MX = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.ar",
           "live.com", "live.com.ar", "hotmail.com.ar", "icloud.com",
           "protonmail.com", "fibertel.com.ar", "speedy.com.ar"}

BAD_LOCAL = re.compile(
    r"^(no-?reply|noreply|postmaster|mailer-daemon|bounce|abuse|hostmaster|"
    r"dns-admin|webmaster|privacy|privacidad|legal|dmca|copyright|spam|"
    r"unsubscribe|baja|"
    r"careers?|jobs?|empleo|empleos|rrhh|rh|hr|cv|curriculum|postulaciones|"
    r"prensa|press|media|marketing@?$|"
    r"facturacion|facturas|cobranzas|pagos|proveedores|compras|admin|"
    r"soporte-?tecnico|helpdesk|"
    r"you|your|yourname|nombre|correo|email|mail|tuemail|test|demo|ejemplo|"
    r"example|user|username|usuario|sample|sentry|wordpress|wix)$", re.I)

BAD_HOST = re.compile(
    r"(sentry\.io|wixpress|wix\.com|squarespace|godaddy|shopify\.com|"
    r"example\.(com|org)|domain\.com|tudominio|tuempresa|tusitio|"
    r"email\.com|correo\.com|sitio\.com|empresa\.com|"
    r"\.png|\.jpg|\.jpeg|\.gif|\.svg|\.webp|\.css|\.js)$", re.I)

# harvester artifacts: "%20info", "3ainfo" (from %3A), leading punctuation, and
# — the one that got through the first build — a phone number run straight into
# the address because the page had no separator between them
# (shape: "1121480583info@example.com.ar" — phone, then the real local part).
ARTIFACT = re.compile(
    r"^([0-9a-f]{2})?(%[0-9a-f]{2})+|^[^a-z0-9]+|^\d{3,}(?=[a-z])", re.I)

# greeting words the harvester turns into "first names"
FAKE_NAME = {
    "hola", "info", "contacto", "contact", "ventas", "sales", "consultas",
    "administracion", "ar", "arg", "argentina", "hello", "hi", "team",
    "equipo", "comercial", "atencion", "clientes", "soporte", "support",
    "servicio", "web", "digital", "agencia", "estudio", "empresa", "tienda",
    "shop", "online", "mail", "correo", "general", "office", "oficina",
    "consulta", "presupuesto", "cotizacion", "pedidos", "mayorista",
    "distribuidora", "gerencia", "direccion", "recepcion", "escribinos",
    "escribenos", "contactanos", "contactenos", "hablemos", "trabajemos",
}

# A cold email that opens "Hola Msanchez" is worse than one that opens "Hola
# equipo" — a mangled name reads as a broken mail-merge and kills the whole
# pitch. So a local part only becomes {{firstName}} if its first token is an
# actual given name. Everything else falls back to the neutral greeting.
FIRST_NAMES = set("""
adrian agustin agustina alan alberto alejandra alejandro alexis alfredo alicia
ana analia andrea andres angel angeles anibal antonella antonio ariel arturo
augusto aurora axel barbara belen benjamin bernardo betina brenda brian bruno
camila carla carlos carolina catalina cecilia celeste cesar cintia claudia
claudio clara constanza cristian cristina cynthia damian daniel daniela dante
dario david debora diana diego dolores domingo eduardo elena eliana elias
emanuel emilia emiliano emilio enrique erica ernesto esteban estefania eugenia
eugenio eva ezequiel fabian fabiana fabricio facundo federico felipe fernanda
fernando flavia florencia franco francisco gabriel gabriela gaston geronimo
german gimena gisela gladys gonzalo graciela gregorio guadalupe guillermina
guillermo gustavo hector hernan hilda horacio hugo ian ignacio ines ivan
jamil javier jazmin jeronimo jesica jesus joaquin jonathan jorge jose josefina
juan julian juliana julieta julio karina laura lautaro leandro leonardo
leonel lorena lorenzo lucas lucia luciana luciano lucila luis luisa magali
magdalena maia maira malena manuel mara marcela marcelo marcos margarita maria
mariana mariano maricel marina mario marisa marta martin martina mateo matias
mauricio mauro maximiliano melina mercedes micaela miguel milagros mirta
monica nadia nahuel nancy natalia nazareno nelson nestor nicolas noelia norma
octavio olga oscar osvaldo pablo paola patricia patricio paula pedro pilar
rafael ramiro ramon raul rebeca renata ricardo roberto rocio rodolfo rodrigo
rolando romina roxana ruben rufina ruth sabrina salvador samuel sandra santiago
santino sara sebastian sergio silvana silvia simon sofia sol solange soledad
sonia stella susana tamara tatiana teresa thiago tomas ulises valentin valentina
valeria vanesa vanina veronica vicente victor victoria vilma virginia walter
wanda ximena yamila yanina yesica zoe
alex andy ana-maria ann anna beatriz caro chris cristobal dan dani dave ed
elisa emma erik esther eva felix flor gaby gian hernando isabel jack james
jean joe john jonas jose-luis josh juan-pablo katia kevin laura-ines lea leo
lisa lucas-martin luz manu mari marie mark mati max maxi mia mike nacho nico
nina noel pat paul pia pia-maria rita rob sam sandy santi seba sofi steve
susan sue tom tony vale vero vicky will
""".split())

AGENCY_RE = re.compile(
    r"(agenc|consultor|consultora|estudio|marketing|publicidad|digital|"
    r"performance|media|seo|ads|growth|partner|marketplace|ecommerce|"
    r"e-commerce|comercio electr|software|desarrollo|web|studio|lab)", re.I)

# "Agencia" in Spanish also means estate agent, travel agent and insurance
# broker — the Maps tier-B sweep drags all three in. None of them will ever
# have an Amazon client, so they are dropped outright rather than mis-segmented.
IRRELEVANT = re.compile(
    r"(inmobiliar|propiedades|bienes ra[ií]ces|alquiler|"
    r"seguros|aseguradora|broker de seguros|"
    r"viajes|turismo|tour|hoteler|"
    r"automotor|concesionaria|reparaci[oó]n|taller mec|"
    r"abogad|jur[ií]dic|escriban[ií]a|notari|"
    r"contable|contador|estudio cont|impuest|"
    r"odontolog|dental|m[eé]dic|cl[ií]nica|salud|est[eé]tica|spa\b|"
    r"gimnasio|fitness|"
    r"funerar|cementerio|"
    r"empleo|recursos humanos|selecci[oó]n de personal|consultora de rrhh|"
    r"seguridad privada|vigilanc|limpieza|"
    r"colegio|escuela|instituto educativo|universidad|jard[ií]n de infantes|"
    r"iglesia|municipalidad|sindicato)", re.I)

MASTER_GLOBS = ["instantly_*.csv", "instantly_segments*/*.csv"]

FIELDS = ["email", "first_name", "last_name", "company_name", "website",
          "city", "tier", "segment", "source"]


# --- company-name hygiene ------------------------------------------------
# Maps and SERP titles carry SEO taglines ("sitefy - Desarrollo Web",
# "Diseno Web Argentina - Webcrea"). Left alone they render as
# "Comision recurrente en dolares para sitefy - Desarrollo Web", so the
# tagline half is dropped and the half holding the brand is kept.
#
# ALLCAPS is deliberately NOT title-cased: it wrecks initialisms
# ("H&FV" -> "H&fv", "GR" -> "Gr"), and shouty-but-correct beats wrong.
GENERIC_TOKENS = set("""
agencia agencias publicidad marketing desarrollo diseno consultora consultoria
estudio servicio servicios soluciones solucion tienda tiendas empresa productora
comunicacion software sistemas web webs ecommerce comercio digital digitales
creacion pagina paginas online profesional profesionales integral integrales
creativa creativo grafico grafica publicitaria publicitario electronico internet
sitio sitios express company agency studio design designs
""".split())
# connectors and place names carry no brand signal either
FILLER_TOKENS = set("""
de del la el los las y e en para con a al por argentina arg buenos aires caba
cordoba rosario mendoza santa fe plata tucuman salta zona sur norte oeste este
centro
""".split())
TAGLINE_SEP = re.compile(r"\s+(?:[|\u00b7\u2022\u2016\u2013\u2014]|-)\s+")


def _tok(w):
    w = unicodedata.normalize("NFD", w.lower().strip(".,()"))
    return "".join(c for c in w if not unicodedata.combining(c))


def _pure_descriptor(s):
    """True when every token is a category word, connector or place name — i.e.
    the half carries no brand at all. 'Agencia Interactua' is NOT pure, so it
    survives; 'Diseno Web Argentina' is, so the brand must be the other half."""
    toks = [t for t in (_tok(x) for x in s.split()) if t]
    real = [t for t in toks if t not in FILLER_TOKENS]
    if not real:
        return True
    return all(t in GENERIC_TOKENS for t in real)


def tidy_company(name):
    """Reduce a SERP/Maps title to the brand, or to nothing.

    Returning "" is a feature: the sequences fall back to "tu agencia" / "la
    marca", which reads far better in a subject line than a truncated SEO
    title ("Agencia de Diseno web Argentina | Paginas Web en Buenos ...").
    """
    name = (name or "").strip()
    if name.endswith(("...", "\u2026")):        # truncated title, never a name
        return ""
    parts = [p.strip() for p in TAGLINE_SEP.split(name) if p.strip()]
    if len(parts) < 2:
        # A separator-less name is kept even when every token is a category
        # word: "Agencia Digital Sur" and "Cordoba Soluciones Digitales" are
        # real Argentine brands, and blanking them loses good personalisation
        # to catch a handful of SEO titles. Only the two unambiguous shapes
        # above and below are dropped.
        return name
    # the brand is not always the first or second half —
    # "Diseno Web - Desarrollo de Paginas Web - Nubelab" hides it third
    for part in parts:
        if len(part) >= 3 and not _pure_descriptor(part):
            return part
    return ""



def known_emails():
    seen = set()
    files = []
    for g in MASTER_GLOBS:
        files += list(SHARED.glob(g))
    # NOT our own output — this script is re-run repeatedly while the harvest
    # is still filling, and deduping against the previous run would empty it.
    # Cross-round dedupe happens against data/ar_imported_emails.txt, written
    # only after an address is actually pushed into Instantly.
    imported = DATA / "ar_imported_emails.txt"
    if imported.exists():
        seen |= {e.strip().lower() for e in imported.read_text().split() if "@" in e}
    for f in files:
        try:
            with f.open(newline="", encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    for k in ("email", "Email", "EMAIL"):
                        v = (row.get(k) or "").strip().lower()
                        if "@" in v:
                            seen.add(v)
        except Exception:
            pass
    return seen


def root(host):
    """Registrable root, ccSLD-aware (.com.ar, .co.uk, …)."""
    parts = host.lower().split(".")
    if len(parts) >= 3 and parts[-2] in {"com", "co", "net", "org", "gob", "edu"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def clean(email, domain):
    e = email.strip().lower().strip(".,;:<>()[]\"'")
    e = ARTIFACT.sub("", e)
    if e.count("@") != 1 or len(e) > 80 or len(e) < 6:
        return None
    local, host = e.split("@")
    if not local or "." not in host:
        return None
    if BAD_LOCAL.match(local) or BAD_HOST.search(host):
        return None
    if not re.fullmatch(r"[a-z0-9._%+\-]+", local):
        return None
    if host not in FREE_MX and root(host) != root(domain):
        return None                      # someone else's company address
    return e


def person_name(local):
    """Return (first, last) if the local part plausibly names a human."""
    if any(ch.isdigit() for ch in local):
        return "", ""
    parts = [p for p in re.split(r"[._\-]", local) if p]
    if not parts:
        return "", ""
    first = parts[0].lower()
    # whitelist-only: "msanchez" / "jperez" / "ventas" must NOT become a name
    if first not in FIRST_NAMES or first in FAKE_NAME:
        return "", ""
    last = parts[1] if len(parts) > 1 and 2 < len(parts[1]) <= 16 else ""
    if last.lower() in FAKE_NAME or any(ch.isdigit() for ch in last):
        last = ""
    return first.capitalize(), last.capitalize()


def rank(email):
    """Lower is better: named humans first, then the main shared inbox."""
    local = email.split("@")[0]
    if person_name(local)[0]:
        return 0
    order = ["info", "contacto", "hola", "ventas", "comercial", "consultas",
             "hello", "contact", "sales"]
    for i, p in enumerate(order):
        if local.startswith(p):
            return 1 + i
    return 20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-domain", type=int, default=2)
    args = ap.parse_args()

    leads = {r["domain"]: r for r in
             (json.loads(l) for l in LEADS.read_text().splitlines() if l.strip())}
    geo = json.loads(GEO.read_text()) if GEO.exists() else {}
    harvest = json.loads(HARVEST_SHARED.read_text()) if HARVEST_SHARED.exists() else {}
    if HARVEST.exists():
        harvest.update(json.loads(HARVEST.read_text()))
    dedupe = known_emails()
    print(f"{len(leads)} leads | geo {len(geo)} | harvest cache {len(harvest)} "
          f"| dedupe set {len(dedupe)}")

    stats = {"no_harvest": 0, "no_email": 0, "not_ar": 0, "junk": 0,
             "dup": 0, "capped": 0, "off_niche": 0}
    rows_ag, rows_se = [], []

    for domain, lead in leads.items():
        g = geo.get(domain)
        if not (g and g["ar"]):
            stats["not_ar"] += 1
            continue
        h = harvest.get(domain)
        if not h:
            stats["no_harvest"] += 1
            continue
        raw = h.get("emails") or []
        if not raw:
            stats["no_email"] += 1
            continue

        good = []
        for e in raw:
            c = clean(e, domain)
            if not c:
                stats["junk"] += 1
                continue
            if c in dedupe:
                stats["dup"] += 1
                continue
            good.append(c)
        good = sorted(dict.fromkeys(good), key=rank)
        if len(good) > args.max_per_domain:
            stats["capped"] += len(good) - args.max_per_domain
            good = good[: args.max_per_domain]
        if not good:
            continue

        blob = f"{lead.get('company','')} {lead.get('category','')} {domain}"
        if IRRELEVANT.search(blob):
            stats["off_niche"] += 1
            continue
        segment = "AR-AGENCIES" if (
            lead["tier"] in ("A", "B") and AGENCY_RE.search(blob)) else "AR-SELLERS"
        company = tidy_company((lead.get("company") or ""))[:60]

        for e in good:
            dedupe.add(e)
            first, last = person_name(e.split("@")[0])
            row = {"email": e, "first_name": first, "last_name": last,
                   "company_name": company, "website": f"https://{domain}",
                   "city": lead.get("city", ""), "tier": lead["tier"],
                   "segment": segment,
                   "source": ",".join(lead.get("sources") or [])}
            (rows_ag if segment == "AR-AGENCIES" else rows_se).append(row)

    for path, rows in ((OUT_AG, rows_ag), (OUT_SE, rows_se)):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    # Instantly's "Enter Emails Manually" box accepts either a bare address or
    # `"Full Name" <address>`; the named form is what fills {{firstName}}.
    def bulk_line(r):
        name = " ".join(x for x in (r["first_name"], r["last_name"]) if x)
        return f'"{name}" <{r["email"]}>' if name else r["email"]

    for path, rows in ((OUT_BULK_AG, rows_ag), (OUT_BULK_SE, rows_se)):
        path.write_text("\n".join(bulk_line(r) for r in rows) + "\n",
                        encoding="utf-8")

    print(f"\nAR-AGENCIES {len(rows_ag)} rows "
          f"({len({r['website'] for r in rows_ag})} domains) -> {OUT_AG.name}")
    print(f"AR-SELLERS  {len(rows_se)} rows "
          f"({len({r['website'] for r in rows_se})} domains) -> {OUT_SE.name}")
    print(f"named contacts: {sum(1 for r in rows_ag+rows_se if r['first_name'])}")
    print("dropped:", stats)


if __name__ == "__main__":
    main()
