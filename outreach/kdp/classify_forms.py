#!/usr/bin/env python3
"""
Classify the contact forms found by harvest_deep.py so we only hand-fill the
ones a human actually can: no captcha, no login, real input fields.

Reads  data/kdp_contacts_deep.json  (needs `hasForm` + `scrapedUrls`)
Writes data/form_targets.json — one record per domain:
    {domain, url, captcha, platform, fields, requiresPhone, verdict}

verdict: "fillable" | "captcha" | "no-form" | "unreachable"
"""
import concurrent.futures as cf
import gzip
import json
import re
import ssl
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
DEEP = DATA / "kdp_contacts_deep.json"
OUT = DATA / "form_targets.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CAPTCHA_RE = re.compile(
    r"(g-recaptcha|grecaptcha|recaptcha/api|www\.google\.com/recaptcha|"
    r"hcaptcha|h-captcha|cf-turnstile|challenges\.cloudflare\.com/turnstile|"
    r"friendlycaptcha|arkoselabs|funcaptcha)", re.I)
# platforms whose forms are iframed/JS-only — a plain fill won't work reliably
IFRAME_FORM_RE = re.compile(r"(typeform\.com|jotform\.com|hsforms\.net|hs-scripts|"
                            r"calendly\.com|tally\.so|airtable\.com/embed)", re.I)
PLATFORM_RE = [
    ("contact-form-7", re.compile(r"wpcf7", re.I)),
    ("gravity-forms", re.compile(r"gform_|gravity_form", re.I)),
    ("wpforms", re.compile(r"wpforms", re.I)),
    ("ninja-forms", re.compile(r"ninja[-_]?forms", re.I)),
    ("formidable", re.compile(r"frm_forms|formidable", re.I)),
    ("elementor", re.compile(r"elementor-form", re.I)),
    ("squarespace", re.compile(r"sqs-block-form|squarespace", re.I)),
    ("wix", re.compile(r"wix-form|wixsite|_wixCssImports", re.I)),
    ("shopify", re.compile(r"contact_form|shopify", re.I)),
    ("hubspot", re.compile(r"hsforms|hbspt", re.I)),
    ("typeform", re.compile(r"typeform", re.I)),
    ("jotform", re.compile(r"jotform", re.I)),
]
FIELD_RE = re.compile(
    r'<(input|textarea|select)\b[^>]*?(?:name|id)=["\']([^"\']+)["\'][^>]*>', re.I)
TYPE_RE = re.compile(r'type=["\']([^"\']+)["\']', re.I)
REQUIRED_RE = re.compile(r"\brequired\b", re.I)
PHONE_RE = re.compile(r"(phone|tel|mobile)", re.I)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html",
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(2_000_000)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        return raw.decode("utf-8", "replace"), r.geturl()


def pick_contact_url(rec):
    """Prefer an explicit contact page over the homepage."""
    urls = rec.get("scrapedUrls") or []
    for u in urls:
        if re.search(r"(contact|get-in-touch|connect|enquir|inquir|work-with|submit)", u, re.I):
            return u
    return urls[0] if urls else "https://" + rec["domain"]


def classify(rec):
    out = {"domain": rec["domain"], "url": pick_contact_url(rec),
           "captcha": False, "platform": "", "fields": [],
           "requiresPhone": False, "verdict": "no-form"}
    try:
        html, final = fetch(out["url"])
        out["url"] = final
    except Exception as e:
        out["verdict"] = "unreachable"
        out["error"] = str(e)[:60]
        return out

    if CAPTCHA_RE.search(html):
        out["captcha"] = True
    for name, rx in PLATFORM_RE:
        if rx.search(html):
            out["platform"] = name
            break
    if IFRAME_FORM_RE.search(html) and out["platform"] in ("", "typeform", "jotform", "hubspot"):
        out["platform"] = out["platform"] or "embedded"

    forms = re.findall(r"<form\b.*?</form>", html, re.S | re.I)
    blob = "\n".join(forms) if forms else ""
    seen = set()
    for tag, nm in FIELD_RE.findall(blob):
        t = (TYPE_RE.search(tag) or [None, ""])[1] if False else ""
        if nm.lower() in seen or nm.startswith(("_", "wpcf7")):
            continue
        seen.add(nm.lower())
        out["fields"].append(nm)
    if any(PHONE_RE.search(f) for f in out["fields"]):
        out["requiresPhone"] = True

    has_email_input = bool(re.search(r'type=["\']email["\']', blob, re.I)) or \
        any(re.search(r"e-?mail", f, re.I) for f in out["fields"])
    has_msg = any(re.search(r"(message|comment|body|enquir|inquir|detail|project)", f, re.I)
                  for f in out["fields"]) or "<textarea" in blob.lower()

    if out["captcha"]:
        out["verdict"] = "captcha"
    elif forms and has_email_input and has_msg:
        out["verdict"] = "fillable"
    elif forms:
        out["verdict"] = "form-unclear"
    return out


def main():
    recs = [r for r in json.loads(DEEP.read_text()) if r.get("hasForm")]
    print(f"classifying {len(recs)} domains with a form")
    res = []
    with cf.ThreadPoolExecutor(max_workers=20) as ex:
        for r in ex.map(classify, recs):
            res.append(r)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    from collections import Counter
    c = Counter(r["verdict"] for r in res)
    print(dict(c))
    print(f"wrote {OUT}")
    for r in sorted(res, key=lambda x: x["domain"]):
        if r["verdict"] == "fillable":
            print(f"  FILLABLE {r['domain']:38} {r['platform'] or '-':16} "
                  f"{'PHONE' if r['requiresPhone'] else ''} {r['url'][:60]}")


if __name__ == "__main__":
    main()
