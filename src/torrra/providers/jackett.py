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
