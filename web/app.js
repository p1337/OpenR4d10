const byId = (id) => document.getElementById(id);

function setText(id, value, fallback = "–") {
  byId(id).textContent = value === null || value === undefined || value === "" ? fallback : String(value);
}

function formatUptime(seconds) {
  if (!Number.isFinite(seconds)) return "–";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days} T ${hours} Std`;
  if (hours) return `${hours} Std ${minutes} Min`;
  return `${minutes} Minuten`;
}

function adapterLabel(value) {
  const labels = {
    system: "Systemdaten",
    command: "Verbunden",
    file: "Dateiausgabe",
    whisplay: "Whisplay LCD",
    unconfigured: "Noch offen",
    unknown: "Unbekannt",
  };
  return labels[value] || value;
}

function setAdapter(id, value) {
  const element = byId(id);
  element.textContent = adapterLabel(value);
  element.dataset.state = value === "unconfigured" ? "open" : "ready";
}

function readinessLabel(value) {
  const labels = {
    ready: "Bereit",
    configuration_required: "Konfiguration nötig",
    missing_dependency: "Paket fehlt",
  };
  return labels[value] || value;
}

function renderServices(catalog) {
  const grid = byId("service-grid");
  const items = Array.isArray(catalog?.items) ? catalog.items : [];
  grid.replaceChildren();
  setText("service-count", items.length ? `${catalog.ready}/${catalog.total} bereit` : "Keine Daten");
  for (const service of items) {
    const card = document.createElement("article");
    card.className = "service-card";
    card.dataset.readiness = service.readiness;

    const heading = document.createElement("div");
    heading.className = "service-card-heading";
    const name = document.createElement("strong");
    name.textContent = service.name;
    const state = document.createElement("span");
    state.textContent = readinessLabel(service.readiness);
    heading.append(name, state);

    const description = document.createElement("p");
    description.textContent = service.description;
    const detail = document.createElement("small");
    detail.textContent = service.missing_executables?.length
      ? `Fehlt: ${service.missing_executables.join(", ")}`
      : service.implementation === "native"
        ? "OpenR4d10 Core"
        : service.implementation === "official_api"
          ? "Offizielle Anmeldung erforderlich"
          : "Lokaler Adapter";
    card.append(heading, description, detail);
    grid.append(card);
  }
}

function render(data) {
  const frame = data.frame || {};
  const fields = frame.fields || {};
  const receiver = fields.receiver || {};
  const power = fields.power || {};
  const adapters = data.adapters || {};
  const severity = frame.severity || "info";
  const hardwareOpen = [adapters.display, adapters.power].includes("unconfigured");

  byId("connection").dataset.state = "online";
  setText("connection-label", "Dienst verbunden");
  setText("hero-title", hardwareOpen ? "System online. Hardware noch offen." : "OpenR4d10 ist bereit.");
  setText(
    "hero-copy",
    hardwareOpen
      ? "Die Weboberfläche läuft. Display und Energieversorgung warten noch auf verifizierte Hardwareadapter."
      : "Alle konfigurierten Dienste liefern aktuelle Daten."
  );
  setText("hostname", receiver.hostname, "OpenR4d10");
  setText("updated", frame.timestamp ? new Date(frame.timestamp).toLocaleString("de-DE") : "gerade eben");
  setText("version", `v${data.version || "–"}`);

  setText("receiver-state", receiver.state === "online" ? "Online" : adapterLabel(adapters.receiver));
  setText("receiver-detail", receiver.hostname ? `Quelle: ${receiver.hostname}` : "Statusquelle aktiv");
  setText("power-state", power.state === "unconfigured" ? "Nicht konfiguriert" : power.state);
  setText("power-detail", adapters.power === "unconfigured" ? "PiSugar-Adapter fehlt" : "Energieadapter aktiv");
  setText("display-state", adapters.display === "unconfigured" ? "Headless" : "Verbunden");
  setText("display-detail", adapters.display === "unconfigured" ? "Whisplay-Adapter fehlt" : `Backend: ${adapters.display}`);
  setText("uptime", formatUptime(receiver.uptime_seconds));
  setText("load", receiver.load_1m);

  setText("screen-title", frame.title);
  setText("screen-body", frame.body);
  byId("status-orb").dataset.severity = severity;
  setAdapter("receiver-adapter", adapters.receiver);
  setAdapter("display-adapter", adapters.display);
  setAdapter("power-adapter", adapters.power);
  setText("footer-status", `Letzte Aktualisierung: ${new Date().toLocaleTimeString("de-DE")}`);
  renderServices(data.services || {});
}

function renderOffline() {
  byId("connection").dataset.state = "offline";
  setText("connection-label", "Dienst nicht erreichbar");
  setText("hero-title", "Verbindung unterbrochen");
  setText("hero-copy", "Die Oberfläche wartet auf den OpenR4d10-Dienst.");
  setText("footer-status", "Erneuter Versuch läuft …");
  byId("status-orb").dataset.severity = "error";
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (error) {
    renderOffline();
  }
}

refresh();
window.setInterval(refresh, 2000);
