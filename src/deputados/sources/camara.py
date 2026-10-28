import csv
import io
import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Any

from tqdm.auto import tqdm

from deputados.http import JsonClient
from deputados.models import Autoria, Comparecimento, Despesa, Parlamentar

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
SOURCE_URL = f"{BASE_URL}/deputados"
FILES_BASE_URL = "https://dadosabertos.camara.leg.br/arquivos"
QUOTA_BASE_URL = "https://www.camara.leg.br/cotas"
EXPENSES_SOURCE_URL = QUOTA_BASE_URL
VOTES_SOURCE_URL = f"{FILES_BASE_URL}/eventosPresencaDeputados"
AUTHORSHIP_SOURCE_URL = f"{FILES_BASE_URL}/proposicoesAutores"

DOCUMENT_TYPES = {"0": "Nota Fiscal", "1": "Recibo", "2": "Despesa no Exterior", "4": "Nota Fiscal Eletrônica"}
PROJECT_TYPES = {
    "PL": "Projeto de Lei Ordinária",
    "PLP": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PRC": "Projeto de Resolução",
}
CLOSED_STATUS_PREFIXES = ("Arquivad", "Retirad", "Transformad", "Vetad", "Perdeu", "Prejudicad", "Devolvid", "Rejeitad")
CONDITION_LABELS = {"EFETIVADO": "Suplente efetivado"}
PLENARY_SESSION = "Sessão Deliberativa"
DEPUTY_AUTHOR = "Deputado(a)"


class CamaraSource:
    def __init__(
        self,
        get_json: Callable[..., dict[str, Any]] | None = None,
        get_file_json: Callable[[str], dict[str, Any]] | None = None,
        get_quota_bytes: Callable[[str], bytes] | None = None,
    ) -> None:
        self._get = get_json or JsonClient(BASE_URL).get
        self._get_file = get_file_json or JsonClient(FILES_BASE_URL, timeout=300).get
        self._get_quota = get_quota_bytes or JsonClient(QUOTA_BASE_URL, timeout=300).get_bytes

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
                    break
                pagina += 1

        return [
            self._com_exercicio(parlamentar)
            for parlamentar in tqdm(resultado, desc="Histórico dos deputados", unit="deputado", disable=None)
        ]

    def despesas(self, ano: int) -> list[Despesa]:
        arquivo = zipfile.ZipFile(io.BytesIO(self._get_quota(f"Ano-{ano}.csv.zip")))
        with arquivo.open(f"Ano-{ano}.csv") as conteudo:
            linhas = csv.DictReader(io.TextIOWrapper(conteudo, encoding="utf-8-sig"), delimiter=";")
            registros = [linha for linha in linhas if linha.get("ideCadastro")]

        vistos: dict[str, int] = defaultdict(int)
        despesas = []
        for linha in tqdm(registros, desc="Despesas da Câmara", unit="despesa", disable=None):
            documento_id = linha.get("ideDocumento") or f"lote-{linha.get('numLote')}"
            vistos[documento_id] += 1
            id_fonte = documento_id if vistos[documento_id] == 1 else f"{documento_id}-{vistos[documento_id]}"
            despesas.append(self._normalizar_despesa(linha, id_fonte))
        return despesas

    def comparecimentos(self, ano: int, parlamentares: Iterable[Parlamentar]) -> list[Comparecimento]:
        eventos = self._get_file(f"eventos/json/eventos-{ano}.json").get("dados", [])
        sessoes = sorted(
            (
                evento
                for evento in eventos
                if evento.get("descricaoTipo") == PLENARY_SESSION and evento.get("situacao") == "Encerrada"
            ),
            key=lambda evento: evento["dataHoraInicio"],
        )
        presencas = {
            (str(item["idDeputado"]), str(item["idEvento"]))
            for item in self._get_file(f"eventosPresencaDeputados/json/eventosPresencaDeputados-{ano}.json").get(
                "dados", []
            )
        }

        registros = []
        for parlamentar in parlamentares:
            for sessao in sessoes:
                inicio = sessao["dataHoraInicio"]
                if not _em_exercicio(parlamentar.periodos_exercicio, inicio):
                    continue
                presente = (parlamentar.id_fonte, str(sessao["id"])) in presencas
                registros.append(
                    Comparecimento(
                        parlamentar_id=parlamentar.id_fonte,
                        sessao_id=str(sessao["id"]),
                        votacao_id=str(sessao["id"]),
                        data=inicio[:10],
                        status="Presente" if presente else "Ausente",
                        status_descricao=None,
                        descricao_votacao=sessao.get("descricao") or PLENARY_SESSION,
                    )
                )
        return registros

    def autorias(self, parlamentar_ids: Iterable[str], ano: int) -> list[Autoria]:
        ids = set(parlamentar_ids)
        autores = self._get_file(f"proposicoesAutores/json/proposicoesAutores-{ano}.json").get("dados", [])
        proposicoes = {
            int(item["id"]): item
            for item in self._get_file(f"proposicoes/json/proposicoes-{ano}.json").get("dados", [])
            if str(item.get("dataApresentacao", "")).startswith(str(ano))
        }

        registros = []
        for autor in autores:
            parlamentar_id = str(autor.get("idDeputadoAutor") or "")
            proposicao = proposicoes.get(int(autor["idProposicao"]))
            if (
                parlamentar_id in ids
                and proposicao
                and autor.get("tipoAutor") == DEPUTY_AUTHOR
                and str(autor.get("proponente")) == "1"
            ):
                registros.append(self._normalizar_autoria(parlamentar_id, proposicao))
        return registros

    def _com_exercicio(self, parlamentar: Parlamentar) -> Parlamentar:
        historico = self._get(f"deputados/{parlamentar.id_fonte}/historico").get("dados", [])
        periodos = _periodos_exercicio(historico, parlamentar.legislatura)
        condicoes = [
            CONDITION_LABELS.get(item["condicaoEleitoral"], item["condicaoEleitoral"])
            for item in historico
            if item.get("condicaoEleitoral")
        ]
        detalhe = self._get(f"deputados/{parlamentar.id_fonte}").get("dados", {})
        return replace(
            parlamentar,
            nome_civil=detalhe.get("nomeCivil") or parlamentar.nome_civil,
            exercicio_inicio=periodos[-1][0][:10] if periodos else None,
            periodos_exercicio=periodos,
            participacao=condicoes[-1] if condicoes else parlamentar.participacao,
        )

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

    @staticmethod
    def _normalizar_despesa(linha: dict[str, str], id_fonte: str) -> Despesa:
        return Despesa(
            id_fonte=id_fonte,
            parlamentar_id=linha["ideCadastro"],
            ano=int(linha["numAno"]),
            mes=int(linha["numMes"]),
            tipo=(linha.get("txtDescricao") or "Não informado").strip(),
            tipo_documento=DOCUMENT_TYPES.get(linha.get("indTipoDocumento", ""), "Outro"),
            fornecedor=linha.get("txtFornecedor") or None,
            cpf_cnpj=(linha.get("txtCNPJCPF") or "").strip() or None,
            documento=linha.get("txtNumero") or None,
            data=(linha.get("datEmissao") or "")[:10] or None,
            detalhamento=linha.get("txtDescricaoEspecificacao") or None,
            valor=float((linha.get("vlrLiquido") or "0").replace(",", ".")),
            url_documento=linha.get("urlDocumento") or None,
            passageiro=linha.get("txtPassageiro") or None,
            trecho=linha.get("txtTrecho") or None,
        )

    @staticmethod
    def _normalizar_autoria(parlamentar_id: str, item: dict[str, Any]) -> Autoria:
        sigla = item.get("siglaTipo") or ""
        situacao = (item.get("ultimoStatus") or {}).get("descricaoSituacao") or None
        return Autoria(
            parlamentar_id=parlamentar_id,
            id_fonte=str(item["id"]),
            identificacao=f"{sigla} {item.get('numero')}/{item.get('ano')}",
            tipo=PROJECT_TYPES.get(sigla) or item.get("descricaoTipo") or "Não informado",
            ementa=item.get("ementa"),
            data=(item.get("dataApresentacao") or "")[:10] or None,
            situacao=situacao,
            tramitando=not (situacao or "").startswith(CLOSED_STATUS_PREFIXES),
            autoria=None,
            url_documento=f"https://www.camara.leg.br/propostas-legislativas/{item['id']}",
        )


def _periodos_exercicio(
    historico: list[dict[str, Any]],
    legislatura: str | None,
) -> tuple[tuple[str, str | None], ...]:
    periodos: list[tuple[str, str | None]] = []
    inicio = None
    for item in sorted(historico, key=lambda registro: registro["dataHora"]):
        if legislatura and str(item.get("idLegislatura")) != legislatura:
            continue
        situacao = item.get("situacao")
        if situacao == "Exercício":
            inicio = inicio or item["dataHora"]
        elif situacao and inicio:
            periodos.append((inicio, item["dataHora"]))
            inicio = None
    if inicio:
        periodos.append((inicio, None))
    return tuple(periodos)


def _em_exercicio(periodos: tuple[tuple[str, str | None], ...], momento: str) -> bool:
    return any(inicio <= momento and (fim is None or momento < fim) for inicio, fim in periodos)
