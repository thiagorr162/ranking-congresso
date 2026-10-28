import json
import time
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    """Erro ao consultar ou interpretar uma API oficial."""


class JsonClient:
    def __init__(self, base_url: str, *, timeout: float = 30, attempts: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.attempts = attempts

    def get(self, path: str, params: Mapping[str, str | int] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}/{path.lstrip('/')}{query}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "saiu-do-seu-bolso/0.1 (+projeto de transparencia publica)",
            },
        )

        for attempt in range(1, self.attempts + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - URLs oficiais fixas
                    return json.load(response)
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
                if attempt == self.attempts:
                    raise ApiError(f"Falha ao consultar {url}: {error}") from error
                time.sleep(0.5 * 2 ** (attempt - 1))

        raise AssertionError("laço de tentativas terminou sem retorno")
