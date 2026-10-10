
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