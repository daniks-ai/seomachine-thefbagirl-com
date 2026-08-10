# Аудит событий и подготовка к рекламе — 2026-07-06

## Стратегия (утверждена)

Две воронки по типу контента:

| Контент | Читатель | CTA / конверсия |
|---|---|---|
| Образовательный (FBA-обучение, статьи из видео) | Холодный новичок | → YouTube-канал (`youtube_channel_click`, `youtube_video_click`) |
| BOFU про инструменты (vs-статьи, ревью, best-tools) | Тёплый, выбирает PPC-тулзу | → daniks.ai напрямую (`daniks_ai_click`) |

Эмбед видео на сайте НЕ используем (осознанно): превьюшка-ссылка уводит на YouTube —
подписка/комменты/сессии возможны только там, алгоритм YouTube вознаграждает external
session starts. Плеер на сайте дал бы просмотры без роста канала.

## Что сделано (commit 74433b5 в thefbagirl-com, ждёт push)

1. **Consent Mode v2 стал региональным** (`BaseLayout.astro`): denied-по-умолчанию только
   EEA/UK/CH; в остальных странах (US!) granted — иначе конверсии Google Ads моделируются/теряются.
2. **Cookie-баннер авто-показывается только в EEA/UK/CH** (`cookie-consent.ts`, гео через
   Cloudflare `/cdn-cgi/trace`, fallback = показать). Футер-ссылка работает везде.
3. **Карта конверсий `ADS_CONVERSIONS`** в click-листенере BaseLayout:
   - `youtube_channel_click` → `AW-17719040765/SEHHCOfz66QcEP21jIFC` (активна)
   - `youtube_video_click` → пусто, ждёт label из Google Ads UI
   - `daniks_ai_click` → пусто, ждёт label из Google Ads UI
4. **`sub_confirmation=1`** добавляется к ссылкам на канал в момент клика (schema/DOM чистые).

Проверено в браузере на dist-сборке: consent-дефолты (granted + regional denied),
клик на канал (rewrite + GA4 event + Ads conversion), youtube_video_click, daniks_ai_click,
баннер рендерится, консоль чистая. Build: 562 страницы OK.

## GA4 + Google Ads — СДЕЛАНО 2026-07-06 (через браузер, ekaterina@daniks.ai)

GA4 (property TheFBAGirl 534895844, stream G-WF73G7Z289):
- Key events: `youtube_channel_click` ✓, `youtube_video_click` ✓ (был), `daniks_ai_click` ✓ (добавлены).
- `purchase` в key events — системный дефолт GA4, снять нельзя, не срабатывает (безвреден).
- Custom events / Modifications — пусто, мусора нет. Всего собирается 11 событий
  (7 стандартных + contact_form_submit + наши 3; tool_review_cta_click без кликов за 28 дней).

Google Ads (Daniks.AI, 762-666-1929):
- Импортированы GA4 key events как конверсии: «TheFBAGirl (web) daniks_ai_click»
  (Primary, Outbound click) и «TheFBAGirl (web) youtube_video_click» (Secondary, Outbound click).
- `youtube_channel_click` НЕ импортирован — работает нативная gtag-конверсия
  «TheFBAGirl - Subscribe on YouTube» (12 конверсий за 30 дней, Active). Импорт = двойной счёт.
- Удалена мёртвая конверсия «TheFBAGirl - YouTube Video Click» (Website, Inactive,
  тег никогда не был вшит в сайт).
- Код: `ADS_CONVERSIONS` в BaseLayout сокращён до одной channel-конверсии (commit 0eec8f3).

## Закрыто 2026-07-06 (по подтверждению пользователя)

1. ✅ Push twin-репо: 74433b5 + 0eec8f3 в main, деплой Cloudflare Pages запущен.
2. ✅ «Purchase (Go To Amazon)» удалена из Google Ads (был мёртвый account-default goal,
   Needs attention, 0 конверсий — тег никогда не стоял на сайте).

## Осталось

- После деплоя проверить на проде: баннер не показывается вне ЕС, `/cdn-cgi/trace` отвечает,
  канальная конверсия фиксируется в Ads.
- Когда наберётся статистика (2-4 недели) — этап 3: кампании (см. выше).

## Аудит контента (343 статьи)

- 270/343 статей имеют видео-пару (`youtubeVideoId` → превью-ссылка в шапке).
- `ChannelCTA` (подписка на канал) рендерится в КАЖДОЙ статье через PostLayout — покрытие 100%.
- 80 статей ссылаются на daniks.ai.
- 24 образовательных статьи вообще без связи с видео (10 blog, 7 news, 3 lifehacks,
  4 tutorials) — news это нормально (нет видео по теме), остальные — кандидаты на
  подбор видео при следующем проходе.
- Ревью сторонних тулз (helium 10, jungle scout, sellerboard, hellotax, taxdoo) без
  прямой ссылки на daniks.ai — осознанно (аффилиат-ревью), daniks-review линкует
  внутреннюю `/daniks/`, что ок.
- Ложные срабатывания классификатора BOFU: маркетплейс-сравнения (amazon vs noon,
  wildberries vs ozon, fba-vs-fbm) — это образовательный контент, daniks-ссылка там
  не обязательна.

## Этап 3 (кампании) — когда дойдём

- Поиск по образовательным запросам → статья → канал (конверсия: youtube_channel/video_click)
- Прямые видеокампании на подписчиков — бенчмарк цены подписчика
- BOFU-поиск → vs/review статьи → daniks.ai (конверсия: daniks_ai_click)
- Позже ретаргетинг посетителей сайта видеорекламой
