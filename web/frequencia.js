const params = new URLSearchParams(window.location.search);
const senatorId = params.get("id");
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
const state = { data: null, filter: params.get("criterio") === "faltas" ? "falta" : "falta" };

function escapeHtml(value) {
  return String(value ?? "Não informado")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function render() {
  const sessions = state.data.frequencia.sessoes.filter((session) =>
    state.filter === "todas" ? session.classificacao !== "nao_classificada" : session.classificacao === state.filter
  );
  document.querySelector("#contagem").textContent = `${sessions.length} ${sessions.length === 1 ? "sessão" : "sessões"}`;
  document.querySelector("#sessoes").innerHTML = sessions.map((session) => `
    <tr>
      <td>${date.format(new Date(`${session.data}T00:00:00Z`))}</td>
      <td><span class="status status-${escapeHtml(session.classificacao)}">${session.classificacao === "falta" ? (CASA.temJustificativas ? "Não compareceu" : "Sem presença") : session.classificacao === "justificada" ? "Justificada" : "Presença"}</span></td>
      <td>${escapeHtml(CASA.temJustificativas ? session.motivo : session.descricao)}</td>
      ${CASA.temJustificativas ? `<td>${session.votacoes}</td>` : ""}
    </tr>
  `).join("");
}

async function load() {
  if (!senatorId) return showError();
  try {
    const response = await fetch(dataUrl(`${encodeURIComponent(senatorId)}/frequencia.json`));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    const summary = state.data.resumo;
    document.title = `${state.data.parlamentar.nome} — Frequência`;
    document.querySelector("#nome").textContent = state.data.parlamentar.nome;
    document.querySelector("#voltar").href = pageUrl("perfil.html", { id: senatorId });
    document.querySelector("#sessoes-descricao").textContent = CASA.sessoes;
    document.querySelector("#cabecalho").innerHTML = CASA.temJustificativas
      ? "<tr><th>Data</th><th>Situação</th><th>Motivo oficial</th><th>Votações</th></tr>"
      : "<tr><th>Data</th><th>Situação</th><th>Sessão</th></tr>";
    document.querySelector("#presencas").textContent = summary.presencas;
    document.querySelector("#faltas").textContent = summary.faltas;
    document.querySelector("#justificadas").textContent = summary.faltas_justificadas;
    document.querySelector("#percentual").textContent = `${summary.percentual_presenca}%`;
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
