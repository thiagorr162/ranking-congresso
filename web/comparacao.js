const comparisonNumber = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const comparisonMoney = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const comparisonInterval = 4500;
let comparisonsRequest;
const runningComparisons = new WeakMap();

function loadComparisons() {
  comparisonsRequest ??= fetch("comparacoes.json").then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
  return comparisonsRequest;
}

async function startComparisons(target, amount) {
  if (!target) return;
  runningComparisons.get(target)?.abort();
  const controller = new AbortController();
  runningComparisons.set(target, controller);
  target.hidden = true;
  if (!(amount > 0)) return;
  let items;
  try {
    items = (await loadComparisons()).filter((item) => amount >= item.valor);
  } catch (error) {
    console.error(error);
    return;
  }
  if (controller.signal.aborted || !items.length) return;

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

  const { signal } = controller;
  target.addEventListener("mouseenter", pause, { signal });
  target.addEventListener("mouseleave", play, { signal });
  link.addEventListener("focus", pause, { signal });
  link.addEventListener("blur", play, { signal });
  signal.addEventListener("abort", pause);

  show();
  play();
}
