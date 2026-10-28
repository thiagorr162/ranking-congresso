import argparse
import json
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from deputados.build import construir_site
from deputados.collector import salvar, salvar_autorias, salvar_comparecimentos, salvar_despesas
from deputados.sources import camara, senado
from deputados.sources.camara import CamaraSource
from deputados.sources.senado import SenadoSource
from deputados.sources.tse import SOURCE_URL as TSE_URL
from deputados.sources.tse import TseSource


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deputados", description="Coleta dados oficiais de parlamentares")
    subparsers = parser.add_subparsers(dest="comando", required=True)
    coletar = subparsers.add_parser("coletar", help="Coleta e normaliza parlamentares")
    coletar.add_argument("--casa", choices=("camara", "senado", "todas"), default="todas")
    coletar.add_argument("--saida", type=Path, default=Path("data/raw"))
    coletar.add_argument("--ano", type=int, default=datetime.now(UTC).year)

    construir = subparsers.add_parser("construir-site", help="Gera o site estático em dist/")
    construir.add_argument("--ano", type=int, default=datetime.now(UTC).year)
    construir.add_argument("--dados", type=Path, default=Path("data/raw"))
    construir.add_argument("--saida", type=Path, default=Path("dist"))
    construir.add_argument("--eleicoes", type=Path, default=Path("eleicoes"))

    eleicoes = subparsers.add_parser("coletar-eleicoes", help="Resume dados eleitorais do TSE dos parlamentares")
    eleicoes.add_argument("--dados", type=Path, default=Path("data/raw"))
    eleicoes.add_argument("--cache", type=Path, default=Path("data/tse"))
    eleicoes.add_argument("--saida", type=Path, default=Path("eleicoes"))

    servir = subparsers.add_parser("servir-site", help="Inicia o servidor local do site")
    servir.add_argument("--pasta", type=Path, default=Path("dist"))
    servir.add_argument("--porta", type=int, default=8000)
    return parser


def coletar(casa: str, saida: Path, ano: int) -> int:
    if casa in {"camara", "todas"}:
        _coletar_casa(
            "camara",
            CamaraSource(),
            saida,
            ano,
            parlamentares_url=camara.SOURCE_URL,
            despesas_url=f"{camara.EXPENSES_SOURCE_URL}/Ano-{ano}.csv.zip",
            comparecimentos_url=camara.VOTES_SOURCE_URL,
            autorias_url=camara.AUTHORSHIP_SOURCE_URL,
        )
    if casa in {"senado", "todas"}:
        _coletar_casa(
            "senado",
            SenadoSource(),
            saida,
            ano,
            parlamentares_url=senado.SOURCE_URL,
            despesas_url=f"{senado.EXPENSES_SOURCE_URL}/{ano}",
            comparecimentos_url=senado.VOTES_SOURCE_URL,
            autorias_url=senado.AUTHORSHIP_SOURCE_URL,
        )
    return 0


def _coletar_casa(
    nome: str,
    fonte: CamaraSource | SenadoSource,
    saida: Path,
    ano: int,
    *,
    parlamentares_url: str,
    despesas_url: str,
    comparecimentos_url: str,
    autorias_url: str,
) -> None:
    parlamentares = fonte.parlamentares()
    destino = salvar(parlamentares, fonte=nome, source_url=parlamentares_url, output_dir=saida)
    print(f"{nome}: {len(parlamentares)} parlamentares -> {destino}")

    despesas = fonte.despesas(ano)
    destino = salvar_despesas(despesas, fonte=nome, ano=ano, source_url=despesas_url, output_dir=saida)
    print(f"{nome}: {len(despesas)} despesas -> {destino}")

    if isinstance(fonte, CamaraSource):
        comparecimentos = fonte.comparecimentos(ano, parlamentares)
    else:
        comparecimentos = fonte.comparecimentos(ano)
    destino = salvar_comparecimentos(
        comparecimentos, fonte=nome, ano=ano, source_url=comparecimentos_url, output_dir=saida
    )
    print(f"{nome}: {len(comparecimentos)} registros de comparecimento -> {destino}")

    autorias = fonte.autorias((parlamentar.id_fonte for parlamentar in parlamentares), ano)
    destino = salvar_autorias(autorias, fonte=nome, ano=ano, source_url=autorias_url, output_dir=saida)
    print(f"{nome}: {len(autorias)} autorias -> {destino}")


def ultima_eleicao_geral(ano: int) -> int:
    """Eleição que elegeu a legislatura em curso: em ano de eleição, os eleitos só assumem no ano seguinte."""
    anterior = ano - (ano - 2) % 4
    return anterior - 4 if anterior == ano else anterior


def coletar_eleicoes(dados: Path, cache: Path, saida: Path) -> int:
    hoje = datetime.now(UTC).date()
    # A legislatura nova só toma posse em 1º de fevereiro: em janeiro, o Congresso ainda é o anterior.
    ultima = ultima_eleicao_geral(hoje.year - (hoje.month == 1))
    # Senadores têm mandato de 8 anos: os atuais saíram das duas últimas eleições gerais.
    anos_por_casa = {"camara": [ultima], "senado": [ultima - 4, ultima]}
    fonte = TseSource(cache)
    saida.mkdir(parents=True, exist_ok=True)
    for casa, anos in anos_por_casa.items():
        parlamentares = json.loads((dados / casa / "parlamentares.json").read_text(encoding="utf-8"))["dados"]
        resumo = fonte.resumir(casa, parlamentares, anos)
        destino = saida / f"{casa}.json"
        documento = {
            "fonte": TSE_URL,
            "anos": anos,
            "gerado_em": datetime.now(UTC).isoformat(),
            "ligados": len(resumo),
            "total": len(parlamentares),
            "parlamentares": resumo,
        }
        destino.write_text(json.dumps(documento, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"{casa}: {len(resumo)} de {len(parlamentares)} parlamentares ligados ao TSE -> {destino}")
    return 0


def servir_site(pasta: Path, porta: int) -> int:
    if not (pasta / "index.html").exists():
        raise FileNotFoundError(f"Site não encontrado em {pasta}. Execute 'construir-site' primeiro.")
    handler = partial(SimpleHTTPRequestHandler, directory=str(pasta))
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), handler)
    print(f"site disponível em http://127.0.0.1:{porta}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nservidor encerrado")
    finally:
        servidor.server_close()
    return 0


def main() -> int:
    args = _parser().parse_args()
    if args.comando == "coletar":
        return coletar(args.casa, args.saida, args.ano)
    if args.comando == "construir-site":
        destino = construir_site(ano=args.ano, data_dir=args.dados, output_dir=args.saida, eleicoes_dir=args.eleicoes)
        print(f"site construído -> {destino}")
        return 0
    if args.comando == "coletar-eleicoes":
        return coletar_eleicoes(args.dados, args.cache, args.saida)
    if args.comando == "servir-site":
        return servir_site(args.pasta, args.porta)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
