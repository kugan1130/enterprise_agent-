import redis
try:
    r = redis.Redis.from_url("redis://127.0.0.1:6379/0", decode_responses=True, protocol=2, socket_timeout=3.0)
    print("PING WITH PROTOCOL=2:", r.ping())
    r.set("test_key", "hello_world")
    print("GET test_key:", r.get("test_key"))
except Exception as e:
    print("REDIS ERROR:", type(e), e)
