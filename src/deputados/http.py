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
    def __init__(self, base_url: str, *, timeout: float = 30, attempts: int = 6, intervalo: float = 0.25) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.attempts = attempts
        # Intervalo mínimo entre chamadas, para não esbarrar no limite de requisições das APIs.
        self.intervalo = intervalo
        self._ultima_chamada = 0.0

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
        headers = {
            "Accept": "application/json",
            "User-Agent": "ranking-do-congresso/0.1 (+projeto de transparencia publica)",
        }
        # Arquivos grandes às vezes têm a conexão cortada no meio: o que já chegou é guardado
        # e a próxima tentativa pede só o restante (cabeçalho Range).
        recebido = b""

        for attempt in range(1, self.attempts + 1):
            time.sleep(max(0.0, self._ultima_chamada + self.intervalo - time.monotonic()))
            self._ultima_chamada = time.monotonic()
            pedido = Request(url, headers={**headers, "Range": f"bytes={len(recebido)}-"} if recebido else headers)
            try:
                with urlopen(pedido, timeout=self.timeout) as response:  # noqa: S310 - URLs oficiais fixas
                    if response.status != 206:
                        recebido = b""
                    try:
                        recebido += response.read()
                    except IncompleteRead as error:
                        recebido += error.partial
                        raise
                    return converter(recebido)
            except (HTTPError, URLError, TimeoutError, ConnectionError, IncompleteRead, json.JSONDecodeError) as error:
                if isinstance(error, json.JSONDecodeError):
                    recebido = b""
                if attempt == self.attempts:
                    raise ApiError(f"Falha ao consultar {url}: {error}") from error
                time.sleep(_espera(error, attempt))

        raise AssertionError("laço de tentativas terminou sem retorno")


def _espera(error: Exception, attempt: int) -> float:
    """Segundos até a próxima tentativa.

    Em 429 (muitas requisições) respeita o Retry-After da API. Nos demais erros (servidor fora do ar,
    timeout, conexão cortada) a espera dobra a cada tentativa, porque as APIs às vezes ficam instáveis
    por um ou dois minutos.
    """
    if isinstance(error, HTTPError) and error.code == 429:
        retry_after = (error.headers or {}).get("Retry-After", "")
        return float(retry_after) if retry_after.isdigit() else 15.0 * attempt
    return min(60.0, 5.0 * 2 ** (attempt - 1))
