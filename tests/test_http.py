import pytest

from nexusserver import Headers, Response
from nexusserver.exceptions import BadRequest, NotImplementedError_, PayloadTooLarge
from nexusserver.http.parser import parse_request


def test_parse_simple_request():
    raw = b"GET /hello?x=1 HTTP/1.1\r\nHost: localhost\r\n\r\n"
    req = parse_request(raw)
    assert req.method == "GET"
    assert req.path == "/hello"
    assert req.query == {"x": "1"}
    assert req.headers["Host"] == "localhost"


def test_parse_post_body():
    raw = (
        b"POST /submit HTTP/1.1\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 12\r\n\r\n"
        b'{"ok": true}'
    )
    req = parse_request(raw)
    assert req.method == "POST"
    assert req.json() == {"ok": True}


def test_no_content_length_means_no_body():
    assert parse_request(b"POST /x HTTP/1.1\r\nHost: a\r\n\r\nstray").body == b""


def test_incomplete_body_is_400():
    with pytest.raises(BadRequest):
        parse_request(b"POST /x HTTP/1.1\r\nContent-Length: 50\r\n\r\nshort")


def test_invalid_content_length_is_400():
    with pytest.raises(BadRequest):
        parse_request(b"POST /x HTTP/1.1\r\nContent-Length: abc\r\n\r\n")


def test_body_limit():
    with pytest.raises(PayloadTooLarge):
        parse_request(b"POST /x HTTP/1.1\r\nContent-Length: 10\r\n\r\n0123456789", max_body_size=5)


def test_chunked_is_501():
    with pytest.raises(NotImplementedError_):
        parse_request(b"POST /x HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n")


def test_path_is_percent_decoded():
    assert parse_request(b"GET /a%20b HTTP/1.1\r\n\r\n").path == "/a b"


def test_multiple_set_cookie_headers_stay_separate():
    response = Response("ok")
    response.set_cookie("a", "1")
    response.set_cookie("b", "2")
    lines = [v for n, v in response.headers.raw_items() if n == "Set-Cookie"]
    assert len(lines) == 2


def test_header_injection_is_rejected():
    with pytest.raises(ValueError):
        Headers().add("X-Test", "ok\r\nSet-Cookie: evil=1")
    with pytest.raises(ValueError):
        Response.redirect("/x\r\nSet-Cookie: evil=1")


def test_cookie_value_injection_is_rejected():
    with pytest.raises(ValueError):
        Response("ok").set_cookie("a", "1; Domain=evil.com")


def test_delete_cookie():
    response = Response("ok")
    response.delete_cookie("a")
    assert "Max-Age=0" in response.headers["Set-Cookie"]


def test_headers_are_case_insensitive():
    headers = Headers([("Content-Type", "text/plain")])
    assert headers["content-type"] == "text/plain"
    assert "CONTENT-TYPE" in headers
