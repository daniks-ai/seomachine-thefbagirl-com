#!/usr/bin/env python3
"""
Turn the two markdown sequences into the exact `sequences` JSON that Instantly's
API expects, so the campaigns are created through `POST /api/v2/campaigns`
instead of the web editor.

The editor is avoided on purpose: typing `{{` in it fires a variable
autocomplete that swallows the variable (that is why the MX and UK campaigns
ended up with literal "equipo"/"your brand" instead of merge tags). Pushing the
JSON keeps `{{firstName|…}}` fallbacks intact.

Shape, mirrored from the live UK campaign:
    [{"steps": [{"type":"email","delay":N,
                 "variants":[{"subject":S,"body":HTML}]}, …]}]
An empty subject means "reply in the same thread".

Output: data/sequence_AR_SELLERS.json, data/sequence_AR_AGENCIES.json

Usage:
    python3 outreach/ar-sellers/ar6_build_sequences.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

# (markdown file, output file, [(step-heading regex, delay, new-subject?), …])
SPECS = [
    (HERE / "sequence-sellers-ar.md", DATA / "sequence_AR_SELLERS.json"),
    (HERE / "sequence-agencias-ar.md", DATA / "sequence_AR_AGENCIES.json"),
]

# delay = days to wait AFTER this step. Last step's delay is unused.
DELAYS = [3, 4, 5, 4, 1]


BULLET = re.compile(r"^[—\-•]|^\d+[.)]\s")


def to_html(lines):
    """Plain paragraphs -> the <div>/<div><br /></div> markup Instantly stores.

    Two things the naive version got wrong and that show up in the delivered
    mail: markdown `**bold**` shipped as literal asterisks, and every line got a
    blank line after it — which blows a tight 4-item bullet list into a page of
    scattered dashes. Consecutive bullets are kept adjacent; only real
    paragraph breaks get the spacer div.
    """
    out = []
    for i, ln in enumerate(lines):
        esc = (ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        esc = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc)
        if i and not (BULLET.match(ln) and BULLET.match(lines[i - 1])):
            out.append("<div><br /></div>")
        out.append("<div>" + esc + "</div>")
    return "".join(out)


def parse(md_path):
    """Return [(subject_or_None, body_lines), …] for steps 1..5 (+variant B)."""
    text = md_path.read_text(encoding="utf-8")
    # everything before the reply-handler subsection is the sequence proper
    text = text.split("## Subsecuencia")[0]
    blocks = re.split(r"^## ", text, flags=re.M)[1:]

    parsed = []
    for b in blocks:
        head, *rest = b.split("\n")
        body = "\n".join(rest)
        subject = None
        m = re.search(r"^\*\*Asunto:\*\*\s*(.+)$", body, re.M)
        if m:
            subject = m.group(1).strip()
            body = body[: m.start()] + body[m.end():]
        lines = [l.strip() for l in body.split("\n")
                 if l.strip() and not l.strip().startswith(("---", ">", "**Asunto"))]
        if not lines:
            continue
        parsed.append({"head": head.strip(), "subject": subject, "lines": lines})
    return parsed


def build(md_path):
    parsed = parse(md_path)
    by_head = {p["head"]: p for p in parsed}

    var_a = next(p for p in parsed if p["head"].startswith("Paso 1 — Variante A"))
    var_b = next(p for p in parsed if p["head"].startswith("Paso 1 — Variante B"))
    later = [p for p in parsed if re.match(r"Paso [2-5]", p["head"])]
    later.sort(key=lambda p: int(re.match(r"Paso (\d)", p["head"]).group(1)))
    assert len(later) == 4, f"expected steps 2-5, got {[p['head'] for p in later]}"

    steps = [{
        "type": "email", "delay": DELAYS[0],
        "variants": [{"subject": var_a["subject"], "body": to_html(var_a["lines"])},
                     {"subject": var_b["subject"], "body": to_html(var_b["lines"])}],
    }]
    for i, p in enumerate(later):
        steps.append({
            "type": "email", "delay": DELAYS[i + 1],
            "variants": [{"subject": p["subject"] or "",
                          "body": to_html(p["lines"])}],
        })
    return [{"steps": steps}], by_head


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for md, out in SPECS:
        seq, _ = build(md)
        out.write_text(json.dumps(seq, ensure_ascii=False), encoding="utf-8")
        steps = seq[0]["steps"]
        print(f"{md.name}: {len(steps)} steps "
              f"(variants {[len(s['variants']) for s in steps]}, "
              f"delays {[s['delay'] for s in steps]}) -> {out.name}")
        for s in steps:
            print(f"   d{s['delay']:>2} | {s['variants'][0]['subject'] or '(same thread)'}")


if __name__ == "__main__":
    main()
