"""Test awarii: staly ruch + os czasu (co sekunde: ile zadan OK, ile bledow).

Uzycie: python failover_test.py [algo] [sekundy] [zad_na_sekunde]
  algo:            fixed | sliding | naive  (domyslnie sliding)
  sekundy:         czas trwania testu       (domyslnie 40)
  zad_na_sekunde:  tempo ruchu              (domyslnie 30)

Ruch idzie do wielu klientow (kluczy), wiec rozklada sie na wszystkie wezly
glowne klastra. Podczas testu zabij wezel w drugim terminalu i obserwuj kolumne
"bledy". Za OK uznajemy odpowiedzi 200 (przepuszczone) i 429 (odrzucone):
w obu przypadkach system podjal decyzje. Bledem jest 503 / brak odpowiedzi.
"""
import random
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

PORTS = [8001, 8002, 8003]
CLIENTS = 30          # liczba roznych klientow (kluczy)
TIMEOUT = 4           # timeout zadania HTTP (s)


def main():
    algo = sys.argv[1] if len(sys.argv) > 1 else "sliding"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    rate = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    run_id = uuid.uuid4().hex[:6]
    results = []                 # (czas zakonczenia wzgledem startu, status)
    lock = threading.Lock()
    local = threading.local()
    t0 = time.perf_counter()

    def task(n):
        if not hasattr(local, "s"):
            local.s = requests.Session()
        client_id = f"fo-{run_id}-{random.randrange(CLIENTS)}"
        port = PORTS[n % len(PORTS)]
        try:
            resp = local.s.get(
                f"http://127.0.0.1:{port}/check",
                params={"client": client_id, "algo": algo},
                timeout=TIMEOUT,
            )
            status = resp.status_code
        except requests.RequestException:
            status = 0
        with lock:
            results.append((time.perf_counter() - t0, status))

    print(f"algorytm: {algo} | {rate} zad/s | {duration} s | {CLIENTS} klientow")
    print(" t[s] | ok | bledy")

    sent = 0
    with ThreadPoolExecutor(max_workers=200) as pool:
        next_t = t0
        for s in range(duration):
            for _ in range(rate):
                pool.submit(task, sent)
                sent += 1
                next_t += 1.0 / rate
                delay = next_t - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
            with lock:
                bucket = [st for (td, st) in results if s <= td < s + 1]
            ok = sum(1 for st in bucket if st in (200, 429))
            err = len(bucket) - ok
            print(f"{s:5d} | {ok:2d} | {err:5d}", flush=True)

    # po zamknieciu puli wszystkie zadania sa zakonczone
    errors = sorted(td for td, st in results if st not in (200, 429))
    total = len(results)
    print("-" * 30)
    print(f"zadan: {total} | bledy: {len(errors)} ({100 * len(errors) / max(total, 1):.1f}%)")
    if errors:
        print(f"pierwszy blad: t = {errors[0]:.1f} s | ostatni blad: t = {errors[-1]:.1f} s "
              f"| okno bledow: {errors[-1] - errors[0]:.1f} s")
    else:
        print("brak bledow")


if __name__ == "__main__":
    main()
