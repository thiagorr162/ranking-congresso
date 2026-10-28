import csv
import io
import re
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from http.client import IncompleteRead
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from tqdm.auto import tqdm

BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele"
SOURCE_URL = "https://dadosabertos.tse.jus.br"
ARQUIVOS = {
    "candidatos": "consulta_cand/consulta_cand_{ano}.zip",
    "bens": "bem_candidato/bem_candidato_{ano}.zip",
    "contas": "prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{ano}.zip",
    "votacao": "votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip",
}
CARGOS = {"camara": {"DEPUTADO FEDERAL"}, "senado": {"SENADOR"}}
FONTES_PUBLICAS = {"FUNDO ESPECIAL", "FUNDO PARTIDARIO"}
REPASSE_A_OUTROS = "DOACOES FINANCEIRAS A OUTROS"
SITUACOES = {"ELEITO POR QP": "Eleito por quociente partidário", "ELEITO POR MÉDIA": "Eleito por média"}
LIMITE_LISTAS = 50
TENTATIVAS = 6


def _normalizar(texto: str | None) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem_acento.upper()).strip()


def _valor(texto: str | None) -> float:
    return float((texto or "0").replace(".", "").replace(",", ".") or 0)


def _fonte(linha: dict[str, str]) -> str:
    """De onde o dinheiro veio originalmente: os fundos públicos têm prioridade sobre quem fez o repasse."""
    fonte, origem = _normalizar(linha["DS_FONTE_RECEITA"]), _normalizar(linha["DS_ORIGEM_RECEITA"])
    if "ESPECIAL" in fonte:
        return "Fundo eleitoral (público)"
    if "PARTIDARIO" in fonte:
        return "Fundo partidário (público)"
    if any(chave in origem for chave in ("PESSOAS FISICAS", "FINANCIAMENTO COLETIVO", "INTERNET")):
        return "Doações de pessoas"
    if "PROPRIOS" in origem:
        return "Recursos próprios"
    if "OUTROS CANDIDATOS" in origem:
        return "Outros candidatos"
    if "PARTIDO" in origem:
        return "Partido (recursos privados)"
    return "Outros"


def _digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


class TseSource:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def baixar(self, tipo: str, ano: int) -> Path:
        caminho = ARQUIVOS[tipo].format(ano=ano)
        destino = self.cache_dir / Path(caminho).name
        if destino.exists():
            return destino
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_suffix(".parcial")
        for tentativa in range(1, TENTATIVAS + 1):
            # Arquivos de centenas de MB: se a conexão travar ou cair, retoma de onde parou.
            inicio = temporario.stat().st_size if temporario.exists() else 0
            headers = {"User-Agent": "ranking-do-congresso/0.1", "Range": f"bytes={inicio}-"}
            try:
                with urlopen(Request(f"{BASE_URL}/{caminho}", headers=headers), timeout=60) as resposta:  # noqa: S310
                    modo = "ab" if resposta.status == 206 else "wb"
                    restante = int(resposta.headers.get("Content-Length") or 0)
                    with (
                        temporario.open(modo) as arquivo,
                        tqdm(total=restante, desc=destino.name, unit="B", unit_scale=True, disable=None) as progresso,
                    ):
                        while bloco := resposta.read(1 << 20):
                            arquivo.write(bloco)
                            progresso.update(len(bloco))
                break
            except (OSError, IncompleteRead) as erro:
                if tentativa == TENTATIVAS:
                    raise RuntimeError(f"Falha ao baixar {caminho} do TSE: {erro}") from erro
                time.sleep(5 * tentativa)
        temporario.rename(destino)
        return destino

    def linhas(self, tipo: str, ano: int, prefixo: str = "") -> Iterator[dict[str, str]]:
        """Percorre o CSV nacional (ou todos os estaduais, se não houver nacional) de um arquivo do TSE."""
        with zipfile.ZipFile(self.baixar(tipo, ano)) as arquivo:
            nomes = [nome for nome in arquivo.namelist() if nome.endswith(".csv") and nome.startswith(prefixo)]
            nacionais = [nome for nome in nomes if nome.endswith("_BRASIL.csv")]
            for nome in nacionais or nomes:
                with arquivo.open(nome) as conteudo:
                    yield from csv.DictReader(io.TextIOWrapper(conteudo, encoding="latin-1"), delimiter=";")

    def resumir(self, casa: str, parlamentares: list[dict[str, Any]], anos: list[int]) -> dict[str, dict]:
        candidatos = self._ligar(casa, parlamentares, anos)
        resultado = {}
        for ano in anos:
            do_ano = {sq: pid for pid, (ano_candidatura, sq, _) in candidatos.items() if ano_candidatura == ano}
            if not do_ano:
                continue
            resumos = {sq: self._resumo_vazio() for sq in do_ano}
            self._somar_receitas(ano, resumos)
            self._somar_despesas(ano, resumos)
            self._somar_votos(ano, resumos)
            self._somar_bens(ano, resumos)
            for sq, resumo in resumos.items():
                pid = do_ano[sq]
                resultado[pid] = {**candidatos[pid][2], "ano": ano, **self._finalizar(resumo)}
        self._patrimonio_anterior(candidatos, resultado)
        return resultado

    def _ligar(
        self,
        casa: str,
        parlamentares: list[dict[str, Any]],
        anos: list[int],
    ) -> dict[str, tuple[int, str, dict[str, Any]]]:
        """Liga cada parlamentar ao candidato do TSE pelo nome completo (ou de urna) e pela UF."""
        por_nome: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
        for ano in anos:
            for linha in self.linhas("candidatos", ano):
                if linha["DS_CARGO"] in CARGOS[casa] and linha.get("NR_TURNO", "1") == "1":
                    for nome in (linha["NM_CANDIDATO"], linha["NM_URNA_CANDIDATO"]):
                        por_nome[(linha["SG_UF"], _normalizar(nome))].append((ano, linha))

        ligados = {}
        for parlamentar in parlamentares:
            for nome in (parlamentar.get("nome_civil"), parlamentar.get("nome")):
                encontrados = {
                    linha["SQ_CANDIDATO"]: (ano, linha)
                    for ano, linha in por_nome.get((parlamentar.get("uf") or "", _normalizar(nome)), [])
                }
                if encontrados:
                    # Mais de uma candidatura com o mesmo nome: prefere a eleita e, depois, a mais recente.
                    ano, linha = max(
                        encontrados.values(),
                        key=lambda item: (item[1]["DS_SIT_TOT_TURNO"].startswith("ELEITO"), item[0]),
                    )
                    ligados[parlamentar["id_fonte"]] = (
                        ano,
                        linha["SQ_CANDIDATO"],
                        {
                            "cargo": linha["DS_CARGO"].capitalize(),
                            "uf": linha["SG_UF"],
                            "partido": linha["SG_PARTIDO"],
                            "nome_urna": linha["NM_URNA_CANDIDATO"],
                            "situacao": SITUACOES.get(
                                linha["DS_SIT_TOT_TURNO"], linha["DS_SIT_TOT_TURNO"].capitalize()
                            ),
                            "_cpf": linha.get("NR_CPF_CANDIDATO"),
                        },
                    )
                    break
        return ligados

    @staticmethod
    def _resumo_vazio() -> dict[str, Any]:
        return {
            "receitas": 0.0,
            "publico": 0.0,
            "por_fonte": Counter(),
            "repasses": 0.0,
            "doadores": Counter(),
            "despesas": 0.0,
            "por_tipo": Counter(),
            "fornecedores": Counter(),
            "nomes_fornecedores": {},
            "votos": 0,
            "bens": 0.0,
        }

    def _somar_receitas(self, ano: int, resumos: dict[str, dict]) -> None:
        for linha in tqdm(
            self.linhas("contas", ano, f"receitas_candidatos_{ano}"), desc=f"Receitas {ano}", disable=None
        ):
            resumo = resumos.get(linha["SQ_CANDIDATO"])
            if resumo is None:
                continue
            valor = _valor(linha["VR_RECEITA"])
            resumo["receitas"] += valor
            if _normalizar(linha["DS_FONTE_RECEITA"]) in FONTES_PUBLICAS:
                resumo["publico"] += valor
            resumo["por_fonte"][_fonte(linha)] += valor
            resumo["doadores"][linha["NM_DOADOR_RFB"] or linha["NM_DOADOR"] or "Não informado"] += valor

    def _somar_despesas(self, ano: int, resumos: dict[str, dict]) -> None:
        prefixo = f"despesas_contratadas_candidatos_{ano}"
        for linha in tqdm(self.linhas("contas", ano, prefixo), desc=f"Despesas {ano}", disable=None):
            resumo = resumos.get(linha["SQ_CANDIDATO"])
            if resumo is None:
                continue
            valor = _valor(linha["VR_DESPESA_CONTRATADA"])
            # Dinheiro repassado a outros candidatos não é custo desta campanha: fica separado.
            if _normalizar(linha["DS_ORIGEM_DESPESA"]).startswith(REPASSE_A_OUTROS):
                resumo["repasses"] += valor
                continue
            documento = _digitos(linha["NR_CPF_CNPJ_FORNECEDOR"])
            # CPF de pessoa física não é publicado: o fornecedor é agrupado só pelo nome.
            chave = documento if len(documento) == 14 else ""
            nome = linha["NM_FORNECEDOR_RFB"] or linha["NM_FORNECEDOR"] or "Não informado"
            resumo["despesas"] += valor
            resumo["por_tipo"][linha["DS_ORIGEM_DESPESA"].capitalize()] += valor
            resumo["fornecedores"][(chave, nome if not chave else "")] += valor
            if chave:
                resumo["nomes_fornecedores"][chave] = nome

    def _somar_votos(self, ano: int, resumos: dict[str, dict]) -> None:
        for linha in tqdm(self.linhas("votacao", ano), desc=f"Votação {ano}", disable=None):
            resumo = resumos.get(linha["SQ_CANDIDATO"])
            if resumo is not None and linha.get("NR_TURNO", "1") == "1":
                resumo["votos"] += int(linha.get("QT_VOTOS_NOMINAIS_VALIDOS") or linha.get("QT_VOTOS_NOMINAIS") or 0)

    def _somar_bens(self, ano: int, resumos: dict[str, dict]) -> None:
        for linha in self.linhas("bens", ano):
            resumo = resumos.get(linha["SQ_CANDIDATO"])
            if resumo is not None:
                resumo["bens"] += _valor(linha["VR_BEM_CANDIDATO"])

    def _patrimonio_anterior(self, candidatos: dict, resultado: dict[str, dict]) -> None:
        """Busca o patrimônio declarado na eleição geral anterior, ligando as candidaturas pelo CPF."""
        por_ano: dict[int, dict[str, str]] = defaultdict(dict)
        for pid, (ano, _, dados) in candidatos.items():
            if pid in resultado and dados.get("_cpf"):
                por_ano[ano - 4][dados["_cpf"]] = pid
        for ano, por_cpf in por_ano.items():
            try:
                sq_por_pid = {
                    por_cpf[linha["NR_CPF_CANDIDATO"]]: linha["SQ_CANDIDATO"]
                    for linha in self.linhas("candidatos", ano)
                    if linha.get("NR_CPF_CANDIDATO") in por_cpf
                }
            except OSError:
                continue
            bens: Counter = Counter()
            pid_por_sq = {sq: pid for pid, sq in sq_por_pid.items()}
            for linha in self.linhas("bens", ano):
                if linha["SQ_CANDIDATO"] in pid_por_sq:
                    bens[pid_por_sq[linha["SQ_CANDIDATO"]]] += _valor(linha["VR_BEM_CANDIDATO"])
            for pid in sq_por_pid:
                resultado[pid]["bens_anterior"] = {"ano": ano, "valor": round(bens[pid], 2)}
        for resumo in resultado.values():
            resumo.pop("_cpf", None)

    @staticmethod
    def _finalizar(resumo: dict[str, Any]) -> dict[str, Any]:
        def lista(contador: Counter, nome: str) -> list[dict[str, Any]]:
            return [{nome: chave, "valor": round(valor, 2)} for chave, valor in contador.most_common(LIMITE_LISTAS)]

        return {
            "receitas": round(resumo["receitas"], 2),
            "dinheiro_publico": round(resumo["publico"], 2),
            "receitas_por_fonte": lista(resumo["por_fonte"], "fonte"),
            "repasses_a_outros": round(resumo["repasses"], 2),
            "maiores_doadores": lista(resumo["doadores"], "nome"),
            "despesas": round(resumo["despesas"], 2),
            "despesas_por_tipo": lista(resumo["por_tipo"], "tipo"),
            "maiores_fornecedores": [
                {
                    "nome": resumo["nomes_fornecedores"].get(cnpj) or nome,
                    "cnpj": cnpj or None,
                    "valor": round(valor, 2),
                }
                for (cnpj, nome), valor in resumo["fornecedores"].most_common(LIMITE_LISTAS)
            ],
            "votos": resumo["votos"],
            "bens": round(resumo["bens"], 2),
        }
