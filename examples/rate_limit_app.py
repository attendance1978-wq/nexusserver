"""Rate limiting.

Run:  python -m nexusserver examples.rate_limit_app:app
Try:  for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w "%{http_code} " localhost:8000/api; done
      (the sixth request gets 429 with a Retry-After header)
"""

from nexusserver import Application
from nexusserver.middleware import RateLimitMiddleware

app = Application()

# 5 requests per 30 seconds per client IP. /health is never limited.
# Behind a reverse proxy, pass key_func=lambda request: <trusted client id> instead.
app.add_middleware(RateLimitMiddleware, limit=5, window=30, exempt_paths=("/health",))


@app.get("/api")
def api():
    return {"data": "expensive result"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run()
