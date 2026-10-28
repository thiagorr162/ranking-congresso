const params = new URLSearchParams(window.location.search);
const senatorId = params.get("id");
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const count = new Intl.NumberFormat("pt-BR");

function formatCnpj(value) {
  return value ? value.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5") : "—";
}

function rows(target, items, columns) {
  document.querySelector(target).innerHTML = items.length
    ? items.map((item) => `<tr>${columns.map((column) => `<td>${column(item)}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${columns.length}">Sem registros.</td></tr>`;
}

async function load() {
  if (!senatorId) return showError();
  try {
    const response = await fetch(dataUrl(`${encodeURIComponent(senatorId)}/eleicao.json`));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const election = data.eleicao;
    document.title = `${data.parlamentar.nome} — Campanha`;
    document.querySelector("#voltar").href = pageUrl("perfil.html", { id: senatorId });
    if (!election) {
      document.querySelector("#sem-dados").hidden = false;
      return;
    }
    const share = election.receitas ? Math.round(election.dinheiro_publico / election.receitas * 100) : 0;
    document.querySelector("#nome").textContent = data.parlamentar.nome;
    document.querySelector("#descricao").textContent =
      `Eleição de ${election.ano} · ${election.cargo} por ${election.uf} (${election.partido}) · ${election.situacao}`;
    document.querySelector("#receitas").textContent = money.format(election.receitas);
    document.querySelector("#publico").textContent = money.format(election.dinheiro_publico);
    document.querySelector("#publico-pct").textContent = `${share}% do arrecadado`;
    document.querySelector("#despesas").textContent = money.format(election.despesas);
    document.querySelector("#repasses").textContent = election.repasses_a_outros
      ? `Sem contar ${money.format(election.repasses_a_outros)} repassados a outros candidatos`
      : "";
    document.querySelector("#votos").textContent = count.format(election.votos);
    document.querySelector("#custo-voto").textContent = election.votos ? `${money.format(election.despesas / election.votos)} por voto` : "";
    const value = (item) => `<strong>${money.format(item.valor)}</strong>`;
    rows("#origens", election.receitas_por_fonte, [(item) => escapeHtml(item.fonte), value]);
    rows("#doadores", election.maiores_doadores, [(item) => escapeHtml(item.nome), value]);
    rows("#tipos", election.despesas_por_tipo, [(item) => escapeHtml(item.tipo), value]);
    rows("#fornecedores", election.maiores_fornecedores, [
      (item) => escapeHtml(item.nome),
      (item) => formatCnpj(item.cnpj),
      value,
    ]);
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
