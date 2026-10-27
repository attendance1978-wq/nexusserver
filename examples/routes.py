"""Routing: path parameters, query strings, HTML, tuples and redirects.

Run:  python -m nexusserver examples.routes:app
Try:  curl localhost:8000/users/7
      curl "localhost:8000/search?q=nexus"
      curl localhost:8000/files/docs/readme.txt
"""

from nexusserver import Application, Response

app = Application()


@app.get("/")
def home():
    return {"message": "Welcome to NexusServer", "routes": ["/users/<int:id>", "/about", "/search", "/files/<path>"]}


@app.get("/about")
def about():
    return Response.html("<h1>About</h1><p>A tiny pure-Python web server.</p>")


@app.get("/users/<int:user_id>")
def user(user_id: int):  # user_id is already an int
    return {"user_id": user_id, "name": f"User {user_id}"}


@app.get("/search")
def search(request):
    query = request.query.get("q", "")
    return {"q": query, "results": [] if not query else [f"result for {query!r}"]}


@app.get("/files/<path:file_path>")  # <path:...> may contain slashes
def file_route(file_path: str):
    return {"file_path": file_path}


@app.get("/old-home")
def old_home():
    return Response.redirect("/", status_code=301)


@app.get("/teapot")
def teapot():
    return "short and stout", 418, {"X-Brew": "tea"}  # (body, status, headers)


if __name__ == "__main__":
    app.run()
