import json
import time
from collections.abc import Callable, Mapping
from http.client import IncompleteRead
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    """Erro ao consultar ou interpretar uma API oficial."""


class JsonClient:
    def __init__(self, base_url: str, *, timeout: float = 30, attempts: int = 5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.attempts = attempts

    def get(self, path: str, params: Mapping[str, str | int] | None = None) -> Any:
        return self._baixar(path, params, json.loads)

    def get_bytes(self, path: str) -> bytes:
        return self._baixar(path, None, lambda conteudo: conteudo)

    def _baixar(
        self,
        path: str,
        params: Mapping[str, str | int] | None,
        converter: Callable[[bytes], Any],
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}/{path.lstrip('/')}{query}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ranking-do-congresso/0.1 (+projeto de transparencia publica)",
            },
        )

        for attempt in range(1, self.attempts + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - URLs oficiais fixas
                    return converter(response.read())
            except (HTTPError, URLError, TimeoutError, ConnectionError, IncompleteRead, json.JSONDecodeError) as error:
                if attempt == self.attempts:
                    raise ApiError(f"Falha ao consultar {url}: {error}") from error
                time.sleep(_espera(error, attempt))

        raise AssertionError("laço de tentativas terminou sem retorno")


def _espera(error: Exception, attempt: int) -> float:
    """Segundos até a próxima tentativa; em 429 (muitas requisições), respeita o Retry-After da API."""
    if isinstance(error, HTTPError) and error.code == 429:
        retry_after = (error.headers or {}).get("Retry-After", "")
        return float(retry_after) if retry_after.isdigit() else 15.0 * attempt
    return 0.5 * 2 ** (attempt - 1)
