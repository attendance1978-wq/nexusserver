"""Custom error responses.

Run:  python -m nexusserver examples.error_handlers:app
Try:  curl -i localhost:8000/missing
      curl -i localhost:8000/boom
      curl -i localhost:8000/orders/0
"""

import logging

from nexusserver import Application, HTTPError, NotFound, UnprocessableEntity

app = Application()


class OutOfStock(Exception):
    """An application-specific error."""


@app.errorhandler(404)                      # by status code
def not_found(request, exc):
    return {"error": "not_found", "path": request.path}, 404


@app.errorhandler(OutOfStock)               # by exception class
def out_of_stock(request, exc):
    return {"error": "out_of_stock", "detail": str(exc)}, 409


@app.errorhandler(HTTPError)                # base class: every other HTTPError (404 above is more specific)
def http_error(request, exc):
    return {"error": exc.message, "status": exc.status_code}, exc.status_code


@app.errorhandler(Exception)                # last resort for unexpected bugs
def crash(request, exc):
    logging.getLogger("example").exception("crash on %s", request.path)
    return {"error": "internal_error"}, 500  # never leak exception details here


@app.get("/boom")
def boom():
    raise RuntimeError("something broke")


@app.get("/orders/<int:order_id>")
def order(order_id: int):
    if order_id == 0:
        raise UnprocessableEntity("Order ids start at 1")
    if order_id == 13:
        raise OutOfStock("item 13 is sold out")
    if order_id > 100:
        raise NotFound()
    return {"order": order_id}


if __name__ == "__main__":
    app.run()
