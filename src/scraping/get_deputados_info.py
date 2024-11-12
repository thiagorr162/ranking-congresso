import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def padronizar_recursos(recursos):
    recursos_padronizados = {}

    for chave, valor in recursos.items():
        chave_limpa = chave.replace("?", "").strip()  # Remove o "?" e espaços extras

        # Padroniza os valores com base em padrões
        if "pessoal de gabinete" in chave_limpa.lower():
            # Extrai números do texto (total e ativos)
            numeros = [int(s) for s in re.findall(r"\d+", valor)]
            recursos_padronizados[chave_limpa] = {
                "total_pessoas": numeros[0] if numeros else None,
                "ativas_atualmente": numeros[1] if len(numeros) > 1 else None,
            }

        elif "salário mensal bruto" in chave_limpa.lower():
            # Extrai o valor numérico do salário e converte para float
            valor_numerico = float(re.sub(r"[^\d,]", "", valor).replace(",", "."))
            recursos_padronizados[chave_limpa] = valor_numerico

        elif "imóvel funcional" in chave_limpa.lower():
            # Extrai o período de uso
            periodo = re.search(r"\d{2}/\d{2}/\d{4} a \d{2}/\d{2}/\d{4}", valor)
            recursos_padronizados[chave_limpa] = {"uso_periodo": periodo.group() if periodo else "Não especificado"}

        elif "auxílio-moradia" in chave_limpa.lower():
            # Extrai o valor numérico do auxílio-moradia
            valor_numerico = float(re.sub(r"[^\d,]", "", valor).replace(",", "."))
            recursos_padronizados[chave_limpa] = valor_numerico

        elif "viagens em missão oficial" in chave_limpa.lower():
            # Extrai a quantidade de viagens (converte para int)
            quantidade = int(re.sub(r"[^\d]", "", valor))
            recursos_padronizados[chave_limpa] = quantidade

        elif "passaporte diplomático" in chave_limpa.lower():
            # Verifica se o valor indica que possui ou não o passaporte
            possui = "possui" in valor.lower()
            recursos_padronizados[chave_limpa] = possui

        else:
            # Caso não se encaixe em nenhuma regra específica, mantém o valor original
            recursos_padronizados[chave_limpa] = valor.strip()

    return recursos_padronizados


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
        soup.find("span", class_="atuacao__tipo", string="de sua autoria")
        .find_next("a", class_="atuacao__quantidade")
        .get_text(strip=True)
    )

    #     # Propostas legislativas - relatadas
    atuacao["propostas_relatadas"] = int(
        soup.find("span", class_="atuacao__tipo", string="relatadas")
        .find_next("a", class_="atuacao__quantidade")
        .get_text(strip=True)
    )

    #     # Votações nominais - em Plenário
    atuacao["votacoes_plenario"] = int(
        soup.find("span", class_="atuacao__tipo", string="em Plenário")
        .find_next("a", class_="atuacao__quantidade")
        .get_text(strip=True)
    )
    info["atuacao-2024"] = atuacao

    presenca = {}
    presenca["presencas"] = (
        soup.find("span", class_="presencas__label")
        .find_next("span", class_="d-none d-inline-lg", string=" na Câmara")
        .find_next("span", class_="presencas__qtd")
        .get_text()
        .strip()
    )

    presenca["ausencia_justificada"] = (
        soup.find("span", class_="presencas__label", string="Ausências justificadas")
        .find_next("span", class_="presencas__qtd")
        .get_text()
        .strip()
    )

    presenca["ausencia_nao_justificada"] = (
        soup.find("span", class_="presencas__label", string="Ausências não justificadas")
        .find_next("span", class_="presencas__qtd")
        .get_text()
        .strip()
    )

    info["presenca-2024"] = presenca

    comissoes = {}

    # Extraindo as comissões como Titular
    comissoes["titular"] = [item.get_text(strip=True) for item in soup.find_all("li", class_="titular-comissoes__item")]

    # Extraindo as comissões como Suplente
    comissoes["suplente"] = [
        item.get_text(strip=True) for item in soup.find_all("li", class_="suplente-comissoes__item")
    ]

    # Adicionando o dicionário de atuação de 2024 ao dicionário principal
    info["comissoes-2024"] = comissoes

    cota_data = {}
    cota_section = soup.find("li", class_="gasto").find("tbody")

    # Encontrar a tabela de dados no `tbody`
    cota_table_body = cota_section
    if cota_table_body:
        for row in cota_table_body.find_all("tr"):
            tipo = row.find_all("td")[0].get_text(strip=True)  # Nome do tipo (Gasto, Não utilizado)
            valor = row.find_all("td")[1].get_text(strip=True).replace(".", "").replace(",", ".")  # Valor numérico
            percentual = row.find_all("td")[2].get_text(strip=True).replace("%", "")  # Percentual

            # Armazenar os dados extraídos no dicionário
            cota_data[tipo] = {"valor": float(valor), "percentual": float(percentual)}

    info["cota-2024"] = cota_data

    # Dicionário para armazenar os dados mensais da cota parlamentar
    gasto_mensal_cota = []

    # Encontrar a tabela pelo ID "gastomensalcotaparlamentar"
    gasto_mensal_table = soup.find("table", id="gastomensalcotaparlamentar")

    if gasto_mensal_table:
        # Iterar pelas linhas do corpo da tabela (tbody)
        for row in gasto_mensal_table.find("tbody").find_all("tr"):
            mes = row.find_all("td")[0].get_text(strip=True)  # Mês
            valor = row.find_all("td")[1].get_text(strip=True).replace(".", "").replace(",", ".")  # Valor numérico
            percentual = row.find_all("td")[2].get_text(strip=True).replace("%", "")  # Percentual

            # Adicionar os dados para cada mês no formato de dicionário
            gasto_mensal_cota.append({"mes": mes, "valor": float(valor), "percentual": float(percentual)})

    # Adicionar os dados mensais ao dicionário principal
    info["gasto_mensal_cota_2024"] = gasto_mensal_cota

    # Dicionário para armazenar os dados mensais da cota parlamentar
    gasto_mensal_cota = []

    # Encontrar a tabela pelo ID "gastomensalcotaparlamentar"
    gasto_mensal_table = soup.find("table", id="gastomensalcotaparlamentar")

    if gasto_mensal_table:
        # Iterar pelas linhas do corpo da tabela (tbody)
        for row in gasto_mensal_table.find("tbody").find_all("tr"):
            mes = row.find_all("td")[0].get_text(strip=True)  # Mês
            valor = row.find_all("td")[1].get_text(strip=True).replace(".", "").replace(",", ".")  # Valor numérico
            percentual = row.find_all("td")[2].get_text(strip=True).replace("%", "")  # Percentual

            # Adicionar os dados para cada mês no formato de dicionário
            gasto_mensal_cota.append({"mes": mes, "valor": float(valor), "percentual": float(percentual)})

    # Adicionar os dados mensais ao dicionário principal
    info["gasto_mensal_cota_2024"] = gasto_mensal_cota

    # Dicionário para armazenar os dados da Verba de Gabinete
    verba_gabinete = {}

    # Encontrar a tabela de percentual gasto pela Verba de Gabinete
    verba_table = soup.find("table", id="percentualgastoverbagabinete")

    # Extração do percentual gasto da Verba de Gabinete
    if verba_table:
        verba_data = {}
        for row in verba_table.find("tbody").find_all("tr"):
            tipo = row.find_all("td")[0].get_text(strip=True)  # Gasto ou Não utilizado
            valor = row.find_all("td")[1].get_text(strip=True).replace(".", "").replace(",", ".")  # Valor numérico
            percentual = row.find_all("td")[2].get_text(strip=True).replace("%", "")  # Percentual

            # Armazenar os dados extraídos no dicionário
            verba_data[tipo] = {"valor": float(valor), "percentual": float(percentual)}
        verba_gabinete["percentual_gasto"] = verba_data

    # Encontrar a tabela de gasto mensal pela Verba de Gabinete
    verba_mensal_table = soup.find("table", id="gastomensalverbagabinete")

    # Extração do gasto mensal da Verba de Gabinete
    if verba_mensal_table:
        mensal_data = []
        for row in verba_mensal_table.find("tbody").find_all("tr"):
            mes = row.find_all("td")[0].get_text(strip=True)  # Mês
            valor = row.find_all("td")[1].get_text(strip=True).replace(".", "").replace(",", ".")  # Valor numérico
            percentual = row.find_all("td")[2].get_text(strip=True).replace("%", "")  # Percentual

            # Adicionar os dados para cada mês no formato de dicionário
            mensal_data.append({"mes": mes, "valor": float(valor), "percentual": float(percentual)})
        verba_gabinete["gasto_mensal"] = mensal_data

    # Adicionar os dados da verba de gabinete ao dicionário principal
    info["verba_gabinete_2024"] = verba_gabinete

    # Dicionário para armazenar os dados de benefícios
    recursos_beneficios = {}

    # Encontrar a seção de benefícios pelo ID "recursos-section"
    recursos_section = soup.find("section", id="recursos-section")

    for beneficio in recursos_section.find_all("div", class_="beneficio"):
        titulo = beneficio.find("h3", class_="beneficio__titulo").get_text(strip=True)  # Título do benefício

        # Encontrar o valor associado ao benefício
        information = beneficio.find("span", class_="beneficio__info") or beneficio.find("a", class_="beneficio__info")

        # Extrair o texto do valor, ou "Não informado" caso não exista
        valor = information.get_text(strip=True) if information else "Não informado"

        # Armazenar o título e valor no dicionário
        recursos_beneficios[titulo] = valor

    # Adicionar os dados de recursos e benefícios ao dicionário principal
    info["recursos_beneficios_2024"] = padronizar_recursos(recursos_beneficios)
    breakpoint()

    # emendas = []

    # # Localizar todas as emendas
    # for emenda in soup.find_all("li", class_="emendas__item"):
    #     # Extrair a descrição da emenda
    #     descricao = emenda.find("p", class_="emendas__descricao").get_text(strip=True)

    #     # Inicializar os valores com None
    #     valores = {
    #         "autorizado": None,
    #         "empenhado": None,
    #         "pago": None
    #     }

    #     for valor_item in emenda.find_all("li", class_="emendas-valores__item"):
    #         # Verificar se os títulos e valores estão presentes antes de tentar extraí-los
    #         titulo_tag = valor_item.find("span", class_="emendas-valores__titulo")
    #         valor_tag = valor_item.find("span", class_="emendas-valores__valor")

    #         if titulo_tag and valor_tag:
    #             titulo = titulo_tag.get_text(strip=True).replace(":", "").lower()
    #             valor = valor_tag.get_text(strip=True).replace("R$ ", "").replace(".", "").replace(",", ".")

    #             # Atribuir o valor correspondente no dicionário
    #             if "autorizado" in titulo:
    #                 valores["autorizado"] = float(valor)
    #             elif "empenhado" in titulo:
    #                 valores["empenhado"] = float(valor)
    #             elif "pago" in titulo:
    #                 valores["pago"] = float(valor)

    #     # Adicionar a emenda ao dicionário principal com descrição e valores
    #     emendas.append({
    #         "descricao": descricao,
    #         "valores": valores
    #     })

    # # Adicionando o dicionário de emendas ao dicionário principal
    # info["emendas-2024"] = emendas
