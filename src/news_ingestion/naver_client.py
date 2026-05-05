from __future__ import annotations

import json
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import NaverConfig
from .models import NaverNewsItem


class NaverApiError(RuntimeError):
    pass


class NaverNewsClient:
    API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, config: NaverConfig, timeout_seconds: int = 15) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds

    def search(self, query: str) -> Iterable[NaverNewsItem]:
        for page in range(self._config.max_pages):
            start = page * self._config.display + 1
            if start > 1000:
                break
            payload = self._request(query=query, start=start)
            items = payload.get("items", [])
            for item in items:
                yield NaverNewsItem(
                    title=item.get("title", ""),
                    originallink=item.get("originallink", ""),
                    link=item.get("link", ""),
                    description=item.get("description", ""),
                    pubDate=item.get("pubDate", ""),
                )

            if len(items) < self._config.display:
                break

    def _request(self, query: str, start: int) -> dict:
        params = urlencode(
            {
                "query": query,
                "display": self._config.display,
                "start": start,
                "sort": "date",
            }
        )
        request = Request(
            f"{self.API_URL}?{params}",
            headers={
                "X-Naver-Client-Id": self._config.client_id,
                "X-Naver-Client-Secret": self._config.client_secret,
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise NaverApiError(f"Naver API returned {exc.code}: {message}") from exc
        except URLError as exc:
            raise NaverApiError(f"Naver API request failed: {exc}") from exc
