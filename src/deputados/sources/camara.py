from collections.abc import Callable
from typing import Any

from tqdm.auto import tqdm

from deputados.http import JsonClient
from deputados.models import Parlamentar

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
SOURCE_URL = f"{BASE_URL}/deputados"


class CamaraSource:
    def __init__(self, get_json: Callable[..., dict[str, Any]] | None = None) -> None:
        self._get = get_json or JsonClient(BASE_URL).get

    def parlamentares(self) -> list[Parlamentar]:
        resultado: list[Parlamentar] = []
        pagina = 1

        with tqdm(desc="Deputados da Câmara", unit="página", disable=None) as progress:
            while True:
                payload = self._get(
                    "deputados",
                    {"pagina": pagina, "itens": 100, "ordem": "ASC", "ordenarPor": "nome"},
                )
                dados = payload.get("dados", [])
                if not isinstance(dados, list):
                    raise ValueError("Resposta inesperada da Câmara: 'dados' não é uma lista")

                resultado.extend(self._normalizar(item) for item in dados)
                progress.update()
                progress.set_postfix(registros=len(resultado))
                if len(dados) < 100:
                    return resultado
                pagina += 1

    @staticmethod
    def _normalizar(item: dict[str, Any]) -> Parlamentar:
        deputado_id = str(item["id"])
        return Parlamentar(
            id_fonte=deputado_id,
            casa="camara",
            cargo="deputado_federal",
            nome=item["nome"],
            nome_civil=None,
            partido=item.get("siglaPartido"),
            uf=item.get("siglaUf"),
            email=item.get("email"),
            url_foto=item.get("urlFoto"),
            url_perfil=f"https://www.camara.leg.br/deputados/{deputado_id}",
            legislatura=str(item["idLegislatura"]) if item.get("idLegislatura") is not None else None,
            participacao="em_exercicio",
        )
