from deputados.sources.camara import CamaraSource
from deputados.sources.senado import SenadoSource


def test_normaliza_e_pagina_camara() -> None:
    chamadas = []

    def fake_get(path, params):
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


def test_normaliza_senado_com_um_parlamentar() -> None:
    def fake_get(path):
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
