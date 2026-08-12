#!/usr/bin/env python3
"""
India Amazon-seller lead build, stage 1: DNS pre-filter.

Crawling the whole Indian web to find sellers is the wrong funnel — a smoke test
over the top 400 .in sites qualified 0.5% of them, because the head of the list
is news/banks/services. The sellers are identifiable far more cheaply: an Indian
D2C brand almost always runs on Shopify (a random sample of .in domains came
back 9% Shopify), and a hosted store platform is visible in the A record alone.

So: resolve the whole universe (~100x cheaper than an HTTP GET), keep the IP,
and let stage 2 crawl only the domains that live on a store platform. The IP is
kept for every host so new platform ranges can be spotted afterwards by
clustering the most common /24s (see --report).

Raw UDP DNS against several public resolvers, ~600-1500 lookups/s — the system
resolver tops out near 100/s, which is too slow for a 690k universe.

Output: data/in_dns.tsv   host<TAB>ip   (append, resumable)

Usage:
    python3 outreach/in-sellers/in1_dns.py --domains-file data/in_universe.txt
    python3 outreach/in-sellers/in1_dns.py --report
"""
import argparse
import asyncio
import collections
import random
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = DATA / "in_dns.tsv"

RESOLVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "8.8.4.4", "1.0.0.1", "208.67.222.222"]

# A-record ranges that identify a hosted online store
PLATFORM_NETS = {
    "shopify": ("23.227.38.", "23.227.32."),
    "wix": ("185.230.63.", "185.230.60."),
    "squarespace": ("198.185.159.", "198.49.23.", "198.185.161."),
    "bigcommerce": ("34.98.66.", "104.16."),   # 104.16 is CF-fronted, weak
    "dukaan": ("35.244.",),
}


def build_query(txid, name):
    q = struct.pack(">HHHHHH", txid, 0x0100, 1, 0, 0, 0)
    for part in name.rstrip(".").split("."):
        b = part.encode("idna") if any(ord(c) > 127 for c in part) else part.encode()
        q += bytes([len(b)]) + b
    return q + b"\x00" + struct.pack(">HH", 1, 1)


def parse_answer(data):
    try:
        qd, an = struct.unpack(">HH", data[4:8])
        i = 12
        for _ in range(qd):
            while data[i]:
                if data[i] & 0xC0:
                    i += 1
                    break
                i += data[i] + 1
            i += 5
        for _ in range(an):
            if data[i] & 0xC0:
                i += 2
            else:
                while data[i]:
                    i += data[i] + 1
                i += 1
            rtype, _cls, _ttl, rdlen = struct.unpack(">HHIH", data[i:i + 10])
            i += 10
            if rtype == 1 and rdlen == 4:
                return ".".join(str(b) for b in data[i:i + 4])
            i += rdlen
    except Exception:
        pass
    return None


class Resolver(asyncio.DatagramProtocol):
    def __init__(self):
        self.pending = {}

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) < 4:
            return
        txid = struct.unpack(">H", data[:2])[0]
        fut = self.pending.pop(txid, None)
        if fut and not fut.done():
            fut.set_result(parse_answer(data))


async def worker(queue, protos, out, sem, stats):
    while True:
        host = await queue.get()
        if host is None:
            queue.task_done()
            return
        ip = None
        for attempt in range(2):
            proto, addr = random.choice(protos)
            txid = random.randrange(65536)
            while txid in proto.pending:
                txid = random.randrange(65536)
            fut = asyncio.get_running_loop().create_future()
            proto.pending[txid] = fut
            try:
                proto.transport.sendto(build_query(txid, host), addr)
                ip = await asyncio.wait_for(fut, timeout=3.5)
            except Exception:
                proto.pending.pop(txid, None)
                ip = None
            if ip:
                break
        out.append((host, ip or ""))
        stats["n"] += 1
        if ip:
            stats["alive"] += 1
        queue.task_done()


def platform_of(ip):
    for name, prefixes in PLATFORM_NETS.items():
        if any(ip.startswith(p) for p in prefixes):
            return name
    return ""


async def run(hosts, concurrency):
    loop = asyncio.get_running_loop()
    protos = []
    for r in RESOLVERS:
        transport, proto = await loop.create_datagram_endpoint(
            Resolver, remote_addr=(r, 53))
        protos.append((proto, (r, 53)))
    queue = asyncio.Queue(maxsize=concurrency * 4)
    out, stats = [], {"n": 0, "alive": 0}
    workers = [asyncio.create_task(worker(queue, protos, out, None, stats))
               for _ in range(concurrency)]

    fh = OUT.open("a", encoding="utf-8")
    import time
    t0 = time.time()
    for i, h in enumerate(hosts):
        await queue.put(h)
        if len(out) >= 2000:
            fh.writelines(f"{a}\t{b}\n" for a, b in out)
            fh.flush()
            out.clear()
            rate = stats["n"] / max(1e-9, time.time() - t0)
            print(f"  {stats['n']}/{len(hosts)} resolved | {stats['alive']} alive "
                  f"| {rate:.0f}/s", flush=True)
    await queue.join()
    for _ in workers:
        await queue.put(None)
    await asyncio.gather(*workers)
    fh.writelines(f"{a}\t{b}\n" for a, b in out)
    fh.close()
    print(f"total {stats['n']}, alive {stats['alive']}")


def report():
    nets = collections.Counter()
    plat = collections.Counter()
    n = 0
    for line in OUT.read_text().splitlines():
        host, _, ip = line.partition("\t")
        if not ip:
            continue
        n += 1
        nets[".".join(ip.split(".")[:3])] += 1
        plat[platform_of(ip) or "-"] += 1
    print(f"{n} resolved hosts")
    print("platforms:", plat.most_common())
    print("top /24s:")
    for net, c in nets.most_common(25):
        print(f"  {net}.x  {c}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains-file")
    ap.add_argument("--concurrency", type=int, default=500)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    if args.report:
        return report()
    done = set()
    if OUT.exists():
        done = {l.split("\t")[0] for l in OUT.read_text().splitlines()}
    p = Path(args.domains_file)
    if not p.is_absolute():
        p = HERE / p
    hosts = [h.strip() for h in p.read_text().splitlines() if h.strip()]
    hosts = [h for h in hosts if h not in done]
    if args.limit:
        hosts = hosts[: args.limit]
    print(f"{len(done)} cached | resolving {len(hosts)} at {args.concurrency}",
          flush=True)
    asyncio.run(run(hosts, args.concurrency))


if __name__ == "__main__":
    main()
