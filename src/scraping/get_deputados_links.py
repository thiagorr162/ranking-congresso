import argparse
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configuração do argparse para receber os parâmetros de linha de comando
parser = argparse.ArgumentParser(description="Coleta de dados de deputados da Câmara dos Deputados")
parser.add_argument("--partido", type=str, default="", help="Sigla do partido")
parser.add_argument("--legislatura", type=str, default="57", help="Número da legislatura")
parser.add_argument("--sexo", type=str, default="", choices=["M", "F"], help="Sexo do deputado (M ou F)")

args = parser.parse_args()

# Define o caminho de saída para os arquivos JSON
output_path = Path(f"data/deputados/links/{args.legislatura}")
output_path.mkdir(parents=True, exist_ok=True)

# Headers para evitar bloqueio por User-Agent
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

# Inicializa o número da página
pagina = 1

while True:
    # URL de base da Câmara dos Deputados com os parâmetros recebidos e a página atual
    base_url = (
        f"https://www.camara.leg.br/deputados/quem-sao/resultado?"
        f"search=&partido={args.partido}&uf=&legislatura={args.legislatura}&sexo={args.sexo}&pagina={pagina}"
    )

    # Faz a requisição e cria o objeto BeautifulSoup
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    # Extrai os links e nomes dos deputados
    deputados_links = soup.select('ul.lista-resultados a[href^="https://www.camara.leg.br/deputados/"]')

    # Verifica se não há mais deputados para processar
    if not deputados_links:
        print(f"Todas as páginas processadas. Última página: {pagina - 1}")
        break

    # Para cada link de deputado, extrai o ID e salva em um JSON separado
    for link in deputados_links:
        deputado_name = link.get_text(strip=True)
        deputado_url = link["href"]
        deputado_id = deputado_url.split("/")[-1]

        deputado_data = {"name": deputado_name, "url": deputado_url}

        # Define o caminho do arquivo JSON usando o ID do deputado
        output_file = output_path / f"{deputado_id}.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(deputado_data, f, ensure_ascii=False, indent=2)

    print(f"Página {pagina} processada com sucesso.")
    # Incrementa o número da página para coletar a próxima página
    pagina += 1

print("Dados dos deputados salvos em arquivos JSON individuais na pasta:", output_path)
