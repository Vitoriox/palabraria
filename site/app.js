const MADRID_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Europe/Madrid",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const byId = (id) => document.getElementById(id);

function setText(id, value) {
  const element = byId(id);
  if (element) element.textContent = value;
}

function capitalize(value) {
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function renderTranslation(lang, translation) {
  const term = byId(`${lang}-term`);
  const definition = byId(`${lang}-definition`);
  const badge = byId(`${lang}-badge`);
  if (!term || !definition || !badge) return;

  const hasTerm = Boolean(translation && translation.term);
  const hasDefinition = Boolean(translation && translation.definition);

  if (!hasTerm && !hasDefinition) {
    term.textContent = "Sin traducción disponible";
    term.classList.add("is-missing");
    definition.textContent = "";
    badge.hidden = true;
    return;
  }

  term.classList.toggle("is-missing", !hasTerm);
  term.textContent = hasTerm ? translation.term : "Sin equivalente directo";
  definition.textContent = translation.definition || "";

  let label = "";
  if (translation.verified) label = "Manual";
  else if (translation.provider === "deepl") label = "DeepL";

  badge.textContent = label;
  badge.hidden = !label;
  badge.classList.toggle("badge--manual", Boolean(translation.verified));
}

function renderOtherSenses(senses) {
  const wrapper = byId("other-senses-wrap");
  const list = byId("other-senses");
  if (!wrapper || !list || !Array.isArray(senses) || senses.length === 0) {
    if (wrapper) wrapper.hidden = true;
    return;
  }

  list.replaceChildren();
  for (const sense of senses) {
    if (!sense || typeof sense.definition !== "string" || !sense.definition) {
      continue;
    }
    const item = document.createElement("li");
    const prefix = sense.acepcion ? `${sense.acepcion} ` : "";
    item.textContent = `${prefix}${sense.definition}`;
    list.append(item);
  }

  if (list.children.length === 0) {
    wrapper.hidden = true;
    return;
  }

  setText(
    "other-summary",
    `Otras acepciones (${list.children.length})`
  );
  wrapper.hidden = false;
}

function renderProviderNote(translations, status) {
  const note = byId("provider-note");
  if (!note) return;

  const providers = new Set(
    Object.values(translations || {})
      .map((translation) => translation && translation.provider)
      .filter(Boolean)
  );

  let text = "";
  if (providers.has("manual") && providers.has("deepl")) {
    text = "DeepL · revisión manual";
  } else if (providers.has("manual")) {
    text = "Traducción revisada manualmente";
  } else if (providers.has("deepl")) {
    text = "Traducción automática: DeepL";
  } else if (status === "failed") {
    text = "Traducción no disponible";
  }

  note.textContent = text;
}

function render(data) {
  if (!data || typeof data.word !== "string" || !data.word.trim()) {
    throw new Error("El archivo de datos no contiene una palabra válida.");
  }

  const displayDate = data.display_date || data.date || "";
  setText("date", capitalize(displayDate));
  setText("word", data.word);

  const pos = Array.isArray(data.pos)
    ? data.pos.filter(Boolean).join(", ")
    : String(data.pos || "");
  const posElement = byId("pos");
  posElement.textContent = pos;
  posElement.hidden = !pos;

  setText("definition", data.definition || "");
  renderOtherSenses(data.other_senses);

  const translations = data.translations || {};
  renderTranslation("en", translations.en);
  renderTranslation("de", translations.de);
  renderProviderNote(translations, data.translation_status);

  const target = data.url || "https://dle.rae.es/";
  byId("word-link").href = target;
  byId("source-link").href = target;

  const note = byId("translation-note");
  if (note) {
    let noteText = "";
    if (data.translation_status === "failed") {
      noteText =
        "La traducción de hoy no está disponible. Se reintentará en la próxima actualización.";
    } else if (data.translation_status === "skipped") {
      noteText = "La traducción se añadirá en la próxima actualización.";
    } else if (!translations.en?.term || !translations.de?.term) {
      noteText = "Faltan una o más traducciones.";
    }
    note.textContent = noteText;
    note.hidden = !noteText;
  }

  const today = MADRID_DATE.format(new Date());
  const stale = byId("stale");
  if (stale) {
    const isStale = typeof data.date === "string" && data.date < today;
    stale.hidden = !isStale;
    if (isStale) {
      stale.textContent = `Estás viendo la edición del ${displayDate}. La actualización de hoy todavía no está disponible.`;
    }
  }

  document.title = `${data.word} — Palabra del día`;

  byId("loading").hidden = true;
  byId("error").hidden = true;
  byId("card").hidden = false;
}

function showError(error) {
  console.error(error);
  const loading = byId("loading");
  if (loading) loading.hidden = true;

  const message =
    error && error.status === 404
      ? "Todavía no hay datos publicados. La primera actualización creará la tarjeta."
      : "No se pudo leer el archivo de datos. Comprueba la conexión e inténtalo de nuevo.";
  setText("error-message", message);
  const errorBox = byId("error");
  if (errorBox) errorBox.hidden = false;
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
