const comparisonNumber = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const comparisonMoney = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const comparisonInterval = 4500;
let comparisonsRequest;

function loadComparisons() {
  comparisonsRequest ??= fetch("comparacoes.json").then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
  return comparisonsRequest;
}

async function startComparisons(target, amount) {
  if (!target || !(amount > 0)) return;
  let items;
  try {
    items = await loadComparisons();
  } catch (error) {
    console.error(error);
    return;
  }

  const link = document.createElement("a");
  link.target = "_blank";
  link.rel = "noreferrer";
  target.replaceChildren(link);
  target.hidden = false;

  let index = 0;
  let timer = null;
  const show = () => {
    const item = items[index];
    const count = Math.floor(amount / item.valor);
    link.href = item.url;
    link.title = `${item.referencia}: ${comparisonMoney.format(item.valor)} · Fonte: ${item.fonte}`;
    link.innerHTML = `equivalente a <strong>${comparisonNumber.format(count)}</strong> ${count === 1 ? item.singular : item.plural}`;
  };
  const play = () => {
    if (timer || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    timer = window.setInterval(() => {
      index = (index + 1) % items.length;
      show();
    }, comparisonInterval);
  };
  const pause = () => {
    window.clearInterval(timer);
    timer = null;
  };

  target.addEventListener("mouseenter", pause);
  target.addEventListener("mouseleave", play);
  link.addEventListener("focus", pause);
  link.addEventListener("blur", play);

  show();
  play();
}
