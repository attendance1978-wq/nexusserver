"""Authentication: password hashing, signed-cookie sessions and Basic auth.

Run:  python -m nexusserver examples.auth_app:app
Try:  curl -c jar -b jar -X POST localhost:8000/login -d 'username=ada&password=lovelace'
      curl -c jar -b jar localhost:8000/profile
      curl -u admin:admin-pass localhost:8000/admin/stats      # Basic auth
      curl -c jar -b jar -X POST localhost:8000/logout

In real code load SECRET_KEY from the environment and keep it stable between restarts.
"""

import os

from nexusserver import Application, Request, Response, Unauthorized
from nexusserver.middleware import BasicAuthMiddleware, SignedSessionMiddleware
from nexusserver.security import hash_password, verify_password

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me-please-0123456789")

USERS = {"ada": hash_password("lovelace"), "grace": hash_password("hopper")}  # store hashes, never passwords
ADMINS = {"admin": hash_password("admin-pass")}

app = Application()
app.add_middleware(SignedSessionMiddleware, secret_key=SECRET_KEY, max_age=3600)


@app.post("/login")
def login(request: Request):
    form = request.form()
    username, password = form.get("username", ""), form.get("password", "")
    stored = USERS.get(username)
    if stored is None or not verify_password(password, stored):
        raise Unauthorized("Wrong username or password")
    request.state["session"]["user"] = username
    return {"logged_in_as": username}


@app.get("/profile")
def profile(request: Request):
    user = request.state["session"].get("user")
    if not user:
        raise Unauthorized("Please log in")
    return {"user": user}


@app.post("/logout")
def logout(request: Request):
    request.state["session"].clear()
    return {"logged_out": True}


# A sub-application for the admin area, protected with HTTP Basic auth.
# (BasicAuthMiddleware guards every path it wraps, so we wrap a separate Application
# and dispatch /admin/* to it.)
admin = Application()
admin.add_middleware(BasicAuthMiddleware, users=ADMINS, realm="Admin area")


@admin.get("/admin/stats")
def stats(request: Request):
    return {"admin": request.state["user"], "users": len(USERS)}


@app.get("/admin/<path:rest>")
def admin_gateway(request: Request, rest: str) -> Response:
    return admin.handle(request)


if __name__ == "__main__":
    app.run()
