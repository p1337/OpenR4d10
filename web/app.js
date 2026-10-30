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
  renderLibrary(catalog);
}

function libraryButton(label, action, extra) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", () => sendControl(action, extra));
  return button;
}

function renderLibrary(catalog) {
  const stations = Array.isArray(catalog?.stations) ? catalog.stations : [];
  const stationList = byId("station-list");
  stationList.replaceChildren();
  for (const station of stations) {
    const row = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${station.name} · ${station.source}`;
    const actions = document.createElement("span");
    actions.className = "library-actions";
    actions.append(
      libraryButton("Play", "station_play", { station_id: station.id }),
      libraryButton("Löschen", "station_delete", { station_id: station.id }),
    );
    row.append(label, actions);
    stationList.append(row);
  }
  if (!stations.length) {
    const row = document.createElement("li");
    row.textContent = "Noch keine Sender gespeichert.";
    stationList.append(row);
  }

  const media = Array.isArray(catalog?.media) ? catalog.media : [];
  const mediaList = byId("media-list");
  mediaList.replaceChildren();
  for (const item of media) {
    const row = document.createElement("li");
    const label = document.createElement("span");
    const size = Number.isFinite(item.size_bytes)
      ? `${(item.size_bytes / 1024 / 1024).toFixed(1)} MB`
      : "Größe unbekannt";
    label.textContent = `${item.title} · ${size}`;
    row.append(label, libraryButton("Play", "media_play", { media_id: item.id }));
    mediaList.append(row);
  }
  if (!media.length) {
    const row = document.createElement("li");
    row.textContent = "Noch keine lokalen Audiodateien eingelesen.";
    mediaList.append(row);
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

async function sendControl(action, extra = {}) {
  const output = byId("control-result");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    output.textContent = `${payload.playback?.state || "stopped"} · ${payload.recording?.state || "stopped"}`;
    await refresh();
  } catch (error) {
    output.textContent = `Fehler: ${error.message}`;
  }
}

byId("media-control").addEventListener("submit", (event) => {
  event.preventDefault();
  sendControl("play", { source: byId("media-source").value, service_id: "webradio" });
});

byId("station-control").addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendControl("station_add", {
    name: byId("station-name").value,
    source: byId("station-url").value,
  });
  event.currentTarget.reset();
});

byId("media-scan").addEventListener("click", () => sendControl("media_scan"));

for (const button of document.querySelectorAll("[data-action]")) {
  button.addEventListener("click", () => {
    const action = button.dataset.action;
    const extra = action === "record_start" ? { source: byId("media-source").value } : {};
    sendControl(action, extra);
  });
}

byId("feed-control").addEventListener("submit", async (event) => {
  event.preventDefault();
  const output = byId("feed-results");
  output.replaceChildren();
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "feed_fetch", url: byId("feed-url").value }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    for (const item of payload.feed.items.slice(0, 10)) {
      const row = document.createElement("li");
      row.textContent = item.title || item.summary || "Ohne Titel";
      output.append(row);
    }
  } catch (error) {
    const row = document.createElement("li");
    row.textContent = `Fehler: ${error.message}`;
    output.append(row);
  }
});

byId("camera-control").addEventListener("submit", async (event) => {
  event.preventDefault();
  const image = byId("camera-preview");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "camera_snapshot", url: byId("camera-url").value, slot: 1 }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    image.src = `/api/camera/1?t=${Date.now()}`;
    image.hidden = false;
    image.alt = `Kamerabild ${payload.camera.width} × ${payload.camera.height}`;
  } catch (error) {
    image.hidden = true;
    byId("control-result").textContent = `Kamerafehler: ${error.message}`;
  }
});

refresh();
window.setInterval(refresh, 2000);
