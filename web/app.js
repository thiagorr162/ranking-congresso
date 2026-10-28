const state = { data: null, sort: "total_gasto", query: "" };

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
const plural = (count, singular, pluralForm) => `${count} ${count === 1 ? singular : pluralForm}`;

const criteria = {
  total_gasto: {
    description: "Total reembolsado pela cota no ano.",
    value: (senador) => money.format(senador.total_gasto),
    detail: (senador) => `${senador.quantidade_despesas} despesas`,
    category: (senador) => senador.categoria_principal || "Sem despesas",
    categoryDetail: (senador) => senador.categoria_principal ? money.format(senador.categoria_principal_valor) : "",
    page: "despesas.html",
    compare: (a, b) => b.total_gasto - a.total_gasto,
  },
  maior_despesa: {
    description: "Maior reembolso individual registrado no ano.",
    value: (senador) => money.format(senador.maior_despesa),
    detail: (senador) => senador.maior_despesa_fornecedor || "Sem despesas",
    category: (senador) => senador.maior_despesa_tipo || "Sem despesas",
    categoryDetail: () => "",
    page: "despesas.html",
    compare: (a, b) => b.maior_despesa - a.maior_despesa,
  },
  faltas: {
    description: CASA.faltas,
    value: (senador) => `${senador.faltas} ${senador.faltas === 1 ? "falta" : "faltas"}`,
    detail: (senador) => `${senador.percentual_presenca}% de presença`,
    category: (senador) => CASA.temJustificativas ? `${senador.faltas_justificadas} justificadas` : `${senador.total_sessoes} sessões no ano`,
    categoryDetail: (senador) => `${senador.presencas} sessões com presença`,
    page: "frequencia.html",
    compare: (a, b) => b.faltas - a.faltas,
  },
  projetos: {
    description: "Projetos de lei e PECs apresentados no ano, como autor ou coautor. Quem apresentou menos aparece primeiro.",
    value: (senador) => plural(senador.projetos, "projeto", "projetos"),
    detail: (senador) => `${senador.projetos_tramitando} em tramitação`,
    category: () => "Ver projetos apresentados",
    categoryDetail: (senador) => `${plural(senador.autorias, "autoria", "autorias")} no total, com requerimentos`,
    page: "projetos.html",
    compare: (a, b) => a.projetos - b.projetos || a.autorias - b.autorias,
  },
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function render() {
  const criterion = criteria[state.sort];
  const query = state.query.trim().toLocaleLowerCase("pt-BR");
  const senators = [...state.data.parlamentares]
    .filter((item) => `${item.nome} ${item.partido} ${item.uf}`.toLocaleLowerCase("pt-BR").includes(query))
    .sort(criterion.compare);

  document.querySelector("#criterio-explicacao").textContent = criterion.description;
  const detailParameter = criterion.parameter || "criterio";
  const detailTarget = criterion.target || state.sort;
  document.querySelector("#ranking").innerHTML = senators.map((senador, index) => `
    <li class="rank-item">
      <span class="position">${index + 1}</span>
      <div class="person">
        <img src="${escapeHtml(senador.foto)}" alt="" loading="lazy" />
        <div>
          <a href="${pageUrl("perfil.html", { id: senador.id })}">${escapeHtml(senador.nome)}</a>
          <small>${escapeHtml(senador.partido)} · ${escapeHtml(senador.uf)}</small>
        </div>
      </div>
      <div class="since">
        <span>${senador.exercicio_inicio ? date.format(new Date(`${senador.exercicio_inicio}T00:00:00Z`)) : "—"}</span>
        <small>${escapeHtml(senador.participacao || "")}</small>
      </div>
      <div class="category">
        <a href="${pageUrl(criterion.page, { id: senador.id, [detailParameter]: detailTarget })}">${escapeHtml(criterion.category(senador))}</a>
        <small>${escapeHtml(criterion.categoryDetail(senador))}</small>
      </div>
      <div class="value">
        <strong>${escapeHtml(criterion.value(senador))}</strong>
        <small>${escapeHtml(criterion.detail(senador))}</small>
      </div>
    </li>
  `).join("");
}

document.title = `Saiu do Seu Bolso — Ranking dos ${CASA.plural}`;
document.querySelector("#titulo-ranking").textContent = `Ranking dos ${CASA.plural}`;
document.querySelector("#coluna-nome").textContent = CASA.singular;
document.querySelector("#fonte").href = CASA.dadosAbertos;

async function load() {
  try {
    const response = await fetch(dataUrl());
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    const top = [...state.data.parlamentares].sort((a, b) => b.total_gasto - a.total_gasto)[0];
    document.querySelector("#total-gasto").textContent = money.format(state.data.total_gasto);
    startComparisons(document.querySelector("#comparacao-total"), state.data.total_gasto);
    document.querySelector("#maior-nome").textContent = top?.nome || "—";
    if (top) {
      document.querySelector("#maior-nome").href = pageUrl("perfil.html", { id: top.id });
      const photo = document.querySelector("#maior-foto");
      photo.src = top.foto;
      photo.hidden = !top.foto;
    }
    document.querySelector("#maior-valor").textContent = top ? money.format(top.total_gasto) : "";
    startComparisons(document.querySelector("#comparacao-maior"), top?.total_gasto);
    document.querySelector("#atualizado").textContent = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" })
      .format(new Date(state.data.atualizado_em));
    document.querySelector("#fonte").href = state.data.fonte;
    render();
  } catch (error) {
    console.error(error);
    document.querySelector("#erro").hidden = false;
  }
}

document.querySelectorAll("[data-sort]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".filters .selected")?.classList.remove("selected");
    button.classList.add("selected");
    state.sort = button.dataset.sort;
    render();
  });
});

document.querySelector("#busca").addEventListener("input", (event) => {
  state.query = event.target.value;
  render();
});

load();
