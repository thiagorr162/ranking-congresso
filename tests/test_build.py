from deputados.build import _agregar_frequencia, _agregar_projetos


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


def test_projetos_contam_so_proposicoes_e_sem_duplicar() -> None:
    def autoria(id_fonte, tipo, tramitando=True):
        return {
            "parlamentar_id": "1",
            "id_fonte": id_fonte,
            "tipo": tipo,
            "data": "2026-03-01",
            "tramitando": tramitando,
        }

    registros = [
        autoria("1", "Projeto de Lei Ordinária"),
        autoria("1", "Projeto de Lei Ordinária"),
        autoria("2", "Proposta de Emenda à Constituição", tramitando=False),
        autoria("3", "Requerimento"),
    ]

    resultado = _agregar_projetos([{"id_fonte": "1"}, {"id_fonte": "2"}], registros)

    assert resultado["1"]["projetos"] == 2
    assert resultado["1"]["projetos_tramitando"] == 1
    assert resultado["1"]["autorias"] == 3
    assert resultado["2"]["projetos"] == 0
