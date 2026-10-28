import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deputados.models import Autoria, Comparecimento, Despesa, Parlamentar


def _gravar(destino: Path, documento: dict[str, Any]) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def _salvar_ano(
    registros: list[dict[str, Any]],
    *,
    fonte: str,
    tipo: str,
    arquivo: str,
    ano: int,
    source_url: str,
    output_dir: Path,
) -> Path:
    documento = {
        "fonte": fonte,
        "tipo": tipo,
        "ano": ano,
        "url_origem": source_url,
        "coletado_em": datetime.now(UTC).isoformat(),
        "total": len(registros),
        "dados": registros,
    }
    return _gravar(output_dir / fonte / f"{arquivo}-{ano}.json", documento)


def salvar(
    parlamentares: Iterable[Parlamentar],
    *,
    fonte: str,
    source_url: str,
    output_dir: Path,
) -> Path:
    registros = [parlamentar.to_dict() for parlamentar in parlamentares]
    documento = {
        "fonte": fonte,
        "url_origem": source_url,
        "coletado_em": datetime.now(UTC).isoformat(),
        "total": len(registros),
        "dados": registros,
    }
    return _gravar(output_dir / fonte / "parlamentares.json", documento)


def salvar_despesas(
    despesas: Iterable[Despesa],
    *,
    fonte: str,
    ano: int,
    source_url: str,
    output_dir: Path,
) -> Path:
    return _salvar_ano(
        [despesa.to_dict() for despesa in despesas],
        fonte=fonte,
        tipo="despesas_cota_parlamentar",
        arquivo="despesas",
        ano=ano,
        source_url=source_url,
        output_dir=output_dir,
    )


def salvar_comparecimentos(
    registros: Iterable[Comparecimento],
    *,
    fonte: str,
    ano: int,
    source_url: str,
    output_dir: Path,
) -> Path:
    return _salvar_ano(
        [registro.to_dict() for registro in registros],
        fonte=fonte,
        tipo="comparecimentos",
        arquivo="comparecimentos",
        ano=ano,
        source_url=source_url,
        output_dir=output_dir,
    )


def salvar_autorias(
    registros: Iterable[Autoria],
    *,
    fonte: str,
    ano: int,
    source_url: str,
    output_dir: Path,
) -> Path:
    return _salvar_ano(
        [registro.to_dict() for registro in registros],
        fonte=fonte,
        tipo="autorias",
        arquivo="autorias",
        ano=ano,
        source_url=source_url,
        output_dir=output_dir,
    )
