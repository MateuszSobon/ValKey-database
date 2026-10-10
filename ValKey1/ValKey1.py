
from concurrent.futures import ThreadPoolExecutor
from http import client
from multiprocessing.pool import ThreadPool
from pydoc import cli
from sre_constants import CATEGORY_LINEBREAK
import uuid
import valkey 

r = valkey.Valkey(host="127.0.0.1", port="6379", decode_responses=True)


LIMIT = 100 #limit zadan
WINDOW = 60 #czas okna

SLIDING_LUA = """
local t = redis.call('TIME')
local now = t[1] * 1000 + math.floor(t[2] / 1000)   -- czas serwera w ms
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])

redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now - window)

if redis.call('ZCARD', KEYS[1]) < limit then
    redis.call('ZADD', KEYS[1], now, ARGV[3])
    redis.call('PEXPIRE', KEYS[1], window)
    return 1
end
return 0
"""

sliding_script = r.register_script(SLIDING_LUA)

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

def allow_sliding(client_id, limit = LIMIT, window = WINDOW) -> bool:
    key = f"rate:fixed:{client_id}"
    member = str(uuid.uuid4())
    return sliding_script(keys=[key], args=[window * 1000, limit, member]) == 1

def run_tests(allow_fn, name, total=1000, workers=50):
    client = "test"
    r.delete(f"rate:fixed:{client}", f"rate:naive:{client}", f"rate:sliding:{client}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: allow_fn(client), range(total)))

    allowed = sum(results)

    print(f"{name:10} | zadan: {total} | przepuszczone: {allowed} "
        f"| limit: {LIMIT} | bledne decyzje: {allowed - LIMIT}")


if __name__ == "__main__":
    run_tests(allow_naive, "naiwna")
    run_tests(allow_fixed_window, "atomowa")
    run_tests(allow_sliding, "przesuwne")