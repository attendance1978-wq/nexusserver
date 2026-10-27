"""A small in-memory JSON CRUD API.

Run:  python -m nexusserver examples.json_api:app
Try:  curl localhost:8000/items
      curl -X POST localhost:8000/items -d '{"name": "Gadget"}'
      curl -X PUT localhost:8000/items/1 -d '{"name": "Renamed"}'
      curl -X DELETE localhost:8000/items/1
"""

import threading

from nexusserver import Application, NotFound, Response
from nexusserver.utils.validation import require_fields

app = Application()

_lock = threading.Lock()  # handlers run on a thread pool
_items: dict[int, dict] = {1: {"id": 1, "name": "Widget"}}
_next_id = 2


def _payload(request) -> dict:
    data = request.json()
    if not isinstance(data, dict):
        from nexusserver import BadRequest
        raise BadRequest("Expected a JSON object body")
    require_fields(data, ["name"])
    return data


@app.get("/items")
def list_items():
    return {"items": list(_items.values())}


@app.get("/items/<int:item_id>")
def get_item(item_id: int):
    if item_id not in _items:
        raise NotFound(f"Item {item_id} does not exist")
    return _items[item_id]


@app.post("/items")
def create_item(request):
    global _next_id
    data = _payload(request)
    with _lock:
        item = {"id": _next_id, "name": data["name"]}
        _items[_next_id] = item
        _next_id += 1
    return Response.json(item, status_code=201)


@app.put("/items/<int:item_id>")
def update_item(request, item_id: int):
    data = _payload(request)
    with _lock:
        if item_id not in _items:
            raise NotFound(f"Item {item_id} does not exist")
        _items[item_id]["name"] = data["name"]
        return _items[item_id]


@app.delete("/items/<int:item_id>")
def delete_item(item_id: int):
    with _lock:
        if _items.pop(item_id, None) is None:
            raise NotFound(f"Item {item_id} does not exist")
    return Response(b"", status_code=204)


if __name__ == "__main__":
    app.run()
