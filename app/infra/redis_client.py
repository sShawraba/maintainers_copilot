import redis
import json
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def store_conversation(conv_id: str, messages: list, ttl: int = 3600):
    """Store conversation history in Redis with TTL."""
    key = f"conv:{conv_id}"
    redis_client.setex(key, ttl, json.dumps(messages))

def get_conversation(conv_id: str) -> list:
    """Retrieve conversation history."""
    key = f"conv:{conv_id}"
    data = redis_client.get(key)
    return json.loads(data) if data else []