const params = new URLSearchParams(window.location.search);
const senatorId = params.get("id");
const expenseId = params.get("despesa");
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });

function valueOrMissing(value) {
  return value || "Não informado pelo Senado";
}

async function load() {
  if (!senatorId || !expenseId) return showError();
  try {
    const response = await fetch(`data/senadores/${encodeURIComponent(senatorId)}/despesas.json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const expense = data.despesas.find((item) => item.id_fonte === expenseId);
    if (!expense) throw new Error("Despesa não encontrada");
    const sameSupplier = data.despesas.filter((item) => item.fornecedor === expense.fornecedor);
    const sameCategory = data.despesas.filter((item) => item.tipo === expense.tipo);
    const sameMonth = data.despesas.filter((item) => item.ano === expense.ano && item.mes === expense.mes);
    const supplierTotal = sameSupplier.reduce((sum, item) => sum + item.valor, 0);
    const categoryTotal = sameCategory.reduce((sum, item) => sum + item.valor, 0);
    const monthTotal = sameMonth.reduce((sum, item) => sum + item.valor, 0);

    document.title = `${data.parlamentar.nome} — ${money.format(expense.valor)}`;
    document.querySelector("#senador").textContent = data.parlamentar.nome;
    document.querySelector("#categoria").textContent = expense.tipo;
    document.querySelector("#valor").textContent = money.format(expense.valor);
    document.querySelector("#detalhamento").textContent = valueOrMissing(expense.detalhamento);
    document.querySelector("#fornecedor").textContent = valueOrMissing(expense.fornecedor);
    document.querySelector("#cpf-cnpj").textContent = valueOrMissing(expense.cpf_cnpj);
    document.querySelector("#tipo-documento").textContent = valueOrMissing(expense.tipo_documento);
    document.querySelector("#documento").textContent = expense.documento ? `Nº ${expense.documento}` : "Número não informado";
    document.querySelector("#data").textContent = expense.data
      ? date.format(new Date(`${expense.data}T00:00:00Z`))
      : "Não informada pelo Senado";
    document.querySelector("#referencia").textContent = `Referência: ${String(expense.mes).padStart(2, "0")}/${expense.ano}`;
    document.querySelector("#identificador").textContent = expense.id_fonte;
    document.querySelector("#total-fornecedor").textContent = money.format(supplierTotal);
    document.querySelector("#quantidade-fornecedor").textContent = `${sameSupplier.length} ${sameSupplier.length === 1 ? "despesa" : "despesas"} no ano`;
    document.querySelector("#total-categoria").textContent = money.format(categoryTotal);
    document.querySelector("#quantidade-categoria").textContent = `${sameCategory.length} ${sameCategory.length === 1 ? "despesa" : "despesas"} no ano`;
    document.querySelector("#total-mes").textContent = money.format(monthTotal);
    document.querySelector("#participacao-mes").textContent = `${monthTotal ? (expense.valor / monthTotal * 100).toFixed(1).replace(".", ",") : "0"}% corresponde a esta despesa`;
    document.querySelector("#aviso-dados").textContent = expense.detalhamento
      ? "As informações acima reproduzem e contextualizam os dados publicados pelo Senado Federal."
      : "O Senado Federal não publicou detalhamento adicional nem link para comprovante neste registro.";
    document.querySelector("#fonte").href = data.fonte;
    document.querySelector("#voltar").href = `despesas.html?id=${encodeURIComponent(senatorId)}&criterio=total_gasto`;
    document.querySelector("#conteudo").hidden = false;
  } catch (error) {
    console.error(error);
    showError();
  }
}

function showError() {
  document.querySelector("#erro").hidden = false;
}

load();
