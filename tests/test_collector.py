import json

from deputados.collector import salvar
from deputados.models import Parlamentar


def test_salva_envelope_com_metadados(tmp_path) -> None:
    parlamentar = Parlamentar(
        id_fonte="1",
        casa="camara",
        cargo="deputado_federal",
        nome="Pessoa Teste",
        nome_civil=None,
        partido="ABC",
        uf="DF",
        email=None,
        url_foto=None,
        url_perfil=None,
    )

    destino = salvar([parlamentar], fonte="camara", source_url="https://example.test", output_dir=tmp_path)
    documento = json.loads(destino.read_text(encoding="utf-8"))

    assert documento["fonte"] == "camara"
    assert documento["total"] == 1
    assert documento["dados"][0]["id_fonte"] == "1"


def test_espera_mais_quando_a_api_pede_calma() -> None:
    from email.message import Message
    from urllib.error import HTTPError

    from deputados.http import _espera

    cabecalhos = Message()
    cabecalhos["Retry-After"] = "7"
    assert _espera(HTTPError("u", 429, "Too Many Requests", cabecalhos, None), 1) == 7
    assert _espera(HTTPError("u", 429, "Too Many Requests", Message(), None), 2) == 30
    assert _espera(TimeoutError(), 2) == 10
    assert _espera(TimeoutError(), 6) == 60


def test_retoma_download_cortado_no_meio(monkeypatch) -> None:
    from http.client import IncompleteRead

    from deputados import http

    pedidos = []

    class Resposta:
        def __init__(self, status, corpo, corta=False):
            self.status, self.corpo, self.corta = status, corpo, corta

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            if self.corta:
                raise IncompleteRead(self.corpo, 10)
            return self.corpo

    def fake_urlopen(pedido, timeout):
        pedidos.append(pedido.get_header("Range"))
        if len(pedidos) == 1:
            return Resposta(200, b'{"dados": [1, ', corta=True)
        return Resposta(206, b"2]}")

    monkeypatch.setattr(http, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", lambda segundos: None)

    assert http.JsonClient("https://example.test", intervalo=0).get("arquivo.json") == {"dados": [1, 2]}
    assert pedidos == [None, "bytes=14-"]
