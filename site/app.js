const byId = (id) => document.getElementById(id);
const setText = (id, value) => {
  const element = byId(id);
  if (element) element.textContent = value;
};
const capitalize = (value) =>
  value ? value.charAt(0).toUpperCase() + value.slice(1) : "";

const MADRID_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Europe/Madrid",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function todayInMadrid() {
  const parts = MADRID_DATE.formatToParts(new Date());
  const value = (type) => parts.find((part) => part.type === type).value;
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function renderTranslation(lang, translation) {
  const term = byId(`${lang}-term`);
  const definition = byId(`${lang}-definition`);
  term.textContent = translation && translation.term ? translation.term : "—";
  definition.textContent = (translation && translation.definition) || "";
}

function render(data) {
  if (!data || typeof data.word !== "string" || !data.word.trim()) {
    throw new Error("El archivo de datos no contiene una palabra válida.");
  }

  setText("date", capitalize(data.display_date || data.date || ""));
  setText("word", data.word);
  setText("definition", data.definition || "");

  const translations = data.translations || {};
  renderTranslation("en", translations.en);
  renderTranslation("de", translations.de);

  const stale = byId("stale");
  if (typeof data.date === "string" && data.date < todayInMadrid()) {
    stale.textContent = `Edición del ${data.display_date || data.date}. Hoy todavía no hay datos nuevos.`;
    stale.hidden = false;
  } else {
    stale.hidden = true;
  }

  document.title = `${data.word} — Palabra del día`;
  byId("loading").hidden = true;
  byId("error").hidden = true;
  byId("card").hidden = false;
}

function showError(error) {
  console.error(error);
  const message =
    error && error.status === 404
      ? "Todavía no hay datos publicados."
      : "No se pudo cargar la palabra. Inténtalo de nuevo.";
  setText("error-message", message);
  byId("loading").hidden = true;
  byId("error").hidden = false;
}

async function load() {
  try {
    const response = await fetch("data/latest.json", { cache: "no-store" });
    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    render(await response.json());
  } catch (error) {
    showError(error);
  }
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  const local =
    location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (location.protocol !== "https:" && !local) return;
  navigator.serviceWorker.register("sw.js").catch((error) => {
    console.warn("No se pudo registrar el service worker", error);
  });
}

load();
registerServiceWorker();
