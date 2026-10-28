const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const params = new URLSearchParams(window.location.search);
const senatorId = params.get("id");
const monthName = new Intl.DateTimeFormat("pt-BR", { month: "short", timeZone: "UTC" });

function renderBars(target, items, formatter = money.format) {
  const maximum = Math.max(...items.map((item) => item.value), 0);
  target.innerHTML = items.length ? items.map((item) => {
    const width = maximum ? Math.max((item.value / maximum) * 100, 2) : 0;
    return `<div class="bar-row">
      <div class="bar-label"><span title="${item.label}">${item.label}</span><strong>${formatter(item.value)}</strong></div>
      <div class="bar-track"><span style="width: ${width}%"></span></div>
    </div>`;
  }).join("") : '<p class="empty-chart">Sem dados no período.</p>';
}

function renderTimeline(target, items) {
  if (!items.length) {
    target.innerHTML = '<p class="empty-chart">Sem dados no período.</p>';
    return;
  }

  const svgNamespace = "http://www.w3.org/2000/svg";
  const width = 640;
  const height = 230;
  const padding = { top: 22, right: 18, bottom: 38, left: 18 };
  const maximum = Math.max(...items.map((item) => item.value), 1);
  const x = (index) => padding.left + (items.length === 1 ? (width - padding.left - padding.right) / 2 : index * (width - padding.left - padding.right) / (items.length - 1));
  const y = (value) => padding.top + (1 - value / maximum) * (height - padding.top - padding.bottom);
  const svg = document.createElementNS(svgNamespace, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Evolução mensal dos gastos");

  for (const fraction of [0, 0.5, 1]) {
    const grid = document.createElementNS(svgNamespace, "line");
    const gridY = padding.top + fraction * (height - padding.top - padding.bottom);
    grid.setAttribute("x1", padding.left);
    grid.setAttribute("x2", width - padding.right);
    grid.setAttribute("y1", gridY);
    grid.setAttribute("y2", gridY);
    grid.setAttribute("class", "timeline-grid");
    svg.append(grid);
  }

  const line = document.createElementNS(svgNamespace, "polyline");
  line.setAttribute("points", items.map((item, index) => `${x(index)},${y(item.value)}`).join(" "));
  line.setAttribute("class", "timeline-line");
  svg.append(line);

  const tooltip = document.createElement("div");
  tooltip.className = "timeline-tooltip";
  tooltip.hidden = true;
  const showTooltip = (item, index) => {
    tooltip.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = `${item.label}: ${money.format(item.value)}`;
    const count = document.createElement("span");
    count.textContent = `${item.count} ${item.count === 1 ? "despesa" : "despesas"}`;
    const description = document.createElement("span");
    description.textContent = `Principal descrição: ${item.description}`;
    tooltip.append(title, count, description);
    tooltip.style.left = `${x(index) / width * 100}%`;
    tooltip.style.top = `${y(item.value) / height * 100}%`;
    tooltip.hidden = false;
  };

  items.forEach((item, index) => {
    const point = document.createElementNS(svgNamespace, "circle");
    point.setAttribute("cx", x(index));
    point.setAttribute("cy", y(item.value));
    point.setAttribute("r", 6);
    point.setAttribute("class", "timeline-point");
    point.setAttribute("tabindex", "0");
    point.setAttribute("aria-label", `${item.label}, ${money.format(item.value)}, ${item.count} despesas, principal descrição: ${item.description}`);
    point.addEventListener("mouseenter", () => showTooltip(item, index));
    point.addEventListener("focus", () => showTooltip(item, index));
    point.addEventListener("click", () => showTooltip(item, index));
    point.addEventListener("mouseleave", () => { tooltip.hidden = true; });
    point.addEventListener("blur", () => { tooltip.hidden = true; });
    svg.append(point);

    const label = document.createElementNS(svgNamespace, "text");
    label.textContent = item.label;
    label.setAttribute("x", x(index));
    label.setAttribute("y", height - 12);
    label.setAttribute("class", "timeline-label");
    svg.append(label);
  });

  target.replaceChildren(svg, tooltip);
}

function renderExpenseCharts(expenses) {
  const byMonth = new Map();
  const byCategory = new Map();
  for (const expense of expenses) {
    const month = expense.ano && expense.mes ? `${expense.ano}-${String(expense.mes).padStart(2, "0")}` : expense.data?.slice(0, 7);
    if (month) {
      const monthly = byMonth.get(month) || { value: 0, count: 0, descriptions: new Map() };
      const description = expense.detalhamento || expense.tipo || "Não informado";
      monthly.value += expense.valor;
      monthly.count += 1;
      monthly.descriptions.set(description, (monthly.descriptions.get(description) || 0) + expense.valor);
      byMonth.set(month, monthly);
    }
    const category = expense.tipo || "Não informado";
    byCategory.set(category, (byCategory.get(category) || 0) + expense.valor);
  }
  const months = [...byMonth].sort(([a], [b]) => a.localeCompare(b)).map(([key, monthly]) => ({
    label: monthName.format(new Date(`${key}-01T00:00:00Z`)).replace(".", ""),
    value: monthly.value,
    count: monthly.count,
    description: [...monthly.descriptions].sort((a, b) => b[1] - a[1])[0][0],
  }));
  const categories = [...byCategory].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([label, value]) => ({ label, value }));
  renderBars(document.querySelector("#grafico-meses"), months);
  renderTimeline(document.querySelector("#grafico-serie-temporal"), months);
  renderBars(document.querySelector("#grafico-categorias"), categories);
}

function renderAttendance(summary) {
  const items = [
    { label: "Presenças", value: summary.presencas, className: "present" },
    { label: "Faltas", value: summary.faltas, className: "absent" },
    { label: "Justificadas", value: summary.faltas_justificadas, className: "justified" },
  ];
  const total = items.reduce((sum, item) => sum + item.value, 0);
  document.querySelector("#grafico-presenca").innerHTML = `
    <div class="attendance-track">${items.map((item) => `<span class="${item.className}" style="width: ${total ? item.value / total * 100 : 0}%"></span>`).join("")}</div>
    <div class="attendance-legend">${items.map((item) => `<span><i class="${item.className}"></i>${item.label}: <strong>${item.value}</strong></span>`).join("")}</div>`;
}

function renderProjects(projects) {
  const target = document.querySelector("#projetos-recentes");
  target.innerHTML = projects.length ? projects.slice(0, 5).map((project) => `
    <li>
      <a class="expense-link" href="${escapeHtml(project.url_documento)}" target="_blank" rel="noreferrer">${escapeHtml(project.identificacao)}</a>
      <span>${escapeHtml(project.ementa)}</span>
      <small>${escapeHtml(project.situacao)}${project.tramitando ? " · em tramitação" : ""}</small>
    </li>`).join("") : '<li class="empty-chart">Nenhum projeto apresentado no período.</li>';
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function load() {
  if (!senatorId) return showError();
  try {
    const base = `data/senadores/${encodeURIComponent(senatorId)}`;
    const responses = await Promise.all([
      fetch(`${base}/perfil.json`),
      fetch(`${base}/despesas.json`),
      fetch(`${base}/projetos.json`),
    ]);
    if (responses.some((response) => !response.ok)) throw new Error("Não foi possível carregar os dados");
    const [data, expensesData, projectsData] = await Promise.all(responses.map((response) => response.json()));
    const person = data.parlamentar;
    const summary = data.resumo;
    document.title = `${person.nome} — Saiu do Seu Bolso`;
    document.querySelector("#foto").src = person.url_foto;
    document.querySelector("#nome").textContent = person.nome;
    document.querySelector("#meta").textContent = `${person.partido} · ${person.uf}`;
    if (person.exercicio_inicio) {
      const since = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${person.exercicio_inicio}T00:00:00Z`));
      document.querySelector("#exercicio").textContent = `${person.participacao || "No cargo"} · atuando desde ${since}`;
    }
    document.querySelector("#perfil-oficial").href = person.url_perfil;
    document.querySelector("#total").textContent = money.format(summary.total_gasto);
    document.querySelector("#quantidade").textContent = `${summary.quantidade_despesas} despesas`;
    document.querySelector("#maior").textContent = money.format(summary.maior_despesa);
    document.querySelector("#maior-fornecedor").textContent = summary.maior_despesa_fornecedor || "Sem despesas";
    document.querySelector("#concentracao").textContent = `${summary.concentracao_fornecedor}%`;
    document.querySelector("#fornecedor").textContent = summary.fornecedor_principal || "Sem despesas";
    document.querySelector("#faltas").textContent = `${summary.faltas}`;
    document.querySelector("#presenca").textContent = `${summary.percentual_presenca}% de presença`;
    document.querySelector("#justificadas").textContent = summary.faltas_justificadas;
    document.querySelector("#projetos").textContent = `${summary.projetos}`;
    document.querySelector("#projetos-mes").textContent = `${summary.projetos_tramitando} em tramitação · ${summary.autorias} autorias no total`;
    document.querySelector("#ver-projetos").href = `projetos.html?id=${encodeURIComponent(senatorId)}`;
    document.querySelector("#categoria").textContent = summary.categoria_principal || "Sem despesas";
    document.querySelector("#categoria-valor").textContent = money.format(summary.categoria_principal_valor);
    document.querySelector("#fornecedor-fato").textContent = summary.fornecedor_principal || "Sem despesas";
    document.querySelector("#fornecedor-valor").textContent = money.format(summary.fornecedor_principal_valor);
    document.querySelector("#ver-todas").href = `despesas.html?id=${encodeURIComponent(senatorId)}&criterio=total_gasto`;
    document.querySelector("#ver-fornecedor").href = `despesas.html?id=${encodeURIComponent(senatorId)}&criterio=concentracao_fornecedor`;
    document.querySelector("#ver-frequencia").href = `frequencia.html?id=${encodeURIComponent(senatorId)}`;
    document.querySelector("#fonte").href = data.fonte;
    renderExpenseCharts(expensesData.despesas);
    renderAttendance(summary);
    renderProjects(projectsData.projetos);
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
