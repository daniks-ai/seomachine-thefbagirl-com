# Source map — Chinese Amazon sellers (lead sources for Daniks.AI PPC)

Задача: карта источников, где реально живут/перечислены китайские Amazon-селлеры,
ранжированная по тому, **насколько близко источник к рабочему бизнес-email**.
Персона отличается от Layer 1-3 (`README.md`, там — PPC-агентства). Здесь —
сами селлеры (бренды private-label из Китая, продающие на Amazon.com).

> Реальность канала: у китайских селлеров email — **вторичный** канал (первичный
> WeChat/QQ). Email-outreach даёт низкий отклик по сравнению с агентствами. Это
> не значит «не делать» — значит держать ожидания и вкладывать в персонализацию
> + мультиязычность (см. раздел «Ограничения» внизу). Если решим, что WeChat
> честнее — переключаемся на путь C из исходного плана.

---

## Tier 1 — готовые контакт-базы (email в комплекте, платно)

Самый быстрый путь к рабочему списку. Отдают Excel/CSV с email-полем.

| Источник | Объём | Поля | Цена | Email? | Ссылка |
|---|---|---|---|---|---|
| **SellerDirectories — China Amazon 3P** | 10 000+ китайских private-label компаний | 16+ датапоинтов: ФИО decision maker, **direct email (name@company.com)**, телефон, юр.название, адрес, сайт, seller ID/URL, список брендов, FBA/FBM split, country | $840/1k · $3 500/5k · $5 900/10k (Excel, 48ч, обновл. ежемесячно) | **Да, direct** | [sellerdirectories.com/china-3p](https://sellerdirectories.com/pages/china-amazon-3p-sellers-database) |
| **SellerDirectories — общая семья баз** | разные срезы Amazon-селлеров | как выше | по запросу | Да | [seller databases](https://sellerdirectories.com/pages/amazon-seller-databases) |
| **BizProspex — Canton Fair Exhibitor List** | экспоненты Canton Fair (производители=часто селлеры) | компания, контакты, категория | ~$1 840 | частично | [bizprospex.com](https://bizprospex.com/product/canton-fair-exhibitor-list/) |

**Оценка:** SellerDirectories China 3P — самый прямой хит под задачу. $840 за 1k
верифицированных direct-email китайских брендов = дешевле, чем строить скрапер
и чистить его вручную. Первый кандидат на пилот-закупку 1k.

---

## Tier 2 — seller-интеллидженс платформы (фильтры + сам добываешь контакт)

Не отдают email напрямую, но дают отфильтровать по «China + FBA + revenue» и
получить seller name / storefront → домен → прогон через ваш Apify
`2b_email_harvest.py` (тот же, что в Layer 2/3).

| Платформа | Что даёт | Фильтр по Китаю | Экспорт | Цена | Ссылка |
|---|---|---|---|---|---|
| **SmartScout** | 1.5M+ селлеров, revenue/category/FBA%/brands/Buy Box, seller map | Да (country/state) | нужно проверить на плане | $25–187/мес (−25% год) | [smartscout.com/seller-data](https://www.smartscout.com/seller-data) |
| **Helium 10 / Jungle Scout** | seller & brand базы, revenue-оценки | частично (по storefront) | ограниченно | подписка | (уже знакомы команде) |
| **Marketplace Pulse** | рейтинги топ-селлеров, страновые срезы, Seller Index 2026 | Да (China-sellers срез) | отчётный, не экспорт лидов | подписка | [marketplacepulse.com/amazon/china-sellers](https://www.marketplacepulse.com/amazon/china-sellers) |

**Схема добычи из Tier 2:** фильтр `China + FBA% high + revenue band` → экспорт/скрейп
seller-name+storefront → достаём домен бренда → `2b_email_harvest.py --domains-file`
(бесплатный Apify contact-scraper, уже в пайплайне) → нормализация → Instantly CSV.

---

## Tier 3 — сообщества и площадки (не email-лист, а точки входа)

Здесь селлеры «живут». Email отсюда не выгрузить, но это каналы прогрева,
инвайтов и ручного нетворка. Для email-first это supplement, для WeChat-пути —
основа.

- **WeChat-группы** (cross-border / Amazon FBA / factory-trade) — вход по инвайту;
  через Global From Anywhere/Asia сообщество: [globalfromanywhere.com/wechat-fba](https://www.globalfromasia.com/wechat-fba/)
- **Facebook «amazon sellers from China»** — [fb.com/groups/amazonchinasellers](https://www.facebook.com/groups/amazonchinasellers/) (можно найти живых селлеров, попросить инвайт в WeChat-群)
- **知无不言 (zhiwubuyan)** — крупнейший китайский форум Amazon-селлеров (深圳-центричный)
- **Cross Border Summit / Cross Border Matchmaker** (Global From Anywhere), очный нетворк, событие 3–5 ноя 2026 — [globalfromanywhere.com/top-chinese-amazon-fba-sellers](https://globalfromanywhere.com/top-chinese-amazon-fba-sellers/)

---

## Tier 4 — первичные директории (сырьё под свой скрейп)

Списки компаний без готовых email — база для enrichment через ваш пайплайн.

- **Canton Fair официальный exhibitor directory** — фильтр по категории/компании/стенду, ~25–32k экспонентов/сессия, есть cross-border e-commerce секция с Amazon/Alibaba: [cantonfair.org.cn exhibitors](https://activity.cantonfair.org.cn/en/SelectedExhibitors/company.html)
- **Global Sources** — экспоненты/поставщики, многие D2C на Amazon
- **Alibaba / 1688 storefronts** — часть указывает WeChat/email напрямую
- **Made-in-China.com** — производители, пересечение с Amazon-селлерами

Named-примеры топ-китайских Amazon-native брендов (для seed-списка / lookalike):
Anker, Aukey, Mpow, SKG, Ausdom, StarMerx, OPOWER — как отправная точка для
поиска соседних брендов через SmartScout «brands by same seller».

---

## География (куда целить фильтры)

Из анализа Marketplace Pulse (250k+ китайских селлеров):
- **Guangdong 40.3%** (из них **Shenzhen 31.8%** всех китайских селлеров — столица Amazon-селлеров мира)
- Shanxi 9.6% · Zhejiang 6.8% · Fujian 6.2%

→ При гео-фильтрах и локализации первого касания приоритет **Shenzhen/Guangdong**.

Источники по гео: [Marketplace Pulse — Shenzhen](https://www.marketplacepulse.com/articles/shenzhen-the-capital-of-amazon-sellers) · [China sellers majority](https://www.marketplacepulse.com/articles/chinese-sellers-outnumber-us-sellers-on-amazoncom)

---

## Ограничения и compliance (держать в голове)

1. **Amazon ToS**: скрейп самого Amazon (storefront-парсинг) нарушает ToS и даёт
   грязь. Поэтому Tier 1 (готовые базы) и Tier 2 (интеллидженс-платформы) > прямой
   скрейп Amazon.
2. **Email в Китае — вторичный канал.** Ожидаемый reply-rate ниже, чем по
   агентствам. Персонализация + китайская локализация первого касания критичны.
3. **Deliverability**: китайские домены/gmail-помойки бьют по репутации отправителя.
   Прогонять через bounce-checker до заливки в Instantly; слать медленно с
   прогретых ящиков (та же дисциплина, что в основном пайплайне).
4. **PIPL/GDPR**: B2B-контакты компаний — ок при opt-out и релевантности; держим
   suppress-лист и честный unsubscribe.

---

## Рекомендованный next step (пилот, минимальный бюджет)

1. **Купить 1k SellerDirectories China 3P** ($840) — сразу direct-email лист с
   16 полями, обновляемый.
2. Прогнать через **существующий `3_build_instantly_csv.py`** (маппинг полей →
   Instantly CSV), добавить в suppress-дисциплину.
3. Собрать **отдельную китайско-адаптированную последовательность** в `sequences/`
   (не переиспользовать агентский копирайт — другая персона, другой язык боли).
4. Слать медленно, мерить reply-rate. Если <0.5% — переключаться на WeChat-путь (C).

Параллельно (бесплатно): взять seed-бренды из Tier 4, прогнать через SmartScout
«same-seller brands» → домены → `2b_email_harvest.py`, сравнить качество с
покупной базой перед масштабированием закупки до 5k/10k.
