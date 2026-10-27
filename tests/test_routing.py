import pytest

from nexusserver.exceptions import MethodNotAllowed, NotFound
from nexusserver.http.request import Request
from nexusserver.routing.router import Router


def test_int_converter():
    router = Router()

    @router.get("/users/<int:user_id>")
    def user(user_id):
        return user_id

    handler, params = router.resolve(Request("GET", "/users/42"))
    assert params == {"user_id": 42}
    with pytest.raises(NotFound):
        router.resolve(Request("GET", "/users/abc"))


def test_path_converter_spans_slashes():
    router = Router()
    router.get("/files/<path:rest>")(lambda rest: rest)
    _, params = router.resolve(Request("GET", "/files/a/b/c.txt"))
    assert params == {"rest": "a/b/c.txt"}


def test_method_not_allowed():
    router = Router()
    router.get("/only-get")(lambda: "ok")
    with pytest.raises(MethodNotAllowed):
        router.resolve(Request("POST", "/only-get"))


def test_unknown_converter():
    with pytest.raises(ValueError):
        Router().get("/x/<uuid:id>")(lambda id: id)
