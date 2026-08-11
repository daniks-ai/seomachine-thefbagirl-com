/* Amazon.co.uk GB-seller collector — BOUNDED single-burst worker.
 * Inject this whole file into the in-app Browser pane (tab on
 * https://amazon.co.uk) via the Claude Browser javascript_tool, then:
 *   1) (optional) seed already-seen seller IDs:  window.__seedSeen(["A1..","A2.."])
 *   2) start:                                    window.__ukStart()
 *   3) poll until done:                          window.__ukStatus()  // {finished:true,...}
 *   4) collect results:                          window.__ukDrain()   // {uk:[...], seen:[...]}
 *
 * Bounded so it stops BEFORE Amazon hard-throttles the IP:
 *   stops after MAX_NEW_UK new GB sellers, or MAX_CAP captcha hits, or MAX_MS ms.
 * Gentle ~2.5s/request pacing. Single foreground tab only (Chrome throttles
 * background tabs). Seller profile fetch REQUIRES the Accept:text/html header or
 * /sp returns a tiny JSON stub. Seller page: "Business Name:" + "Business
 * Address:" block; last address line = ISO country code — keep GB.
 */
(function () {
  const MAX_NEW_UK = 40;      // stop after this many fresh GB sellers
  const MAX_CAP = 4;          // stop after this many captcha/503 hits (IP heating up)
  const MAX_MS = 25 * 60 * 1000; // hard time cap
  const HDRS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.9'
  };
  const CATS = [
    "/gp/bestsellers/", "/gp/new-releases/", "/gp/bestsellers/handmade/",
    "/gp/bestsellers/beauty/", "/gp/bestsellers/drugstore/", "/gp/bestsellers/grocery/",
    "/gp/bestsellers/kitchen/", "/gp/bestsellers/home/", "/gp/bestsellers/toys/",
    "/gp/bestsellers/baby/", "/gp/bestsellers/pet-supplies/", "/gp/bestsellers/officeproduct/",
    "/gp/bestsellers/sports/", "/gp/bestsellers/outdoors/", "/gp/bestsellers/diy/",
    "/gp/bestsellers/fashion/", "/gp/bestsellers/luggage/", "/gp/bestsellers/automotive/",
    "/gp/bestsellers/industrial/", "/gp/bestsellers/musical-instruments/"
  ];

  const M = {
    asinQ: [], asinSeen: new Set(), sellerQ: [], sellerSeen: new Set(),
    uk: [], seenThisRun: [], catFrontier: CATS.slice(), catSeen: new Set(),
    stats: { asin: 0, tp: 0, prof: 0, uk: 0, cap: 0 },
    running: false, finished: false, startedAt: 0, pausedUntil: 0
  };
  window.__M = M;

  window.__seedSeen = function (ids) {
    (ids || []).forEach(x => M.sellerSeen.add(x));
    return M.sellerSeen.size;
  };
  window.__ukStatus = function () {
    return JSON.stringify({
      finished: M.finished, running: M.running, stats: M.stats,
      asinQ: M.asinQ.length, sellerQ: M.sellerQ.length, newUk: M.uk.length,
      elapsedS: M.startedAt ? Math.round((Date.now() - M.startedAt) / 1000) : 0
    });
  };
  window.__ukDrain = function () {
    return JSON.stringify({ uk: M.uk, seen: M.seenThisRun, stats: M.stats });
  };
  window.__ukStop = function () { M.running = false; return 'stopped'; };

  async function refillFromCategories() {
    let url = M.catFrontier.shift();
    while (url && M.catSeen.has(url)) url = M.catFrontier.shift();
    if (!url) return;
    M.catSeen.add(url);
    try {
      const r = await fetch(url, { credentials: 'include', headers: HDRS });
      const t = await r.text();
      if (r.status === 503 || /captcha/i.test(t.slice(0, 4000))) { M.stats.cap++; M.pausedUntil = Date.now() + 90000; return; }
      for (const m of t.matchAll(/\/dp\/([A-Z0-9]{10})/g)) { const a = m[1]; if (!M.asinSeen.has(a)) { M.asinSeen.add(a); M.asinQ.push(a); } }
      for (const m of t.matchAll(/href="(\/gp\/(?:bestsellers|new-releases)\/[a-z0-9\-]+(?:\/[a-z0-9\-]+)?)[/"?]/gi)) { const c = m[1]; if (!M.catSeen.has(c) && M.catFrontier.length < 2000) M.catFrontier.push(c); }
    } catch (e) {}
  }

  function stopConditionsHit() {
    return M.uk.length >= MAX_NEW_UK || M.stats.cap >= MAX_CAP || (Date.now() - M.startedAt) >= MAX_MS;
  }

  window.__ukStart = function () {
    if (M.running) return 'already';
    M.running = true; M.finished = false; M.startedAt = Date.now();
    (async () => {
      while (M.running) {
        if (stopConditionsHit()) break;
        if (Date.now() < M.pausedUntil) { await new Promise(r => setTimeout(r, 5000)); continue; }
        if (M.asinQ.length < 40) await refillFromCategories();
        // --- ASIN step: extract seller + harvest related ASINs ---
        const a = M.asinQ.shift();
        if (a) {
          try {
            const r = await fetch('/dp/' + a, { credentials: 'include', headers: HDRS });
            const t = await r.text();
            if (r.status === 503 || /captcha/i.test(t.slice(0, 4000))) { M.stats.cap++; M.asinQ.unshift(a); M.pausedUntil = Date.now() + 120000; continue; }
            M.stats.asin++;
            const m = t.match(/href=['"]([^'"]*seller=([A-Z0-9]{10,16})[^'"]*)['"][^>]*id=['"]sellerProfileTriggerId['"][^>]*>([^<]*)</);
            if (m) { M.stats.tp++; const sid = m[2]; if (!M.sellerSeen.has(sid)) { M.sellerSeen.add(sid); M.sellerQ.push({ s: sid, n: m[3].trim() }); } }
            if (M.asinQ.length < 500) { let n = 0; for (const mm of t.matchAll(/\/dp\/([A-Z0-9]{10})/g)) { const x = mm[1]; if (!M.asinSeen.has(x)) { M.asinSeen.add(x); M.asinQ.push(x); if (++n >= 25) break; } } }
          } catch (e) {}
          await new Promise(r => setTimeout(r, 1600 + Math.random() * 900));
        }
        // --- Seller step: /sp -> keep GB ---
        const it = M.sellerQ.shift();
        if (it) {
          try {
            const r = await fetch('/sp?seller=' + it.s, { credentials: 'include', headers: HDRS });
            const t = await r.text();
            if (r.status === 503 || /captcha/i.test(t.slice(0, 4000))) { M.stats.cap++; M.sellerQ.unshift(it); M.pausedUntil = Date.now() + 120000; continue; }
            M.stats.prof++; M.seenThisRun.push(it.s);
            const i = t.search(/Business Name/i);
            if (i >= 0) {
              const parts = t.slice(i, i + 3000).replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, '␟').replace(/␟+/g, '␟').split('␟').map(x => x.trim()).filter(Boolean);
              const di = parts.findIndex(p => /^Business Address/i.test(p));
              const biz = parts[1] || null; let addr = [], country = null;
              if (di >= 0) { for (let k = di + 1; k < parts.length && addr.length < 8; k++) { if (/Delivery Policies|Returns|Help|Products|Review|Shipping/i.test(parts[k])) break; addr.push(parts[k]); } country = addr.length ? addr[addr.length - 1] : null; }
              if (country === 'GB' && biz) { M.uk.push({ s: it.s, n: it.n, biz, country, addr: addr.join(', ') }); M.stats.uk++; }
            }
          } catch (e) {}
          await new Promise(r => setTimeout(r, 1600 + Math.random() * 900));
        }
        if (!a && !it) await new Promise(r => setTimeout(r, 3000));
      }
      M.running = false; M.finished = true;
    })();
    return 'started';
  };
})();
'uk-worker-installed';
