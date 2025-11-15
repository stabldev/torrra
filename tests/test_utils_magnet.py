import httpx
import respx

from torrra.utils.magnet import resolve_magnet_uri


async def test_resolve_already_magnet():
    # tests that a magnet uri is returned as is
    magnet = "magnet:?xt=urn:btih:test"
    resolved = await resolve_magnet_uri(magnet)
    assert resolved == magnet


@respx.mock
async def test_resolve_http_redirect():
    # tests that a 301/302 redirect is handled correctly
    test_url = "http://test.com/redirect"
    magnet_uri = "magnet:?xt=urn:btih:redirect"
    respx.get(test_url).mock(httpx.Response(302, headers={"location": magnet_uri}))

    resolved = await resolve_magnet_uri(test_url)
    assert resolved == magnet_uri


@respx.mock
async def test_resolve_http_error_returns_none():
    # tests that an http error results in none
    test_url = "http://test.com/error"
    respx.get(test_url).mock(side_effect=httpx.RequestError("test error"))

    resolved = await resolve_magnet_uri(test_url)
    assert resolved is None


@respx.mock
async def test_resolve_unhandled_url_returns_none():
    # tests that a normal url (e.g. html page) returns none
    test_url = "http://test.com/page.html"
    respx.get(test_url).mock(httpx.Response(200, content=b"<html></html>"))

    resolved = await resolve_magnet_uri(test_url)
    assert resolved is None
