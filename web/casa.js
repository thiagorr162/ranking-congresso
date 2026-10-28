const CASAS = {
  camara: {
    pasta: "deputados",
    menu: "Deputados",
    singular: "deputado",
    plural: "deputados",
    rotulo: "DEPUTADO",
    orgao: "Câmara dos Deputados",
    pelo: "pela Câmara",
    dadosAbertos: "https://dadosabertos.camara.leg.br/",
    temJustificativas: false,
    rotuloFalta: "Sem presença registrada",
    faltas: "Sessões deliberativas do Plenário sem presença registrada.",
    sessoes: "Sessões deliberativas do Plenário.",
  },
  senado: {
    pasta: "senadores",
    menu: "Senadores",
    singular: "senador",
    plural: "senadores",
    rotulo: "SENADOR",
    orgao: "Senado Federal",
    pelo: "pelo Senado",
    dadosAbertos: "https://www12.senado.leg.br/dados-abertos/",
    temJustificativas: true,
    rotuloFalta: "Não compareceu",
    faltas: "Sessões em que o Senado registrou “Não compareceu”.",
    sessoes: "Sessões deliberativas com votação nominal.",
  },
};

const casaParam = new URLSearchParams(window.location.search).get("casa");
const CASA_ID = casaParam in CASAS ? casaParam : "camara";
const CASA = CASAS[CASA_ID];

function pageUrl(page, params = {}) {
  return `${page}?${new URLSearchParams({ casa: CASA_ID, ...params })}`;
}

function dataUrl(path) {
  return `data/${CASA.pasta}${path ? `/${path}` : ".json"}`;
}

function renderNav() {
  const nav = document.querySelector("#nav-casas");
  if (!nav) return;
  nav.innerHTML = Object.entries(CASAS).map(([id, casa]) =>
    `<a${id === CASA_ID ? ' class="active"' : ""} href="${id === "camara" ? "./" : `./?casa=${id}`}">${casa.menu}</a>`
  ).join("");
  document.querySelectorAll("[data-orgao]").forEach((element) => { element.textContent = CASA.orgao; });
  document.querySelectorAll("[data-rotulo-falta]").forEach((element) => { element.textContent = CASA.rotuloFalta; });
  document.querySelectorAll("[data-so-senado]").forEach((element) => { element.hidden = !CASA.temJustificativas; });
}

renderNav();
