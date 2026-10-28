import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from deputados.models import Autoria, Comparecimento, Despesa, Parlamentar


def salvar(
    parlamentares: Iterable[Parlamentar],
    *,
    fonte: str,
    source_url: str,
    output_dir: Path,
) -> Path:
    registros = [parlamentar.to_dict() for parlamentar in parlamentares]
    destino = output_dir / fonte / "parlamentares.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        "fonte": fonte,
        "url_origem": source_url,
        "coletado_em": datetime.now(UTC).isoformat(),
        "total": len(registros),
        "dados": registros,
    }
    destino.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def salvar_despesas(despesas: Iterable[Despesa], *, ano: int, source_url: str, output_dir: Path) -> Path:
    registros = [despesa.to_dict() for despesa in despesas]
    destino = output_dir / "senado" / f"despesas-{ano}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        "fonte": "senado",
        "tipo": "despesas_ceaps",
        "ano": ano,
        "url_origem": f"{source_url}/{ano}",
        "coletado_em": datetime.now(UTC).isoformat(),
        "total": len(registros),
        "dados": registros,
    }
    destino.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def salvar_comparecimentos(registros: Iterable[Comparecimento], *, ano: int, source_url: str, output_dir: Path) -> Path:
    dados = [registro.to_dict() for registro in registros]
    destino = output_dir / "senado" / f"comparecimentos-{ano}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        "fonte": "senado",
        "tipo": "comparecimentos_votacoes",
        "ano": ano,
        "url_origem": source_url,
        "coletado_em": datetime.now(UTC).isoformat(),
        "total": len(dados),
        "dados": dados,
    }
    destino.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def salvar_autorias(registros: Iterable[Autoria], *, ano: int, source_url: str, output_dir: Path) -> Path:
    dados = [registro.to_dict() for registro in registros]
    destino = output_dir / "senado" / f"autorias-{ano}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        "fonte": "senado",
        "tipo": "autorias",
        "ano": ano,
        "url_origem": source_url,
        "coletado_em": datetime.now(UTC).isoformat(),
        "total": len(dados),
        "dados": dados,
    }
    destino.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino
