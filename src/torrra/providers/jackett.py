from typing import Dict, List

import httpx


class JackettClient:
    def __init__(self, url: str, api_key: str, timeout: int = 10):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str) -> List[Dict]:
        endpoint = f"{self.url}/api/v2.0/indexers/all/results"
        params = {"apikey": self.api_key, "query": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            return resp.json().get("Results", [])

    async def validate(self) -> bool:
        url = f"{self.url}/api/v2.0/indexers/nonexistent_indexer/results"
        params = {"apikey": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return True
            except httpx.RequestError as e:
                print(f"[error] jackett: connection error: {e}")
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 401:
                    print("[error] jackett: invalid api key")
                elif status_code == 500 and "nonexistent_indexer" in e.response.text:
                    return True
            return False
