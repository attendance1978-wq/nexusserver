"""Sessions: a visit counter plus login / logout.

Run:  python -m nexusserver examples.sessions_app:app
Try:  curl -c jar -b jar localhost:8000/
      curl -c jar -b jar -X POST localhost:8000/login -d 'name=Ada'
      curl -c jar -b jar localhost:8000/me
      curl -c jar -b jar -X POST localhost:8000/logout
"""

from nexusserver import Application, Unauthorized
from nexusserver.middleware import SessionMiddleware

app = Application()
app.add_middleware(SessionMiddleware, cookie_name="demo_session", max_age=3600)


@app.get("/")
def index(request):
    session = request.state["session"]
    session["visits"] = session.get("visits", 0) + 1
    return {"visits": session["visits"]}


@app.post("/login")
def login(request):
    name = request.form().get("name", "").strip()
    if not name:
        raise Unauthorized("Tell me who you are")
    request.state["session"]["user"] = name
    return {"logged_in_as": name}


@app.get("/me")
def me(request):
    user = request.state["session"].get("user")
    if user is None:
        raise Unauthorized("Not logged in")
    return {"user": user}


@app.post("/logout")
def logout(request):
    request.state["session"].clear()
    return {"logged_out": True}


if __name__ == "__main__":
    app.run()
