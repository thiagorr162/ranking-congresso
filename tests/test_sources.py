import csv
import io
import zipfile

from deputados.models import Parlamentar
from deputados.sources.camara import CamaraSource, _em_exercicio, _periodos_exercicio
from deputados.sources.senado import SenadoSource


def test_normaliza_e_pagina_camara() -> None:
    chamadas = []

    def fake_get(path, params=None):
        if path == "deputados/123/historico":
            return {
                "dados": [
                    {
                        "dataHora": "2023-02-01T12:05",
                        "idLegislatura": 57,
                        "situacao": "Exercício",
                        "condicaoEleitoral": "Titular",
                    }
                ]
            }
        if path == "deputados/123":
            return {"dados": {"nomeCivil": "MARIA DA SILVA"}}
        chamadas.append((path, params))
        return {
            "dados": [
                {
                    "id": 123,
                    "nome": "Maria Silva",
                    "siglaPartido": "ABC",
                    "siglaUf": "SP",
                    "idLegislatura": 57,
                    "urlFoto": "https://example.test/foto.jpg",
                    "email": "dep.maria@camara.leg.br",
                }
            ]
        }

    deputados = CamaraSource(fake_get).parlamentares()

    assert len(chamadas) == 1
    assert deputados[0].id_fonte == "123"
    assert deputados[0].cargo == "deputado_federal"
    assert deputados[0].legislatura == "57"
    assert deputados[0].exercicio_inicio == "2023-02-01"
    assert deputados[0].participacao == "Titular"
    assert deputados[0].nome_civil == "MARIA DA SILVA"


def test_normaliza_senado_com_um_parlamentar() -> None:
    def fake_get(path):
        if path == "senador/456/mandatos":
            return {
                "MandatoParlamentar": {
                    "Parlamentar": {
                        "Mandatos": {
                            "Mandato": {
                                "Exercicios": {
                                    "Exercicio": [
                                        {"DataInicio": "2023-02-01", "DataFim": "2024-05-10"},
                                        {"DataInicio": "2024-09-01"},
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        assert path == "senador/lista/atual"
        return {
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {
                    "Parlamentar": {
                        "IdentificacaoParlamentar": {
                            "CodigoParlamentar": "456",
                            "NomeParlamentar": "João Souza",
                            "NomeCompletoParlamentar": "João da Silva Souza",
                            "SiglaPartidoParlamentar": "XYZ",
                            "UfParlamentar": "MG",
                            "EmailParlamentar": "sen.joao@senado.leg.br",
                            "UrlFotoParlamentar": "https://example.test/foto.jpg",
                            "UrlPaginaParlamentar": "https://example.test/perfil",
                        },
                        "Mandato": {
                            "DescricaoParticipacao": "Titular",
                            "PrimeiraLegislaturaDoMandato": {
                                "NumeroLegislatura": "57",
                                "DataInicio": "2023-02-01",
                                "DataFim": "2027-01-31",
                            },
                            "SegundaLegislaturaDoMandato": {
                                "NumeroLegislatura": "58",
                                "DataInicio": "2027-02-01",
                                "DataFim": "2031-01-31",
                            },
                        },
                    }
                }
            }
        }

    senadores = SenadoSource(fake_get).parlamentares()

    assert len(senadores) == 1
    assert senadores[0].nome_civil == "João da Silva Souza"
    assert senadores[0].legislatura == "57,58"
    assert senadores[0].mandato_fim == "2031-01-31"
    assert senadores[0].exercicio_inicio == "2024-09-01"


def test_normaliza_despesa_sem_categoria() -> None:
    despesa = SenadoSource._normalizar_despesa(
        {
            "id": 10,
            "codSenador": 456,
            "ano": 2026,
            "mes": 3,
            "tipoDespesa": None,
            "tipoDocumento": "Nota Fiscal",
            "fornecedor": "Fornecedor Teste",
            "cpfCnpj": "00.000.000/0001-00",
            "documento": None,
            "data": "2026-03-10",
            "detalhamento": "Serviço prestado",
            "valorReembolsado": 150.5,
        }
    )

    assert despesa.tipo == "Não informado"
    assert despesa.cpf_cnpj == "00.000.000/0001-00"
    assert despesa.detalhamento == "Serviço prestado"
    assert despesa.valor == 150.5


def test_coleta_autorias_por_senador() -> None:
    chamadas = []

    def fake_get(path, params):
        chamadas.append((path, params))
        return [
            {
                "id": 99,
                "identificacao": "PL 1/2026",
                "tipoDocumento": "Projeto de Lei Ordinária",
                "ementa": "Dispõe sobre algo.",
                "dataApresentacao": "2026-02-01",
                "situacaoAtual": "AGUARDANDO RELATOR",
                "tramitando": "Sim",
                "autoria": "Senador João Souza (XYZ/MG)",
                "urlDocumento": "https://example.test/doc",
            }
        ]

    autorias = SenadoSource(fake_get).autorias(["456"], 2026)

    assert chamadas[0][0] == "processo"
    assert chamadas[0][1]["codigoParlamentarAutor"] == "456"
    assert chamadas[0][1]["dataInicioApresentacao"] == "2026-01-01"
    assert autorias[0].parlamentar_id == "456"
    assert autorias[0].tramitando is True


def test_periodos_de_exercicio_respeitam_afastamentos() -> None:
    historico = [
        {"dataHora": "2023-02-01T00:00", "idLegislatura": 57, "situacao": None},
        {"dataHora": "2023-02-02T11:17", "idLegislatura": 57, "situacao": "Exercício"},
        {"dataHora": "2024-03-12T09:50", "idLegislatura": 57, "situacao": "SUPLENCIA"},
        {"dataHora": "2024-03-21T17:48", "idLegislatura": 57, "situacao": "Exercício"},
        {"dataHora": "2025-01-10T10:00", "idLegislatura": 57, "situacao": "Exercício"},
        {"dataHora": "2019-02-01T10:00", "idLegislatura": 56, "situacao": "Exercício"},
    ]

    periodos = _periodos_exercicio(historico, "57")

    assert periodos == (("2023-02-02T11:17", "2024-03-12T09:50"), ("2024-03-21T17:48", None))
    assert _em_exercicio(periodos, "2024-03-15T15:00:00") is False
    assert _em_exercicio(periodos, "2026-05-05T15:00:00") is True


def test_cota_da_camara_usa_id_da_api_e_desambigua_documentos() -> None:
    campos = [
        "ideCadastro",
        "numAno",
        "numMes",
        "txtDescricao",
        "indTipoDocumento",
        "txtFornecedor",
        "txtCNPJCPF",
        "txtNumero",
        "datEmissao",
        "txtDescricaoEspecificacao",
        "vlrLiquido",
        "urlDocumento",
        "txtPassageiro",
        "txtTrecho",
        "ideDocumento",
        "numLote",
    ]
    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=campos, delimiter=";")
    escritor.writeheader()
    linha = dict.fromkeys(campos, "")
    linha |= {
        "ideCadastro": "123",
        "numAno": "2026",
        "numMes": "3",
        "txtDescricao": "PASSAGEM AÉREA",
        "indTipoDocumento": "4",
        "vlrLiquido": "117.72",
        "ideDocumento": "9",
        "txtPassageiro": "FULANO",
    }
    escritor.writerow(linha)
    escritor.writerow(linha)
    escritor.writerow(linha | {"ideCadastro": ""})
    arquivo = io.BytesIO()
    with zipfile.ZipFile(arquivo, "w") as zip_file:
        zip_file.writestr("Ano-2026.csv", texto.getvalue())

    despesas = CamaraSource(get_quota_bytes=lambda path: arquivo.getvalue()).despesas(2026)

    assert [despesa.id_fonte for despesa in despesas] == ["9", "9-2"]
    assert despesas[0].parlamentar_id == "123"
    assert despesas[0].tipo_documento == "Nota Fiscal Eletrônica"
    assert despesas[0].valor == 117.72
    assert despesas[0].passageiro == "FULANO"


def test_faltas_da_camara_so_contam_sessoes_em_exercicio() -> None:
    arquivos = {
        "eventos/json/eventos-2026.json": {
            "dados": [
                {
                    "id": 1,
                    "dataHoraInicio": "2026-03-01T15:00:00",
                    "descricaoTipo": "Sessão Deliberativa",
                    "situacao": "Encerrada",
                },
                {
                    "id": 2,
                    "dataHoraInicio": "2026-05-01T15:00:00",
                    "descricaoTipo": "Sessão Deliberativa",
                    "situacao": "Encerrada",
                },
                {
                    "id": 3,
                    "dataHoraInicio": "2026-05-02T15:00:00",
                    "descricaoTipo": "Audiência Pública",
                    "situacao": "Encerrada",
                },
            ]
        },
        "eventosPresencaDeputados/json/eventosPresencaDeputados-2026.json": {
            "dados": [{"idEvento": 2, "idDeputado": 7}]
        },
    }
    deputado = Parlamentar(
        id_fonte="7",
        casa="camara",
        cargo="deputado_federal",
        nome="Teste",
        nome_civil=None,
        partido=None,
        uf=None,
        email=None,
        url_foto=None,
        url_perfil=None,
        periodos_exercicio=(("2026-04-01T00:00", None),),
    )

    registros = CamaraSource(get_file_json=arquivos.__getitem__).comparecimentos(2026, [deputado])

    assert [(registro.sessao_id, registro.status) for registro in registros] == [("2", "Presente")]


def test_autorias_da_camara_contam_so_proponentes_do_ano() -> None:
    arquivos = {
        "proposicoesAutores/json/proposicoesAutores-2026.json": {
            "dados": [
                {"idProposicao": 10, "idDeputadoAutor": 7, "tipoAutor": "Deputado(a)", "proponente": "1"},
                {"idProposicao": 11, "idDeputadoAutor": 7, "tipoAutor": "Deputado(a)", "proponente": "0"},
                {"idProposicao": 12, "idDeputadoAutor": 7, "tipoAutor": "Deputado(a)", "proponente": "1"},
                {"idProposicao": 10, "idDeputadoAutor": 8, "tipoAutor": "Deputado(a)", "proponente": "1"},
            ]
        },
        "proposicoes/json/proposicoes-2026.json": {
            "dados": [
                {
                    "id": "10",
                    "siglaTipo": "PL",
                    "numero": "1",
                    "ano": "2026",
                    "dataApresentacao": "2026-02-01T10:00",
                    "ultimoStatus": {"descricaoSituacao": "Arquivada"},
                },
                {"id": "11", "siglaTipo": "PRL", "numero": "1", "ano": "2026", "dataApresentacao": "2026-02-01T10:00"},
                {"id": "12", "siglaTipo": "PL", "numero": "2", "ano": "2026", "dataApresentacao": "2005-02-01T10:00"},
            ]
        },
    }

    autorias = CamaraSource(get_file_json=arquivos.__getitem__).autorias(["7"], 2026)

    assert len(autorias) == 1
    assert autorias[0].identificacao == "PL 1/2026"
    assert autorias[0].tipo == "Projeto de Lei Ordinária"
    assert autorias[0].tramitando is False


def test_tse_liga_parlamentar_a_candidatura_eleita(tmp_path) -> None:
    from deputados.sources.tse import TseSource

    candidatos = [
        {
            "DS_CARGO": "SENADOR",
            "NR_TURNO": "1",
            "SG_UF": "MG",
            "NM_CANDIDATO": "JOÃO DA SILVA SOUZA",
            "NM_URNA_CANDIDATO": "JOÃO SOUZA",
            "SQ_CANDIDATO": "18",
            "SG_PARTIDO": "XYZ",
            "DS_SIT_TOT_TURNO": "ELEITO",
            "NR_CPF_CANDIDATO": "1",
        },
        {
            "DS_CARGO": "SENADOR",
            "NR_TURNO": "1",
            "SG_UF": "MG",
            "NM_CANDIDATO": "JOÃO DA SILVA SOUZA",
            "NM_URNA_CANDIDATO": "JOÃO SOUZA",
            "SQ_CANDIDATO": "22",
            "SG_PARTIDO": "XYZ",
            "DS_SIT_TOT_TURNO": "NÃO ELEITO",
            "NR_CPF_CANDIDATO": "1",
        },
    ]
    fonte = TseSource(tmp_path)
    fonte.linhas = lambda tipo, ano, prefixo="": iter(
        [linha for linha in candidatos if linha["SQ_CANDIDATO"].startswith(str(ano)[2:])]
    )
    parlamentar = {"id_fonte": "456", "nome": "João Souza", "nome_civil": "João da Silva Souza", "uf": "MG"}

    ligados = fonte._ligar("senado", [parlamentar], [2018, 2022])

    ano, sq, dados = ligados["456"]
    assert (ano, sq) == (2018, "18")
    assert dados["situacao"] == "Eleito"


def test_ultima_eleicao_geral() -> None:
    from deputados.cli import ultima_eleicao_geral

    assert ultima_eleicao_geral(2025) == 2022
    assert ultima_eleicao_geral(2026) == 2022
    assert ultima_eleicao_geral(2027) == 2026
