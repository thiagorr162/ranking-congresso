import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

PRESENT_STATUSES = {"Sim", "Não", "Abstenção", "Votou", "P-NRV", "Presidente (art. 51 RISF)"}
VOTE_STATUSES = {"Sim", "Não", "Abstenção", "Votou"}
JUSTIFIED_STATUSES = {"AP", "LS", "MIS", "LP", "LAP"}
TIPOS_PROJETO = {
    "Projeto de Lei Ordinária",
    "Projeto de Lei Complementar",
    "Proposta de Emenda à Constituição",
    "Projeto de Decreto Legislativo",
    "Projeto de Resolução",
    "Projeto de Resolução do Senado",
}
STATUS_LABELS = {
    "AP": "Atividade parlamentar",
    "LS": "Licença-saúde",
    "MIS": "Missão oficial",
    "LP": "Licença particular",
    "LAP": "Licença-paternidade ou adoção",
    "NCom": "Não compareceu",
    "P-NRV": "Presente, sem voto registrado",
}


def _carregar(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}. Execute a coleta primeiro.")
    return json.loads(path.read_text(encoding="utf-8"))


def _agregar_frequencia(registros: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    por_parlamentar: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for registro in registros:
        por_parlamentar[registro["parlamentar_id"]][registro["sessao_id"]].append(registro)

    resultado = {}
    for parlamentar_id, sessoes in por_parlamentar.items():
        registros_parlamentar = [registro for votos in sessoes.values() for registro in votos]
        detalhes = []
        totais = {
            "presencas": 0,
            "faltas": 0,
            "justificadas": 0,
            "nao_classificadas": 0,
            "votos_registrados": sum(item["status"] in VOTE_STATUSES for item in registros_parlamentar),
            "votacoes_total": len(registros_parlamentar),
            "presente_sem_voto": sum(item["status"] == "P-NRV" for item in registros_parlamentar),
        }
        for sessao_id, votos in sessoes.items():
            statuses = {voto["status"] for voto in votos}
            if statuses & PRESENT_STATUSES:
                classificacao = "presenca"
                totais["presencas"] += 1
            elif "NCom" in statuses:
                classificacao = "falta"
                totais["faltas"] += 1
            elif statuses & JUSTIFIED_STATUSES:
                classificacao = "justificada"
                totais["justificadas"] += 1
            else:
                classificacao = "nao_classificada"
                totais["nao_classificadas"] += 1

            status = next(iter(statuses))
            descricao = next((voto.get("status_descricao") for voto in votos if voto.get("status_descricao")), None)
            detalhes.append(
                {
                    "sessao_id": sessao_id,
                    "data": votos[0]["data"],
                    "classificacao": classificacao,
                    "status": status,
                    "motivo": descricao or STATUS_LABELS.get(status, status),
                    "votacoes": len(votos),
                }
            )
        total = totais["presencas"] + totais["faltas"] + totais["justificadas"]
        resultado[parlamentar_id] = {
            **totais,
            "total_sessoes": total,
            "percentual_presenca": round(totais["presencas"] / total * 100, 1) if total else 0,
            "sessoes": sorted(detalhes, key=lambda item: item["data"], reverse=True),
        }
    return resultado


def _agregar_projetos(
    parlamentares: list[dict[str, Any]],
    autorias: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    por_parlamentar: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for autoria in autorias:
        por_parlamentar[autoria["parlamentar_id"]][autoria["id_fonte"]] = autoria

    resultado = {}
    for parlamentar in parlamentares:
        parlamentar_id = parlamentar["id_fonte"]
        registros = list(por_parlamentar[parlamentar_id].values())
        projetos = sorted(
            (item for item in registros if item["tipo"] in TIPOS_PROJETO),
            key=lambda item: item.get("data") or "",
            reverse=True,
        )
        resultado[parlamentar_id] = {
            "projetos": len(projetos),
            "projetos_tramitando": sum(item["tramitando"] for item in projetos),
            "autorias": len(registros),
            "lista": projetos,
        }
    return resultado


def _agregar(
    parlamentares: list[dict[str, Any]],
    despesas: list[dict[str, Any]],
    frequencias: dict[str, dict[str, Any]],
    projetos: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    por_senador: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for despesa in despesas:
        por_senador[despesa["parlamentar_id"]].append(despesa)

    ranking = []
    for senador in parlamentares:
        registros = por_senador[senador["id_fonte"]]
        total = sum(item["valor"] for item in registros)
        maior = max(registros, key=lambda item: item["valor"], default=None)
        por_fornecedor: dict[str, float] = defaultdict(float)
        por_categoria: dict[str, float] = defaultdict(float)
        for item in registros:
            por_fornecedor[item["fornecedor"] or "Não informado"] += item["valor"]
            por_categoria[item["tipo"]] += item["valor"]

        fornecedor, valor_fornecedor = max(por_fornecedor.items(), key=lambda item: item[1], default=(None, 0.0))
        categoria, valor_categoria = max(por_categoria.items(), key=lambda item: item[1], default=(None, 0.0))
        frequencia = frequencias.get(
            senador["id_fonte"],
            {
                "presencas": 0,
                "faltas": 0,
                "justificadas": 0,
                "nao_classificadas": 0,
                "total_sessoes": 0,
                "percentual_presenca": 0,
                "votos_registrados": 0,
                "votacoes_total": 0,
                "presente_sem_voto": 0,
                "sessoes": [],
            },
        )
        ranking.append(
            {
                "id": senador["id_fonte"],
                "nome": senador["nome"],
                "partido": senador["partido"],
                "uf": senador["uf"],
                "foto": senador["url_foto"],
                "perfil_oficial": senador["url_perfil"],
                "total_gasto": round(total, 2),
                "quantidade_despesas": len(registros),
                "maior_despesa": round(maior["valor"], 2) if maior else 0,
                "maior_despesa_fornecedor": maior["fornecedor"] if maior else None,
                "maior_despesa_tipo": maior["tipo"] if maior else None,
                "fornecedor_principal": fornecedor,
                "fornecedor_principal_valor": round(valor_fornecedor, 2),
                "concentracao_fornecedor": round(valor_fornecedor / total * 100, 1) if total else 0,
                "categoria_principal": categoria,
                "categoria_principal_valor": round(valor_categoria, 2),
                "presencas": frequencia["presencas"],
                "faltas": frequencia["faltas"],
                "faltas_justificadas": frequencia["justificadas"],
                "total_sessoes": frequencia["total_sessoes"],
                "percentual_presenca": frequencia["percentual_presenca"],
                "votos_registrados": frequencia["votos_registrados"],
                "votacoes_total": frequencia["votacoes_total"],
                "presente_sem_voto": frequencia["presente_sem_voto"],
                "participacao": senador.get("participacao"),
                "exercicio_inicio": senador.get("exercicio_inicio"),
                **{chave: valor for chave, valor in projetos[senador["id_fonte"]].items() if chave != "lista"},
            }
        )
    return ranking


def construir_site(*, ano: int, data_dir: Path, output_dir: Path) -> Path:
    senadores_doc = _carregar(data_dir / "senado" / "parlamentares.json")
    despesas_doc = _carregar(data_dir / "senado" / f"despesas-{ano}.json")
    comparecimentos_doc = _carregar(data_dir / "senado" / f"comparecimentos-{ano}.json")
    autorias_doc = _carregar(data_dir / "senado" / f"autorias-{ano}.json")
    frequencias = _agregar_frequencia(comparecimentos_doc["dados"])
    projetos = _agregar_projetos(senadores_doc["dados"], autorias_doc["dados"])
    ranking = _agregar(senadores_doc["dados"], despesas_doc["dados"], frequencias, projetos)

    source_dir = Path(__file__).parents[2] / "web"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_dir, output_dir)
    data_output = output_dir / "data"
    data_output.mkdir()
    documento = {
        "ano": ano,
        "atualizado_em": despesas_doc["coletado_em"],
        "fonte": despesas_doc["url_origem"],
        "total_senadores": len(ranking),
        "total_gasto": round(sum(item["total_gasto"] for item in ranking), 2),
        "projetos_fonte": autorias_doc["url_origem"],
        "senadores": ranking,
    }
    (data_output / "senadores.json").write_text(
        json.dumps(documento, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    detalhes_output = data_output / "senadores"
    detalhes_output.mkdir()
    agregados = {item["id"]: item for item in ranking}
    despesas_por_senador: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for despesa in despesas_doc["dados"]:
        despesas_por_senador[despesa["parlamentar_id"]].append(despesa)
    for senador in senadores_doc["dados"]:
        senador_id = senador["id_fonte"]
        pasta_senador = detalhes_output / senador_id
        pasta_senador.mkdir()
        base = {
            "ano": ano,
            "atualizado_em": despesas_doc["coletado_em"],
            "fonte": despesas_doc["url_origem"],
            "parlamentar": senador,
            "resumo": agregados[senador_id],
        }
        arquivos = {
            "perfil.json": base,
            "projetos.json": {
                **base,
                "fonte": autorias_doc["url_origem"],
                "projetos": projetos[senador_id]["lista"],
            },
            "frequencia.json": {
                **base,
                "frequencia": frequencias.get(senador_id, {"sessoes": []}),
            },
            "despesas.json": {
                **base,
                "despesas": sorted(
                    despesas_por_senador[senador_id],
                    key=lambda item: (item.get("data") or "", item["valor"]),
                    reverse=True,
                ),
            },
        }
        for nome, conteudo in arquivos.items():
            (pasta_senador / nome).write_text(
                json.dumps(conteudo, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
    return output_dir / "index.html"
