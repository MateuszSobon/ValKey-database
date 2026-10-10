
from concurrent.futures import ThreadPoolExecutor
from http import client
from multiprocessing.pool import ThreadPool
from pydoc import cli
from sre_constants import CATEGORY_LINEBREAK
import valkey 

r = valkey.Valkey(host="127.0.0.1", port="6379", decode_responses=True)


LIMIT = 100 #limit zadan
WINDOW = 60 #czas okna

def allow_fixed_window(client_id: str) -> bool:
    key = f"rate:fixed:{client_id}"

    pipe = r.pipeline(transaction=True)
    pipe.incr(key)
    pipe.expire(key, WINDOW, nx=True)
    count, _ = pipe.execute()

    return count <= LIMIT 

def allow_naive(client_id) -> bool:
    key = f"rate:fixed:{client_id}"
    count = int(r.get(key) or 0)
    if count >= LIMIT:
        return False
    r.set(key, count +1, ex = WINDOW)
    return True

def run_tests(allow_fn, name, total=1000, workers=50):
    client = "test"
    r.delete(f"rate:fixed:{client}", f"rate:naive:{client}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: allow_fn(client), range(total)))

    allowed = sum(results)

    print(f"{name:10} | zadan: {total} | przepuszczone: {allowed} "
        f"| limit: {LIMIT} | bledne decyzje: {allowed - LIMIT}")


if __name__ == "__main__":
    run_tests(allow_naive, "naiwna")
    run_tests(allow_fixed_window, "atomowa")