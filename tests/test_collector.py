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
