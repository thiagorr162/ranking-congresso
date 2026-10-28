import argparse
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from deputados.build import construir_site
from deputados.collector import salvar, salvar_autorias, salvar_comparecimentos, salvar_despesas
from deputados.sources.camara import SOURCE_URL as CAMARA_URL
from deputados.sources.camara import CamaraSource
from deputados.sources.senado import (
    AUTHORSHIP_SOURCE_URL,
    EXPENSES_SOURCE_URL,
    VOTES_SOURCE_URL,
    SenadoSource,
)
from deputados.sources.senado import SOURCE_URL as SENADO_URL


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

    servir = subparsers.add_parser("servir-site", help="Inicia o servidor local do site")
    servir.add_argument("--pasta", type=Path, default=Path("dist"))
    servir.add_argument("--porta", type=int, default=8000)
    return parser


def coletar(casa: str, saida: Path, ano: int) -> int:
    fontes = []
    if casa in {"camara", "todas"}:
        fontes.append(("camara", CAMARA_URL, CamaraSource()))
    if casa in {"senado", "todas"}:
        fontes.append(("senado", SENADO_URL, SenadoSource()))

    for nome, url, fonte in fontes:
        parlamentares = fonte.parlamentares()
        destino = salvar(parlamentares, fonte=nome, source_url=url, output_dir=saida)
        print(f"{nome}: {len(parlamentares)} parlamentares -> {destino}")
        if nome == "senado":
            despesas = fonte.despesas(ano)
            destino = salvar_despesas(
                despesas,
                ano=ano,
                source_url=EXPENSES_SOURCE_URL,
                output_dir=saida,
            )
            print(f"senado: {len(despesas)} despesas -> {destino}")
            comparecimentos = fonte.comparecimentos(ano)
            destino = salvar_comparecimentos(
                comparecimentos,
                ano=ano,
                source_url=VOTES_SOURCE_URL,
                output_dir=saida,
            )
            print(f"senado: {len(comparecimentos)} registros de comparecimento -> {destino}")
            autorias = fonte.autorias((parlamentar.id_fonte for parlamentar in parlamentares), ano)
            destino = salvar_autorias(
                autorias,
                ano=ano,
                source_url=AUTHORSHIP_SOURCE_URL,
                output_dir=saida,
            )
            print(f"senado: {len(autorias)} autorias -> {destino}")
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
        destino = construir_site(ano=args.ano, data_dir=args.dados, output_dir=args.saida)
        print(f"site construído -> {destino}")
        return 0
    if args.comando == "servir-site":
        return servir_site(args.pasta, args.porta)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
