from deputados.build import _agregar_frequencia


def test_falta_conta_uma_vez_por_sessao() -> None:
    registros = [
        {
            "parlamentar_id": "1",
            "sessao_id": "10",
            "votacao_id": "100",
            "data": "2026-03-01",
            "status": "NCom",
            "status_descricao": "Não compareceu",
            "descricao_votacao": "Votação A",
        },
        {
            "parlamentar_id": "1",
            "sessao_id": "10",
            "votacao_id": "101",
            "data": "2026-03-01",
            "status": "NCom",
            "status_descricao": "Não compareceu",
            "descricao_votacao": "Votação B",
        },
        {
            "parlamentar_id": "1",
            "sessao_id": "11",
            "votacao_id": "102",
            "data": "2026-03-02",
            "status": "Sim",
            "status_descricao": None,
            "descricao_votacao": "Votação C",
        },
    ]

    frequencia = _agregar_frequencia(registros)["1"]

    assert frequencia["faltas"] == 1
    assert frequencia["presencas"] == 1
    assert frequencia["total_sessoes"] == 2
    assert frequencia["percentual_presenca"] == 50.0
