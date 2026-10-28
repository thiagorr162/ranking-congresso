const state = { data: null, sort: "total_gasto", query: "" };

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
const plural = (count, singular, pluralForm) => `${count} ${count === 1 ? singular : pluralForm}`;
const number = new Intl.NumberFormat("pt-BR");
const costPerVote = (senador) => senador.campanha_custo !== null && senador.campanha_votos ? senador.campanha_custo / senador.campanha_votos : null;
const publicShare = (senador) => senador.campanha_receitas ? Math.round(senador.campanha_publico / senador.campanha_receitas * 100) : 0;

const criteria = {
  total_gasto: {
    label: "Mais gastou",
    amount: (senador) => senador.total_gasto,
    description: "Total reembolsado pela cota no ano.",
    value: (senador) => money.format(senador.total_gasto),
    detail: (senador) => `${senador.quantidade_despesas} despesas`,
    category: (senador) => senador.categoria_principal || "Sem despesas",
    categoryDetail: (senador) => senador.categoria_principal ? money.format(senador.categoria_principal_valor) : "",
    page: "despesas.html",
    compare: (a, b) => b.total_gasto - a.total_gasto,
  },
  campanha: {
    label: "Campanha mais cara",
    column: "Custo da campanha",
    amount: (senador) => senador.campanha_custo,
    description: "Despesas declaradas ao TSE na campanha que elegeu cada parlamentar. Suplentes de senador não fazem campanha própria.",
    value: (senador) => senador.campanha_custo === null ? "Sem dados" : money.format(senador.campanha_custo),
    detail: (senador) => senador.campanha_custo === null ? "" : `${publicShare(senador)}% de dinheiro público`,
    category: (senador) => senador.campanha_ano ? `Eleição de ${senador.campanha_ano}` : "Sem campanha própria",
    categoryDetail: (senador) => senador.campanha_votos ? `${number.format(senador.campanha_votos)} votos` : "",
    page: "eleicao.html",
    compare: (a, b) => (b.campanha_custo ?? -1) - (a.campanha_custo ?? -1),
  },
  voto_caro: {
    label: "Voto mais caro",
    column: "Custo por voto",
    description: "Custo da campanha dividido pelos votos recebidos. Suplentes de senador não fazem campanha própria.",
    value: (senador) => costPerVote(senador) === null ? "Sem dados" : money.format(costPerVote(senador)),
    detail: (senador) => senador.campanha_votos ? `${number.format(senador.campanha_votos)} votos` : "",
    category: (senador) => senador.campanha_ano ? `Eleição de ${senador.campanha_ano}` : "Sem campanha própria",
    categoryDetail: (senador) => senador.campanha_custo === null ? "" : `Campanha de ${money.format(senador.campanha_custo)}`,
    page: "eleicao.html",
    compare: (a, b) => (costPerVote(b) ?? -1) - (costPerVote(a) ?? -1),
  },
  maior_despesa: {
    label: "Maior despesa",
    amount: (senador) => senador.maior_despesa,
    description: "Maior reembolso individual registrado no ano.",
    value: (senador) => money.format(senador.maior_despesa),
    detail: (senador) => senador.maior_despesa_fornecedor || "Sem despesas",
    category: (senador) => senador.maior_despesa_tipo || "Sem despesas",
    categoryDetail: () => "",
    page: "despesas.html",
    compare: (a, b) => b.maior_despesa - a.maior_despesa,
  },
  faltas: {
    label: "Mais faltou",
    description: CASA.faltas,
    value: (senador) => `${senador.faltas} ${senador.faltas === 1 ? "falta" : "faltas"}`,
    detail: (senador) => `${senador.percentual_presenca}% de presença`,
    category: (senador) => CASA.temJustificativas ? `${senador.faltas_justificadas} justificadas` : `${senador.total_sessoes} sessões no ano`,
    categoryDetail: (senador) => `${senador.presencas} sessões com presença`,
    page: "frequencia.html",
    compare: (a, b) => b.faltas - a.faltas,
  },
  projetos: {
    label: "Menos projetos",
    description: "Projetos de lei e PECs apresentados no ano, como autor ou coautor. Quem apresentou menos aparece primeiro.",
    value: (senador) => plural(senador.projetos, "projeto", "projetos"),
    detail: (senador) => `${senador.projetos_tramitando} em tramitação`,
    category: () => "Ver projetos apresentados",
    categoryDetail: (senador) => `${plural(senador.autorias, "autoria", "autorias")} no total, com requerimentos`,
    page: "projetos.html",
    compare: (a, b) => a.projetos - b.projetos || a.autorias - b.autorias,
  },
};


function renderTop(criterion) {
  const top = [...state.data.parlamentares].sort(criterion.compare)[0];
  const name = document.querySelector("#maior-nome");
  const photo = document.querySelector("#maior-foto");
  document.querySelector("#destaque-rotulo").textContent = `1º lugar · ${criterion.label}`;
  document.querySelector("#maior-partido").textContent = top
    ? [`${top.partido} · ${top.uf}`, top.exercicio_inicio && `atuando desde ${date.format(new Date(`${top.exercicio_inicio}T00:00:00Z`))}`].filter(Boolean).join(" · ")
    : "";
  const contact = document.querySelector("#maior-contato");
  contact.replaceChildren();
  if (top?.email) {
    const email = document.createElement("a");
    email.href = `mailto:${top.email}`;
    email.textContent = top.email;
    contact.append(email);
  }
  document.querySelector("#maior-detalhe").textContent = top ? criterion.detail(top) : "";
  name.textContent = top?.nome || "—";
  name.href = top ? pageUrl("perfil.html", { id: top.id }) : "";
  photo.hidden = !top?.foto;
  if (top?.foto) photo.src = top.foto;
  document.querySelector("#maior-valor").textContent = top ? criterion.value(top) : "";
  startComparisons(document.querySelector("#comparacao-maior"), top && criterion.amount ? criterion.amount(top) : 0);
}

function render() {
  const criterion = criteria[state.sort];
  const query = state.query.trim().toLocaleLowerCase("pt-BR");
  const senators = [...state.data.parlamentares]
    .sort(criterion.compare)
    .map((senador, index) => ({ senador, position: index + 1 }))
    .filter(({ senador }) => `${senador.nome} ${senador.partido} ${senador.uf}`.toLocaleLowerCase("pt-BR").includes(query));

  document.querySelector("#criterio-explicacao").textContent = criterion.description;
  document.querySelector("#coluna-valor").textContent = criterion.column || `Valor em ${state.data.ano}`;
  document.querySelector("#ranking").innerHTML = senators.map(({ senador, position }) => `
    <li class="rank-item${position <= 3 ? " rank-top" : ""}" value="${position}">
      <span class="position">${position}<small>/${state.data.parlamentares.length}</small></span>
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
        <a href="${pageUrl(criterion.page, { id: senador.id, criterio: state.sort })}">${escapeHtml(criterion.category(senador))}</a>
        <small>${escapeHtml(criterion.categoryDetail(senador))}</small>
      </div>
      <div class="value">
        <strong>${escapeHtml(criterion.value(senador))}</strong>
        <small>${escapeHtml(criterion.detail(senador))}</small>
      </div>
    </li>
  `).join("");
}

document.title = `Ranking do Congresso — ${CASA.menu}`;
document.querySelector("#titulo-ranking").textContent = `Ranking dos ${CASA.plural}`;
document.querySelector("#coluna-nome").textContent = CASA.singular;
document.querySelector("#fonte").href = CASA.dadosAbertos;

async function load() {
  try {
    const response = await fetch(dataUrl());
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    document.querySelector("#total-gasto").textContent = money.format(state.data.total_gasto);
    startComparisons(document.querySelector("#comparacao-total"), state.data.total_gasto);
    const campaigns = state.data.parlamentares.reduce((sum, item) => sum + (item.campanha_custo || 0), 0);
    const years = state.data.eleicoes_anos || [];
    if (years.length) document.querySelector("#campanhas-rotulo").textContent = `Gasto nas campanhas de ${years.join(" e ")}`;
    document.querySelector("#total-campanhas").textContent = campaigns ? money.format(campaigns) : "—";
    startComparisons(document.querySelector("#comparacao-campanhas"), campaigns);
    document.querySelector("#atualizado").textContent = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" })
      .format(new Date(state.data.atualizado_em));
    document.querySelector("#fonte").href = state.data.fonte;
    renderTop(criteria[state.sort]);
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
    renderTop(criteria[state.sort]);
    render();
  });
});

document.querySelector("#busca").addEventListener("input", (event) => {
  state.query = event.target.value;
  render();
});

load();
