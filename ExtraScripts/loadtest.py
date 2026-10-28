"""Generator ruchu: rozrzuca zadania jednego klienta po wszystkich instancjach.

Uzycie: python loadtest.py [algo] [total] [workers]
  algo:    naive | fixed | sliding   (domyslnie sliding)
  total:   liczba zadan              (domyslnie 1000)
  workers: liczba watkow klienta     (domyslnie 50)
"""
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests

PORTS = [8001, 8002, 8003]
LIMIT = 100

_local = threading.local()


def get_session():
    # jedna sesja HTTP na watek (ponowne uzycie polaczen)
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def call(i, client_id, algo):
    port = PORTS[i % len(PORTS)]  # round-robin po instancjach
    t0 = time.perf_counter()
    try:
        resp = get_session().get(
            f"http://127.0.0.1:{port}/check",
            params={"client": client_id, "algo": algo},
            timeout=5,
        )
        status = resp.status_code
    except requests.RequestException:
        status = 0  # brak odpowiedzi (np. instancja nie dziala)
    return port, status, (time.perf_counter() - t0) * 1000


def percentile(sorted_values, p):
    return sorted_values[min(len(sorted_values) - 1, int(len(sorted_values) * p))]


def main():
    algo = sys.argv[1] if len(sys.argv) > 1 else "sliding"
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    client_id = f"load-{uuid.uuid4().hex[:8]}"  # swiezy klient = czysty licznik

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda i: call(i, client_id, algo), range(total)))
    elapsed = time.perf_counter() - t0

    allowed_per_port = Counter(port for port, status, _ in results if status == 200)
    allowed = sum(allowed_per_port.values())
    rejected = sum(1 for _, status, _ in results if status == 429)
    errors = sum(1 for _, status, _ in results if status not in (200, 429))
    latencies = sorted(lat for _, _, lat in results)

    print(f"algorytm: {algo} | klient: {client_id} | zadan: {total} | watkow: {workers}")
    print("przepuszczone wg instancji:",
          {p: allowed_per_port.get(p, 0) for p in PORTS})
    print(f"przepuszczone lacznie: {allowed} | odrzucone: {rejected} | bledy: {errors}")
    print(f"limit: {LIMIT} | bledne decyzje (nadmiar): {max(0, allowed - LIMIT)}")
    print(f"przepustowosc: {total / elapsed:.0f} zad/s | "
          f"opoznienie p50: {percentile(latencies, 0.50):.1f} ms | "
          f"p95: {percentile(latencies, 0.95):.1f} ms | "
          f"p99: {percentile(latencies, 0.99):.1f} ms")


if __name__ == "__main__":
    main()
