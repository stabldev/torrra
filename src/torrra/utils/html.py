import httpx


def parse_html(url: str) -> str:
    res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
    html = res.text

    return html
