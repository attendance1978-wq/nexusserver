"""Configured middleware + writing your own.

Run:  python -m nexusserver examples.middleware_app:app
Try:  curl -i -H "Origin: https://app.example" localhost:8000/data
      curl -i --compressed localhost:8000/data
      curl -i localhost:8000/   # note the X-Request-Time header
"""

import time

from nexusserver import Application
from nexusserver.http.request import Request
from nexusserver.http.response import Response
from nexusserver.middleware import BaseMiddleware, CORSMiddleware, GZipMiddleware

app = Application()


class TimingMiddleware(BaseMiddleware):
    """Add an X-Request-Time header (milliseconds)."""

    def __call__(self, request: Request) -> Response:
        start = time.perf_counter()
        response = self.app(request)
        response.headers["X-Request-Time"] = f"{(time.perf_counter() - start) * 1000:.2f}ms"
        return response


# Keyword options go straight to the middleware's constructor.
app.add_middleware(CORSMiddleware, allow_origins=["https://app.example"], allow_credentials=True)
app.add_middleware(GZipMiddleware, minimum_size=200)
app.add_middleware(TimingMiddleware)


@app.get("/")
def index():
    return "ok"


@app.get("/data")
def data():
    return {"rows": [{"id": i, "value": "x" * 20} for i in range(50)]}


if __name__ == "__main__":
    app.run()
