from collections.abc import Callable
from typing import Any

from tqdm.auto import tqdm

from deputados.http import JsonClient
from deputados.models import Comparecimento, Despesa, Parlamentar

BASE_URL = "https://legis.senado.leg.br/dadosabertos"
SOURCE_URL = f"{BASE_URL}/senador/lista/atual"
ADMIN_BASE_URL = "https://adm.senado.gov.br/adm-dadosabertos"
EXPENSES_SOURCE_URL = f"{ADMIN_BASE_URL}/api/v1/senadores/despesas_ceaps"
VOTES_SOURCE_URL = f"{BASE_URL}/votacao"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class SenadoSource:
    def __init__(
        self,
        get_json: Callable[..., dict[str, Any]] | None = None,
        get_admin_json: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        self._get = get_json or JsonClient(BASE_URL).get
        self._get_admin = get_admin_json or JsonClient(ADMIN_BASE_URL).get

    def parlamentares(self) -> list[Parlamentar]:
        payload = self._get("senador/lista/atual")
        raiz = payload.get("ListaParlamentarEmExercicio", {})
        parlamentares = raiz.get("Parlamentares", {}).get("Parlamentar", [])
        return [self._normalizar(item) for item in _as_list(parlamentares)]

    def despesas(self, ano: int) -> list[Despesa]:
        payload = self._get_admin(f"api/v1/senadores/despesas_ceaps/{ano}")
        if not isinstance(payload, list):
            raise ValueError("Resposta inesperada do Senado: despesas não são uma lista")
        return [
            self._normalizar_despesa(item)
            for item in tqdm(payload, desc="Despesas do Senado", unit="despesa", disable=None)
        ]

    def comparecimentos(self, ano: int) -> list[Comparecimento]:
        payload = self._get(
            "votacao",
            {"dataInicio": f"{ano}-01-01", "dataFim": f"{ano}-12-31"},
        )
        if not isinstance(payload, list):
            raise ValueError("Resposta inesperada do Senado: votações não são uma lista")

        registros = []
        for votacao in tqdm(payload, desc="Votações do Senado", unit="votação", disable=None):
            for voto in votacao.get("votos", []):
                registros.append(
                    Comparecimento(
                        parlamentar_id=str(voto["codigoParlamentar"]),
                        sessao_id=str(votacao["codigoSessao"]),
                        votacao_id=str(votacao["codigoSessaoVotacao"]),
                        data=votacao["dataSessao"],
                        status=voto["siglaVotoParlamentar"],
                        status_descricao=voto.get("descricaoVotoParlamentar"),
                        descricao_votacao=votacao["descricaoVotacao"],
                    )
                )
        return registros

    @staticmethod
    def _normalizar(item: dict[str, Any]) -> Parlamentar:
        identificacao = item["IdentificacaoParlamentar"]
        mandato = item.get("Mandato", {})
        primeira = mandato.get("PrimeiraLegislaturaDoMandato", {})
        segunda = mandato.get("SegundaLegislaturaDoMandato", {})

        legislaturas = [
            str(valor)
            for valor in (primeira.get("NumeroLegislatura"), segunda.get("NumeroLegislatura"))
            if valor is not None
        ]
        return Parlamentar(
            id_fonte=str(identificacao["CodigoParlamentar"]),
            casa="senado",
            cargo="senador",
            nome=identificacao["NomeParlamentar"],
            nome_civil=identificacao.get("NomeCompletoParlamentar"),
            partido=identificacao.get("SiglaPartidoParlamentar"),
            uf=identificacao.get("UfParlamentar") or mandato.get("UfParlamentar"),
            email=identificacao.get("EmailParlamentar"),
            url_foto=_https(identificacao.get("UrlFotoParlamentar")),
            url_perfil=_https(identificacao.get("UrlPaginaParlamentar")),
            legislatura=",".join(legislaturas) or None,
            mandato_inicio=primeira.get("DataInicio"),
            mandato_fim=segunda.get("DataFim") or primeira.get("DataFim"),
            participacao=mandato.get("DescricaoParticipacao"),
        )

    @staticmethod
    def _normalizar_despesa(item: dict[str, Any]) -> Despesa:
        return Despesa(
            id_fonte=str(item["id"]),
            parlamentar_id=str(item["codSenador"]),
            ano=int(item["ano"]),
            mes=int(item["mes"]),
            tipo=(item.get("tipoDespesa") or "Não informado").strip(),
            tipo_documento=item.get("tipoDocumento"),
            fornecedor=item.get("fornecedor"),
            cpf_cnpj=item.get("cpfCnpj"),
            documento=item.get("documento"),
            data=item.get("data"),
            detalhamento=item.get("detalhamento"),
            valor=float(item["valorReembolsado"]),
        )


def _https(url: str | None) -> str | None:
    if url and url.startswith("http://"):
        return f"https://{url.removeprefix('http://')}"
    return url
