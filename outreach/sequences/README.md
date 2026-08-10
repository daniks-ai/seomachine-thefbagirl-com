# Localized outbound sequences — segment → language → files

All sequences are faithful localizations of the live English campaign
`Daniks.AI White Label — PPC Agencies [US]` (pulled verbatim 2026-07-07).
Every version keeps: 5 steps + variant B on step 1 + the "Reply handler"
subsequence, pauses **3 / 4 / 5 / 4** days, Instantly variables
(`{{firstName|…}}`, `{{companyName|…}}`, `{{sendingAccountFirstName}}`),
USD pricing (matches daniks.ai/agency), and the reply-keyword CTAs translated
so recipients reply in their own language.

## Mapping

| Segment CSV (outreach/data/instantly_segments/) | Contacts | Language | Sequence file |
|---|---|---|---|
| instantly_EN-US.csv | 993 | English | (live campaign / `_source_en.md`) |
| instantly_INDIA.csv | 613 | English | `_source_en.md` |
| instantly_EN-UK.csv | 342 | English | `_source_en.md` |
| instantly_EN-INTL.csv | 297 | English | `_source_en.md` |
| instantly_EU-EN.csv | 92 | English | `_source_en.md` |
| instantly_APAC-EN.csv | 74 | English | `_source_en.md` |
| instantly_MENA.csv | 35 | English | `_source_en.md` |
| instantly_DACH.csv | 173 | German | **de.md** |
| instantly_EU-FR.csv | 61 | French | **fr.md** |
| instantly_EU-ES.csv | 63 | Spanish | **es.md** |
| instantly_EU-IT.csv | 33 | Italian | **it.md** |
| instantly_LATAM-ES.csv | 11 | Spanish (MX) | **es.md** |
| instantly_LATAM-PT.csv | 11 | Portuguese (BR) | **pt-br.md** |

> The original `instantly_LATAM.csv` was split by the `language` column into
> `LATAM-ES` (Spanish) and `LATAM-PT` (Portuguese) so each gets the right copy.

## Reply-keyword CTAs per language (what the lead is asked to reply)

| Step | EN | DE | FR | ES | IT | PT-BR |
|---|---|---|---|---|---|---|
| 1 one-pager | send it | Schicken | envoyez | envíelo | invii | envie |
| 1 opt-out | no thanks | kein Interesse | non merci | no, gracias | no grazie | não, obrigado |
| 2 calc | numbers | Zahlen | chiffres | números | numeri | números |
| 3 demo | demo | Demo | démo | demo | demo | demo |
| 4 white-label | (your logo) | (Ihr Logo) | (votre logo) | (su logo) | (il suo logo) | (seu logo) |

## How to launch each non-English segment

1. In Instantly, **duplicate** the live campaign (keeps steps, pauses, schedule, sending accounts).
2. Rename e.g. `Daniks.AI White Label — PPC Agencies [DE]`.
3. Replace each step's Subject + body with the matching language file (use Code View `</>` to avoid the `{{` autocomplete bug noted in memory).
4. Recreate step-1 variant B and the "Reply handler" subsequence in that language.
5. Import the segment CSV into that campaign's Leads.
6. Set the Schedule timezone to the region (DACH/EU = CET, LATAM = local) so sends land in business hours.
7. Keep the same daily cap / warmed sending accounts — "send slowly."

English segments (EN-US/UK/INDIA/INTL/EU-EN/APAC/MENA) need no translation —
they run on the existing English copy.
