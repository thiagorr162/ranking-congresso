import json
from pathlib import Path
import re

import requests
from bs4 import BeautifulSoup

# Caminho dos arquivos JSON salvos anteriormente
input_path = Path("data/deputados")
output_path = Path("data/deputados/atualizado")
output_path.mkdir(parents=True, exist_ok=True)

# Headers para evitar bloqueio por User-Agent
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

# Função para extrair informações detalhadas do HTML da página do deputado


# Processa cada arquivo JSON
for json_file in input_path.rglob("*.json"):
    with json_file.open("r", encoding="utf-8") as f:
        deputado_data = json.load(f)

    # URL da página do deputado
    url = deputado_data["url"]

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    info = {}

    # Extraindo informações detalhadas do deputado
    info["nome"] = soup.find("span", string="Nome Civil:").find_next_sibling(string=True).strip().title()
    info["partido"] = soup.find("span", string="Partido:").find_next_sibling(string=True).strip().title()
    info["email"] = soup.find("a", class_="email")["href"].replace("mailto:", "")
    info["telefone"] = soup.find("span", string="Telefone:").find_next_sibling(string=True).strip()

    info["nascimento"] = soup.find("span", string="Data de Nascimento:").find_next_sibling(string=True).strip()
    info["naturalidade"] = soup.find("span", string="Naturalidade:").find_next_sibling(string=True).strip()

    info["endereco"] = soup.find("span", string="Endereço:").find_next_sibling(string=True).strip().replace("\n", "")
    info["endereco"] = re.sub(" +", " ", info["endereco"])

    # Extraindo informações de atuação para 2024
    atuacao = {}

    # Propostas legislativas - de sua autoria
    atuacao["propostas_autoria"] = int(
        soup.find("span", class_="atuacao__tipo", string="de sua autoria").find_next("a", class_="atuacao__quantidade").get_text(strip=True)
    )

#     # Propostas legislativas - relatadas
    atuacao["propostas_relatadas"] = int(
        soup.find("span", class_="atuacao__tipo", string="relatadas").find_next("a", class_="atuacao__quantidade").get_text(strip=True)
    )

#     # Votações nominais - em Plenário
    atuacao["votacoes_plenario"] = int(
        soup.find("span", class_="atuacao__tipo", string="em Plenário").find_next("a", class_="atuacao__quantidade").get_text(strip=True)
    )
    
    presenca = {}
    presenca["presencas"] = soup.find("span", class_="presencas__label").find_next("span", class_="d-none d-inline-lg", string=" na Câmara").find_next("span", class_="presencas__qtd").get_text().strip()

    presenca["ausencia_justificada"] = soup.find("span", class_="presencas__label", string="Ausências justificadas").find_next("span", class_="presencas__qtd").get_text().strip()

    presenca["ausencia_nao_justificada"] = soup.find("span", class_="presencas__label", string="Ausências não justificadas").find_next("span", class_="presencas__qtd").get_text().strip()

    # Adicionando o dicionário de atuação de 2024 ao dicionário principal
    info["atuacao-2024"] = atuacao
    info["presenca-2024"] = presenca




    breakpoint()

