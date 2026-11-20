const filter = document.querySelector(".filter");
if (filter) {
  filter.hidden = false;
  const query = filter.querySelector("input");
  const normalize = value => value.normalize("NFKC").toLowerCase().replaceAll("ё", "е").trim();
  const items = [...document.querySelectorAll("[data-item]")].map(element => ({
    element,
    text: normalize(element.textContent)
  }));
  query.addEventListener("input", () => {
    const words = normalize(query.value).split(/\s+/);
    let visible = 0;
    for (const {element, text} of items) {
      element.hidden = !words.every(word => text.includes(word));
      if (!element.hidden) visible++;
    }
    for (const group of document.querySelectorAll("[data-group]")) {
      group.hidden = !group.querySelector("[data-item]:not([hidden])");
    }
    document.querySelector("#count").textContent = query.value.trim()
      ? (visible ? `Найдено записей: ${visible}` : "Совпадений нет.")
      : "";
  });
}
const preview = document.createElement("div");
preview.className = "term-preview";
preview.id = "wiki-term-preview";
preview.setAttribute("role", "tooltip");
preview.hidden = true;
document.body.append(preview);
let activeLink;
function hidePreview() {
  activeLink?.removeAttribute("aria-describedby");
  preview.hidden = true;
  activeLink = null;
}
function showPreview(link) {
  hidePreview();
  activeLink = link;
  preview.textContent = link.dataset.preview;
  preview.hidden = false;
  link.setAttribute("aria-describedby", preview.id);
  const bounds = link.getBoundingClientRect();
  preview.style.left = Math.max(8,Math.min(bounds.left, innerWidth-preview.offsetWidth-8))+"px";
  const above = bounds.top-preview.offsetHeight-7;
  preview.style.top = (above >= 8 ? above : Math.min(bounds.bottom+7,innerHeight-preview.offsetHeight-8))+"px";
}
for (const link of document.querySelectorAll("a[data-preview]")) {
  link.addEventListener("pointerenter", event => {
    if (event.pointerType !== "touch") showPreview(link);
  });
  link.addEventListener("focus", () => showPreview(link));
  link.addEventListener("pointerleave", hidePreview);
  link.addEventListener("blur", hidePreview);
}
document.addEventListener("keydown", event => { if(event.key === "Escape") hidePreview(); });
window.addEventListener("scroll", hidePreview, {passive:true});
window.addEventListener("resize", hidePreview);
function showLinkedStep() {
  const section = document.getElementById(location.hash.slice(1));
  if (section?.matches(".guide-layout details")) section.open = true;
}
window.addEventListener("hashchange", showLinkedStep);
showLinkedStep();
const damageForm = document.querySelector(".damage-calculator");
if (damageForm) {
  damageForm.addEventListener("submit", event => event.preventDefault());
  damageForm.addEventListener("input", () => {
    const output = damageForm.querySelector("output");
    if (!damageForm.checkValidity()) {
      output.value = "Введите целые числа в каждое поле.";
      return;
    }
    const values = new FormData(damageForm);
    const raw = (2 * Number(values.get("atk")) + 5) * Math.sqrt(Number(values.get("hp"))) /
      (Number(values.get("def")) + 5 + Math.sqrt(Number(values.get("land"))));
    output.value = `Удар ${Math.floor(raw)} · Контратака ${Math.floor(raw / 3)}`;
  });
}
const eddaPlanner = document.querySelector(".edda-planner");
if (eddaPlanner) {
  const map = document.querySelector(".edda-map");
  const select = eddaPlanner.querySelector("select");
  const lands = Array.from(select.options);
  const capture = eddaPlanner.querySelector("[data-capture]");
  const undo = eddaPlanner.querySelector("[data-undo]");
  const route = [0];
  function showEddaRoute() {
    let power = 16;
    const log = eddaPlanner.querySelector("ol");
    log.replaceChildren();
    for (const id of route.slice(1)) {
      const land = lands.find(option => Number(option.value) === id);
      power -= Number(land.dataset.power);
      const entry = document.createElement("li");
      entry.textContent = land.textContent + " · мощь Эдды " + power;
      log.append(entry);
    }
    const finished = power <= 2;
    for (const link of map.querySelectorAll("[data-land]")) {
      link.classList.toggle("held", route.includes(Number(link.dataset.land)));
    }
    select.replaceChildren(...lands.filter(option => !route.includes(Number(option.value)) &&
      option.dataset.roads.split(",").some(id => route.includes(Number(id)))));
    select.disabled = capture.disabled = finished || !select.options.length;
    undo.disabled = route.length === 1;
    const stage = finished ? "Достигнут порог финала главы." : power <= 11 ?
      "Достигнут порог встречи с эйнхериями." : "Встреча с эйнхериями открывается при 11.";
    eddaPlanner.querySelector("[role=status]").textContent = "Мощь Эдды " + power + ". " + stage;
  }
  capture.addEventListener("click", () => { route.push(Number(select.value)); showEddaRoute(); });
  undo.addEventListener("click", () => { route.pop(); showEddaRoute(); });
  showEddaRoute();
  eddaPlanner.hidden = false;
}
