const state = { data: null, sort: "total_gasto", query: "" };

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

const criteria = {
  total_gasto: {
    description: "Total reembolsado pela cota no ano.",
    value: (senador) => money.format(senador.total_gasto),
    detail: (senador) => `${senador.quantidade_despesas} despesas`,
    category: (senador) => senador.categoria_principal || "Sem despesas",
    categoryDetail: (senador) => senador.categoria_principal ? money.format(senador.categoria_principal_valor) : "",
    page: "despesas.html",
  },
  maior_despesa: {
    description: "Maior reembolso individual registrado no ano.",
    value: (senador) => money.format(senador.maior_despesa),
    detail: (senador) => senador.maior_despesa_fornecedor || "Sem despesas",
    category: (senador) => senador.maior_despesa_tipo || "Sem despesas",
    categoryDetail: () => "",
    page: "despesas.html",
  },
  faltas: {
    description: "Sessões em que o Senado registrou “Não compareceu”.",
    value: (senador) => `${senador.faltas} ${senador.faltas === 1 ? "falta" : "faltas"}`,
    detail: (senador) => `${senador.percentual_presenca}% de presença`,
    category: (senador) => `${senador.faltas_justificadas} justificadas`,
    categoryDetail: (senador) => `${senador.presencas} sessões com presença`,
    page: "frequencia.html",
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
  const senators = [...state.data.senadores]
    .filter((item) => `${item.nome} ${item.partido} ${item.uf}`.toLocaleLowerCase("pt-BR").includes(query))
    .sort((a, b) => b[state.sort] - a[state.sort]);

  document.querySelector("#criterio-explicacao").textContent = criterion.description;
  const detailParameter = criterion.parameter || "criterio";
  const detailTarget = criterion.target || state.sort;
  document.querySelector("#ranking").innerHTML = senators.map((senador, index) => `
    <li class="rank-item">
      <span class="position">${index + 1}</span>
      <div class="person">
        <img src="${escapeHtml(senador.foto)}" alt="" loading="lazy" />
        <div>
          <a href="senador.html?id=${encodeURIComponent(senador.id)}">${escapeHtml(senador.nome)}</a>
          <small>${escapeHtml(senador.partido)} · ${escapeHtml(senador.uf)}</small>
        </div>
      </div>
      <div class="category">
        <a href="${criterion.page}?id=${encodeURIComponent(senador.id)}&${detailParameter}=${encodeURIComponent(detailTarget)}">${escapeHtml(criterion.category(senador))}</a>
        <small>${escapeHtml(criterion.categoryDetail(senador))}</small>
      </div>
      <div class="value">
        <strong>${escapeHtml(criterion.value(senador))}</strong>
        <small>${escapeHtml(criterion.detail(senador))}</small>
      </div>
    </li>
  `).join("");
}

async function load() {
  try {
    const response = await fetch("data/senadores.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    const top = [...state.data.senadores].sort((a, b) => b.total_gasto - a.total_gasto)[0];
    document.querySelector("#total-gasto").textContent = money.format(state.data.total_gasto);
    document.querySelector("#maior-nome").textContent = top?.nome || "—";
    document.querySelector("#maior-valor").textContent = top ? money.format(top.total_gasto) : "";
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
