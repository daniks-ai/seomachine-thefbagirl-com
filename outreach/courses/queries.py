#!/usr/bin/env python3
"""
Query plan for the Amazon-course / coaching vertical.

Two families:
  DIRECT   — find the course seller's own site ("amazon fba course", "curso
             amazon fba", "amazon fba coaching") across 20+ languages.
  LISTICLE — find round-up articles ("best amazon fba courses 2026") whose
             outbound links are a curated list of course sellers; those pages
             get crawled by listicle_crawl.py for a second-order domain harvest.

Usage:
    python3 outreach/courses/queries.py --emit direct   > data/q_direct.txt
    python3 outreach/courses/queries.py --emit listicle > data/q_listicle.txt
    python3 outreach/courses/queries.py --chunk 25 --emit direct --json
"""
import argparse
import json

# (market, [queries]) — market is Bing's mkt code, it steers the result set
DIRECT = {
    "en-US": [
        "amazon fba course", "amazon fba coaching program", "amazon fba mentorship",
        "amazon seller training program", "amazon fba academy", "amazon fba bootcamp",
        "amazon fba masterclass", "learn amazon fba online course",
        "amazon wholesale course", "amazon private label course",
        "amazon online arbitrage course", "amazon retail arbitrage training",
        "amazon ppc training course", "amazon seller coach one on one",
        "amazon fba consultant coaching", "amazon fba workshop",
        "amazon selling course for beginners", "amazon brand building course",
        "amazon kdp publishing course", "amazon dropshipping course",
        "amazon seller mentor program", "amazon fba group coaching",
        "amazon fba course with support", "sell on amazon training",
    ],
    "en-GB": [
        "amazon fba course uk", "amazon fba coaching uk", "amazon seller training uk",
        "amazon fba mentorship uk", "amazon fba academy uk",
        "online arbitrage course uk", "amazon wholesale course uk",
    ],
    "en-CA": ["amazon fba course canada", "amazon seller training canada",
              "amazon fba coaching canada"],
    "en-AU": ["amazon fba course australia", "amazon seller training australia",
              "amazon fba coaching australia"],
    "en-IN": ["amazon fba course india", "amazon seller training india",
              "amazon selling course hindi", "amazon fba coaching india"],
    "en-PH": ["amazon fba course philippines", "amazon virtual assistant fba training"],
    "en-AE": ["amazon fba course dubai", "amazon seller training uae"],
    "en-PK": ["amazon fba course pakistan", "amazon fba training institute lahore",
              "amazon course karachi"],
    "en-NG": ["amazon fba course nigeria", "amazon fba training nigeria"],
    "en-ZA": ["amazon fba course south africa"],
    "de-DE": [
        "amazon fba kurs", "amazon fba coaching", "amazon fba mentoring",
        "amazon seller schulung", "amazon fba akademie", "amazon fba seminar",
        "amazon private label kurs", "amazon ppc schulung",
        "amazon fba beratung coaching", "kdp kurs deutsch",
    ],
    "de-AT": ["amazon fba kurs österreich", "amazon fba coaching wien"],
    "de-CH": ["amazon fba kurs schweiz", "amazon fba coaching schweiz"],
    "es-ES": [
        "curso amazon fba", "mentoria amazon fba", "formacion vender en amazon",
        "academia amazon fba", "curso amazon seller central", "asesoria amazon fba",
    ],
    "es-MX": ["curso amazon fba mexico", "mentoria amazon mexico",
              "curso vender en amazon mexico"],
    "es-AR": ["curso amazon fba argentina", "mentoria amazon fba argentina"],
    "es-CO": ["curso amazon fba colombia"],
    "es-CL": ["curso amazon fba chile"],
    "pt-BR": [
        "curso amazon fba", "curso vender na amazon", "mentoria amazon fba",
        "treinamento amazon fba brasil", "consultoria amazon fba curso",
    ],
    "pt-PT": ["curso amazon fba portugal", "formacao vender na amazon"],
    "fr-FR": [
        "formation amazon fba", "coaching amazon fba", "formation vendre sur amazon",
        "accompagnement amazon fba", "formation amazon ppc",
    ],
    "fr-CA": ["formation amazon fba quebec"],
    "it-IT": [
        "corso amazon fba", "formazione amazon fba", "corso vendere su amazon",
        "consulenza amazon fba corso", "academy amazon fba",
    ],
    "nl-NL": ["amazon fba cursus", "verkopen op amazon cursus", "amazon fba coaching nederland"],
    "nl-BE": ["amazon fba cursus belgie"],
    "pl-PL": ["kurs amazon fba", "szkolenie sprzedaz na amazon", "mentoring amazon fba"],
    "tr-TR": ["amazon fba egitimi", "amazon fba kursu", "amazonda satis egitimi",
              "amazon fba danismanlik egitim"],
    "ru-RU": ["курс amazon fba", "обучение амазон", "наставничество амазон",
              "курсы по продажам на амазон"],
    "uk-UA": ["курси amazon fba", "навчання амазон"],
    "ar-SA": ["كورس امازون fba", "دورة البيع على امازون", "تدريب امازون fba"],
    "ar-EG": ["كورس امازون مصر", "دورة امازون fba"],
    "he-IL": ["קורס אמזון fba", "ליווי אמזון fba"],
    "ja-JP": ["amazon 物販 講座", "amazon せどり スクール", "amazon 物販 コンサル",
              "amazon 物販 塾"],
    "ko-KR": ["아마존 셀러 강의", "아마존 fba 강의"],
    "zh-TW": ["亞馬遜 課程", "亞馬遜 電商 培訓"],
    "zh-CN": ["亚马逊运营培训", "亚马逊跨境电商课程"],
    "id-ID": ["kursus amazon fba", "pelatihan jualan di amazon"],
    "vi-VN": ["khoa hoc amazon fba", "dao tao ban hang amazon"],
    "th-TH": ["คอร์ส amazon fba", "สอนขายของ amazon"],
    "sv-SE": ["amazon fba kurs sverige", "salja pa amazon utbildning"],
    "da-DK": ["amazon fba kursus"],
    "nb-NO": ["amazon fba kurs norge"],
    "fi-FI": ["amazon fba kurssi"],
    "cs-CZ": ["kurz amazon fba", "prodej na amazonu skoleni"],
    "sk-SK": ["kurz amazon fba slovensko"],
    "hu-HU": ["amazon fba tanfolyam", "amazon eladas tanfolyam"],
    "ro-RO": ["curs amazon fba", "cursuri vanzare pe amazon"],
    "el-GR": ["σεμιναριο amazon fba", "μαθημα πωλησεις amazon"],
    "bg-BG": ["курс amazon fba"],
    "hr-HR": ["amazon fba kurs hrvatska"],
    "sr-RS": ["amazon fba kurs srbija"],
    "lt-LT": ["amazon fba kursai"],
    "lv-LV": ["amazon fba kursi"],
    "et-EE": ["amazon fba koolitus"],
    "sl-SI": ["amazon fba tecaj"],
    "ms-MY": ["kursus amazon fba malaysia"],
}

LISTICLE = {
    "en-US": [
        "best amazon fba courses", "best amazon fba courses 2026",
        "top amazon fba coaching programs", "amazon fba course reviews",
        "best amazon seller training programs", "amazon fba mentorship reviews",
        "best online arbitrage courses", "best amazon wholesale courses",
        "best amazon ppc courses", "amazon fba coaches list",
        "best amazon kdp courses", "amazon fba course comparison",
        "top amazon consultants and coaches", "best courses for amazon sellers 2026",
    ],
    "en-GB": ["best amazon fba courses uk", "amazon fba coaching uk reviews"],
    "en-IN": ["best amazon fba courses in india", "amazon selling course india reviews"],
    "en-PK": ["best amazon fba institutes in pakistan", "amazon course pakistan reviews"],
    "de-DE": ["beste amazon fba kurse", "amazon fba coaching erfahrungen",
              "amazon fba kurs vergleich", "amazon fba kurse test"],
    "es-ES": ["mejores cursos amazon fba", "cursos amazon fba opiniones"],
    "es-MX": ["mejores cursos amazon fba mexico"],
    "pt-BR": ["melhores cursos amazon fba", "curso amazon fba vale a pena"],
    "fr-FR": ["meilleures formations amazon fba", "formation amazon fba avis"],
    "it-IT": ["migliori corsi amazon fba", "corso amazon fba opinioni"],
    "nl-NL": ["beste amazon fba cursus", "amazon fba cursus ervaringen"],
    "pl-PL": ["najlepsze kursy amazon fba", "kurs amazon fba opinie"],
    "tr-TR": ["en iyi amazon fba egitimleri", "amazon fba egitimi yorumlar"],
    "ru-RU": ["лучшие курсы amazon fba", "курсы амазон отзывы"],
    "ar-SA": ["افضل كورسات امازون fba"],
    "ja-JP": ["amazon 物販 スクール おすすめ", "amazon 物販 塾 比較"],
    "id-ID": ["kursus amazon fba terbaik"],
    "ro-RO": ["cele mai bune cursuri amazon fba"],
    "cs-CZ": ["nejlepsi kurzy amazon fba"],
    "hu-HU": ["legjobb amazon fba tanfolyamok"],
}


def flatten(plan):
    return [(mkt, q) for mkt, qs in plan.items() for q in qs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", choices=["direct", "listicle", "both"], default="direct")
    ap.add_argument("--chunk", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    plan = []
    if args.emit in ("direct", "both"):
        plan += flatten(DIRECT)
    if args.emit in ("listicle", "both"):
        plan += flatten(LISTICLE)

    if args.chunk:
        chunks = [plan[i:i + args.chunk] for i in range(0, len(plan), args.chunk)]
        if args.json:
            print(json.dumps(chunks, ensure_ascii=False))
        else:
            for i, c in enumerate(chunks):
                print(f"--- chunk {i} ({len(c)}) ---")
                for mkt, q in c:
                    print(f"{mkt}\t{q}")
        return
    if args.json:
        print(json.dumps(plan, ensure_ascii=False))
    else:
        for mkt, q in plan:
            print(f"{mkt}\t{q}")


if __name__ == "__main__":
    main()
