"""Wspolny modul ogranicznika. Tryb pracy wybiera zmienna srodowiskowa VALKEY_MODE:
  single  (domyslnie) - pojedyncza instancja, VALKEY_HOST / VALKEY_PORT
  cluster             - klaster, VALKEY_NODES = pierwszy wezel startowy, np. 127.0.0.1:7001
"""
import os
import uuid

import valkey
from valkey.cluster import ValkeyCluster

MODE = os.environ.get("VALKEY_MODE", "single")

if MODE == "cluster":
    host, port = os.environ.get("VALKEY_NODES", "127.0.0.1:7001").split(",")[0].split(":")
    r = ValkeyCluster(
        host=host,
        port=int(port),
        decode_responses=True,
        socket_timeout=2,          # nie wisimy w nieskonczonosc, gdy wezel padnie
        socket_connect_timeout=2,
    )
else:
    r = valkey.Valkey(
        host=os.environ.get("VALKEY_HOST", "127.0.0.1"),
        port=int(os.environ.get("VALKEY_PORT", "6379")),
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2,
    )

LIMIT = 100   # limit zadan
WINDOW = 60   # czas okna (s)

# Fixed window jako skrypt Lua: INCR + ustawienie TTL przy pierwszym zadaniu, atomowo.
# (Transakcje MULTI/EXEC w kliencie klastrowym sa ograniczone, skrypt dziala wszedzie.)
FIXED_LUA = """
local c = redis.call('INCR', KEYS[1])
if c == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
return c
"""

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


def allow_fixed_window(client_id, limit=LIMIT, window=WINDOW) -> bool:
    """Atomowo (Lua): INCR + TTL w jednym kroku."""
    key = f"rate:fixed:{client_id}"
    count = r.eval(FIXED_LUA, 1, key, window * 1000)
    return int(count) <= limit


def allow_naive(client_id, limit=LIMIT, window=WINDOW) -> bool:
    """Naiwnie: GET -> sprawdzenie -> SET (nieatomowe, do porownania)."""
    key = f"rate:naive:{client_id}"
    count = int(r.get(key) or 0)
    if count >= limit:
        return False
    r.set(key, count + 1, ex=window)
    return True


def allow_sliding(client_id, limit=LIMIT, window=WINDOW) -> bool:
    """Atomowo (Lua): sorted set, czas z serwera Valkey."""
    key = f"rate:sliding:{client_id}"
    member = str(uuid.uuid4())
    return r.eval(SLIDING_LUA, 1, key, window * 1000, limit, member) == 1


ALGORITHMS = {
    "naive": allow_naive,
    "fixed": allow_fixed_window,
    "sliding": allow_sliding,
}
