const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
const params = new URLSearchParams(window.location.search);
const senatorId = params.get("id");
const criterion = params.get("criterio") || "total_gasto";
const state = { expenses: [], ordering: "data_desc" };
const collator = new Intl.Collator("pt-BR", { sensitivity: "base" });

function escapeHtml(value) {
  return String(value ?? "Não informado")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function selectExpenses(data) {
  if (criterion === "maior_despesa") {
    return [...data.despesas].sort((a, b) => b.valor - a.valor).slice(0, 1);
  }
  if (criterion === "concentracao_fornecedor") {
    return data.despesas.filter((item) => item.fornecedor === data.resumo.fornecedor_principal);
  }
  return data.despesas;
}

function heading(data) {
  if (criterion === "maior_despesa") {
    return ["MAIOR DESPESA", data.parlamentar.nome, "O maior reembolso individual registrado no ano."];
  }
  if (criterion === "concentracao_fornecedor") {
    return ["FORNECEDOR PRINCIPAL", data.parlamentar.nome, data.resumo.fornecedor_principal || "Sem despesas"];
  }
  return ["TODAS AS DESPESAS", data.parlamentar.nome, `Cota parlamentar de ${data.ano}.`];
}

function orderedExpenses() {
  const sorters = {
    data_desc: (a, b) => (b.data || "").localeCompare(a.data || ""),
    data_asc: (a, b) => (a.data || "").localeCompare(b.data || ""),
    valor_desc: (a, b) => b.valor - a.valor,
    valor_asc: (a, b) => a.valor - b.valor,
    descricao_asc: (a, b) => collator.compare(a.tipo || "", b.tipo || ""),
    fornecedor_asc: (a, b) => collator.compare(a.fornecedor || "", b.fornecedor || ""),
  };
  return [...state.expenses].sort(sorters[state.ordering]);
}

function renderExpenses() {
  document.querySelector("#despesas").innerHTML = orderedExpenses().map((expense) => `
    <tr>
      <td>${expense.data ? date.format(new Date(`${expense.data}T00:00:00Z`)) : "Não informada"}</td>
      <td><a class="expense-link" href="${pageUrl("despesa.html", { id: senatorId, despesa: expense.id_fonte })}">${escapeHtml(expense.tipo)}</a>${expense.detalhamento ? `<small class="cell-detail">${escapeHtml(expense.detalhamento)}</small>` : '<small class="cell-detail">Sem detalhamento adicional</small>'}</td>
      <td>${escapeHtml(expense.fornecedor)}<small class="cell-detail">${escapeHtml(expense.cpf_cnpj)}</small></td>
      <td>${expense.url_documento ? `<a class="expense-link" href="${escapeHtml(expense.url_documento)}" target="_blank" rel="noreferrer">${escapeHtml(expense.tipo_documento)} ↗</a>` : escapeHtml(expense.tipo_documento)}<small class="cell-detail">Nº ${escapeHtml(expense.documento)}</small></td>
      <td><strong>${money.format(expense.valor)}</strong></td>
    </tr>
  `).join("");
}

async function load() {
  if (!senatorId) return showError();
  try {
    const response = await fetch(dataUrl(`${encodeURIComponent(senatorId)}/despesas.json`));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const expenses = selectExpenses(data);
    state.expenses = expenses;
    const [label, title, description] = heading(data);
    document.title = `${title} — Despesas`;
    document.querySelector("#rotulo").textContent = label;
    document.querySelector("#titulo").textContent = title;
    document.querySelector("#descricao").textContent = description;
    document.querySelector("#voltar").href = pageUrl("perfil.html", { id: senatorId });
    document.querySelector("#contagem").textContent = `${expenses.length} ${expenses.length === 1 ? "despesa" : "despesas"}`;
    document.querySelector("#fonte").href = data.fonte;
    renderExpenses();
    document.querySelector("#conteudo").hidden = false;
  } catch (error) {
    console.error(error);
    showError();
  }
}

document.querySelector("#ordenacao").addEventListener("change", (event) => {
  state.ordering = event.target.value;
  renderExpenses();
});

function showError() {
  document.querySelector("#erro").hidden = false;
}

load();
