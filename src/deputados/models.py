from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Parlamentar:
    id_fonte: str
    casa: str
    cargo: str
    nome: str
    nome_civil: str | None
    partido: str | None
    uf: str | None
    email: str | None
    url_foto: str | None
    url_perfil: str | None
    legislatura: str | None = None
    mandato_inicio: str | None = None
    mandato_fim: str | None = None
    participacao: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Despesa:
    id_fonte: str
    parlamentar_id: str
    ano: int
    mes: int
    tipo: str
    tipo_documento: str | None
    fornecedor: str | None
    cpf_cnpj: str | None
    documento: str | None
    data: str | None
    detalhamento: str | None
    valor: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Comparecimento:
    parlamentar_id: str
    sessao_id: str
    votacao_id: str
    data: str
    status: str
    status_descricao: str | None
    descricao_votacao: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
