from deputados.build import _agregar_frequencia, _agregar_projetos, _versionar_arquivos


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


def test_versiona_scripts_e_estilos(tmp_path) -> None:
    (tmp_path / "app.js").write_text("console.log(1)")
    (tmp_path / "styles.css").write_text("body{}")
    (tmp_path / "index.html").write_text(
        '<link href="styles.css" /><script src="app.js"></script><a href="perfil.html">x</a>'
    )

    _versionar_arquivos(tmp_path)
    html = (tmp_path / "index.html").read_text()

    assert 'href="styles.css?v=' in html
    assert 'src="app.js?v=' in html
    assert 'href="perfil.html"' in html
