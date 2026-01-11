import time

class Cache:
    def __init__(self, ttl=60):
        self.ttl = ttl
        self.store = {}

    def get(self, key):
        entry = self.store.get(key)
        if entry and time.time() - entry['timestamp'] < self.ttl:
            return entry['value']
        return None

    def set(self, key, value):
        self.store[key] = {
            "value": value,
            "timestamp": time.time()
        }