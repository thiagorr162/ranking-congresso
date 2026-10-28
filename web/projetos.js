const params = new URLSearchParams(window.location.search);
const senatorId = params.get("id");
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
const state = { data: null, filter: "todos" };

function escapeHtml(value) {
  return String(value ?? "Não informado")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  return value ? date.format(new Date(`${value.slice(0, 10)}T00:00:00Z`)) : "—";
}

function render() {
  const projects = state.data.projetos.filter((project) =>
    state.filter === "todos" || (state.filter === "tramitando") === project.tramitando
  );
  document.querySelector("#contagem").textContent = `${projects.length} ${projects.length === 1 ? "projeto" : "projetos"}`;
  document.querySelector("#lista").innerHTML = projects.map((project) => `
    <tr>
      <td>${formatDate(project.data)}</td>
      <td>
        <a class="expense-link" href="${escapeHtml(project.url_documento)}" target="_blank" rel="noreferrer">${escapeHtml(project.identificacao)}</a>
        <span class="cell-detail">${escapeHtml(project.tipo)}</span>
      </td>
      <td>${escapeHtml(project.ementa)}</td>
      <td>${escapeHtml(project.situacao)}<span class="cell-detail">${project.tramitando ? "Em tramitação" : "Encerrado"}</span></td>
    </tr>
  `).join("");
}

async function load() {
  if (!senatorId) return showError();
  try {
    const response = await fetch(dataUrl(`${encodeURIComponent(senatorId)}/projetos.json`));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    const summary = state.data.resumo;
    document.title = `${state.data.parlamentar.nome} — Projetos`;
    document.querySelector("#nome").textContent = state.data.parlamentar.nome;
    document.querySelector("#voltar").href = pageUrl("perfil.html", { id: senatorId });
    document.querySelector("#projetos").textContent = summary.projetos;
    document.querySelector("#tramitando").textContent = summary.projetos_tramitando;
    document.querySelector("#autorias").textContent = summary.autorias;
    document.querySelector("#exercicio").textContent = formatDate(state.data.parlamentar.exercicio_inicio);
    document.querySelector("#participacao").textContent = state.data.parlamentar.participacao || "";
    document.querySelector("#conteudo").hidden = false;
    render();
  } catch (error) {
    console.error(error);
    showError();
  }
}

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".filters .selected")?.classList.remove("selected");
    button.classList.add("selected");
    state.filter = button.dataset.filter;
    render();
  });
});

function showError() {
  document.querySelector("#erro").hidden = false;
}

load();
