
import valkey 

r = valkey.Valkey(host="127.0.0.1", port="6379", decode_responses=True)
print(r.ping())
print(r.incr("client:123"))