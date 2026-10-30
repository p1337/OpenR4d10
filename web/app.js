const byId = (id) => document.getElementById(id);
let presetSignature = "";

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
    adapter_error: "Adapter nicht erreichbar",
    disabled: "Deaktiviert",
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
    if (service.service_id !== "system") {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.textContent = service.enabled ? "Deaktivieren" : "Aktivieren";
      toggle.addEventListener("click", () => sendControl("service_set_enabled", {
        service_id: service.service_id,
        enabled: !service.enabled,
      }));
      card.append(toggle);
    }
    grid.append(card);
  }
  renderPresets(catalog);
  renderLibrary(catalog);
}

function initials(value) {
  return String(value || "Radio")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join("")
    .toUpperCase();
}

function renderPresets(catalog) {
  const presets = catalog?.presets || {};
  const stations = Array.isArray(presets.stations) ? presets.stations : [];
  const feeds = Array.isArray(presets.feeds) ? presets.feeds : [];
  const signature = JSON.stringify([stations, feeds]);
  if (signature === presetSignature) return;
  presetSignature = signature;
  const grid = byId("radio-preset-grid");
  grid.replaceChildren();
  for (const station of stations) {
    const card = document.createElement("article");
    card.className = "radio-preset-card";

    const artwork = document.createElement("div");
    artwork.className = "radio-artwork";
    artwork.dataset.initials = initials(station.name);
    const image = document.createElement("img");
    image.src = station.artwork;
    image.alt = `${station.name} Senderbild`;
    image.loading = "lazy";
    image.addEventListener("load", () => artwork.classList.add("has-image"));
    image.addEventListener("error", () => image.remove());
    artwork.append(image);

    const copy = document.createElement("div");
    copy.className = "radio-preset-copy";
    const name = document.createElement("strong");
    name.textContent = station.name;
    const detail = document.createElement("span");
    detail.textContent = `${station.country} · ${station.genre}`;
    copy.append(name, detail);

    const actions = document.createElement("div");
    actions.className = "radio-preset-actions";
    actions.append(
      libraryButton("Play", "preset_play", { preset_id: station.preset_id }),
      libraryButton("Speichern", "preset_save", { preset_id: station.preset_id }),
    );
    card.append(artwork, copy, actions);
    grid.append(card);
  }
  if (!stations.length) {
    const empty = document.createElement("p");
    empty.className = "services-note";
    empty.textContent = "Die Senderliste wird geladen.";
    grid.append(empty);
  }

  const feedSelect = byId("feed-preset");
  const selected = feedSelect.value;
  feedSelect.replaceChildren(new Option("Nachrichtenquelle auswählen …", ""));
  for (const feed of feeds) {
    feedSelect.add(new Option(`${feed.name} (${feed.language})`, feed.preset_id));
  }
  if (feeds.some((feed) => feed.preset_id === selected)) feedSelect.value = selected;
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch (_error) {
    return null;
  }
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
  const displayOpen = adapters.display === "unconfigured";
  const powerOpen = adapters.power === "unconfigured";

  let heroTitle = "OpenR4d10 ist bereit.";
  let heroCopy = "Alle konfigurierten Dienste liefern aktuelle Daten.";
  if (displayOpen && powerOpen) {
    heroTitle = "System online. Display und Energie noch offen.";
    heroCopy = "Die Weboberfläche läuft. Display und Energieversorgung warten auf verifizierte Hardwareadapter.";
  } else if (displayOpen) {
    heroTitle = "System online. Display noch offen.";
    heroCopy = "Die Weboberfläche und Energieabfrage laufen; der Displayadapter ist noch nicht konfiguriert.";
  } else if (powerOpen) {
    heroTitle = "System und Display online. Energieanzeige noch offen.";
    heroCopy = "Das Whisplay ist verbunden. Nur die verifizierte PiSugar-Telemetrie fehlt noch.";
  }

  byId("connection").dataset.state = "online";
  setText("connection-label", "Dienst verbunden");
  setText("hero-title", heroTitle);
  setText("hero-copy", heroCopy);
  setText("hostname", receiver.hostname, "OpenR4d10");
  setText("updated", frame.timestamp ? new Date(frame.timestamp).toLocaleString("de-DE") : "gerade eben");
  setText("version", `v${data.version || "–"}`);

  setText("receiver-state", receiver.state === "online" ? "Online" : adapterLabel(adapters.receiver));
  setText("receiver-detail", receiver.hostname ? `Quelle: ${receiver.hostname}` : "Statusquelle aktiv");
  setText("power-state", power.state === "unconfigured" ? "PiSugar vorhanden" : power.state);
  setText(
    "power-detail",
    adapters.power === "unconfigured"
      ? "Akkubetrieb bestätigt · Messwerte noch offen"
      : "PiSugar-Telemetrie verbunden"
  );
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
  renderDeviceState(data.device_ui);
  renderServices(data.services || {});
}

function renderDeviceState(state) {
  if (!state) return;
  setText("device-volume", Number.isInteger(state.volume) ? `${state.volume}%` : null);
  setText("device-squelch", state.squelch);
  setText("device-channel", Number.isInteger(state.channel) ? String(state.channel).padStart(3, "0") : null);
  setText("device-service", state.service);
  const pttButton = byId("ptt-button");
  pttButton.setAttribute("aria-pressed", state.ptt_active ? "true" : "false");
  setText(
    "device-ptt",
    state.ptt_active
      ? "PTT-Eingabe aktiv – kein Audioadapter verbunden"
      : "Bereit – kein PTT-Dienstadapter konfiguriert"
  );
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
    if (typeof payload.enabled === "boolean") {
      output.textContent = `Dienst ${payload.enabled ? "aktiviert" : "deaktiviert"}.`;
    } else if (Number.isInteger(payload.scanned)) {
      output.textContent = `${payload.scanned} Mediendateien eingelesen.`;
    } else if (Number.isInteger(payload.station_id)) {
      output.textContent = "Sender gespeichert.";
    } else if (typeof payload.deleted === "boolean") {
      output.textContent = payload.deleted ? "Sender gelöscht." : "Sender nicht gefunden.";
    } else {
      output.textContent = `${payload.playback?.state || "stopped"} · ${payload.recording?.state || "stopped"}`;
    }
    await refresh();
  } catch (error) {
    output.textContent = `Fehler: ${error.message}`;
  }
}

async function postDeviceInput(request, button = null) {
  const output = byId("device-control-result");
  if (button) button.disabled = true;
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "device_input", ...request }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderDeviceState(payload.device_ui);
    const state = payload.device_ui || {};
    if (payload.selected_preset && request.control === "right_outer") {
      output.textContent = `Kanal ${payload.selected_preset.channel} · ${payload.selected_preset.name}`;
    } else if (payload.playback && request.control === "left_outer") {
      output.textContent = `Wiedergabelautstärke ${payload.playback.volume}%`;
    } else if (payload.playback && request.control === "right_press") {
      output.textContent = payload.playback.paused
        ? "Wiedergabe pausiert"
        : "Wiedergabe läuft";
    } else {
      output.textContent = request.control === "ptt"
        ? (state.ptt_active ? "PTT-Eingabe aktiv · kein PTT-Audioadapter verbunden" : "PTT-Eingabe beendet")
        : `${state.service || "Gerät"} · ${state.title || "Eingabe übernommen"}`;
    }
  } catch (error) {
    output.textContent = `Fehler: ${error.message}`;
  } finally {
    if (button) button.disabled = false;
  }
}

function sendDeviceInput(button) {
  const request = { control: button.dataset.deviceControl };
  if (button.dataset.steps) request.steps = Number(button.dataset.steps);
  if (button.dataset.held) request.held_seconds = Number(button.dataset.held);
  return postDeviceInput(request, button);
}

for (const button of document.querySelectorAll("[data-device-control]")) {
  button.addEventListener("click", () => sendDeviceInput(button));
}

const keyboardDeviceInputs = {
  KeyW: { control: "left_outer", steps: 1 },
  KeyS: { control: "left_outer", steps: -1 },
  KeyA: { control: "left_inner", steps: -1 },
  KeyD: { control: "left_inner", steps: 1 },
  ArrowUp: { control: "right_outer", steps: 1 },
  ArrowDown: { control: "right_outer", steps: -1 },
  ArrowLeft: { control: "right_inner", steps: -1 },
  ArrowRight: { control: "right_inner", steps: 1 },
  Space: { control: "left_press" },
  Enter: { control: "right_press" },
};

function isEditableTarget(target) {
  return target instanceof HTMLElement && (
    target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}

let pttKeyActive = false;
let pttQueue = Promise.resolve();

function setPttInput(active) {
  if (pttKeyActive === active) return;
  pttKeyActive = active;
  byId("ptt-button").setAttribute("aria-pressed", active ? "true" : "false");
  pttQueue = pttQueue
    .catch(() => undefined)
    .then(() => postDeviceInput({ control: "ptt", active }));
}

document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || isEditableTarget(event.target)) return;
  if (event.code === "KeyQ") {
    event.preventDefault();
    if (!event.repeat) setPttInput(true);
    return;
  }
  const request = keyboardDeviceInputs[event.code];
  if (!request) return;
  event.preventDefault();
  if (event.repeat && !Object.hasOwn(request, "steps")) return;
  postDeviceInput(request);
});

document.addEventListener("keyup", (event) => {
  if (event.code !== "KeyQ") return;
  event.preventDefault();
  setPttInput(false);
});

const pttButton = byId("ptt-button");
pttButton.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  pttButton.setPointerCapture?.(event.pointerId);
  setPttInput(true);
});
for (const eventName of ["pointerup", "pointercancel", "lostpointercapture"]) {
  pttButton.addEventListener(eventName, () => setPttInput(false));
}
window.addEventListener("blur", () => setPttInput(false));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) setPttInput(false);
});

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

async function loadFeed(request) {
  const output = byId("feed-results");
  const credit = byId("feed-credit");
  output.replaceChildren();
  credit.hidden = true;
  credit.replaceChildren();
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    if (payload.credit) {
      const link = document.createElement("a");
      link.href = safeExternalUrl(payload.homepage) || "#";
      link.textContent = payload.credit;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      credit.append(link);
      credit.hidden = false;
    }
    for (const item of payload.feed.items.slice(0, 10)) {
      const row = document.createElement("li");
      const itemUrl = safeExternalUrl(item.link);
      if (itemUrl) {
        const link = document.createElement("a");
        link.href = itemUrl;
        link.textContent = item.title || item.summary || "Ohne Titel";
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        row.append(link);
      } else {
        row.textContent = item.title || item.summary || "Ohne Titel";
      }
      output.append(row);
    }
  } catch (error) {
    const row = document.createElement("li");
    row.textContent = `Fehler: ${error.message}`;
    output.append(row);
  }
}

byId("feed-control").addEventListener("submit", async (event) => {
  event.preventDefault();
  await loadFeed({ action: "feed_fetch", url: byId("feed-url").value });
});

byId("feed-preset-load").addEventListener("click", () => {
  const presetId = byId("feed-preset").value;
  if (!presetId) {
    byId("control-result").textContent = "Bitte zuerst eine Nachrichtenquelle auswählen.";
    return;
  }
  loadFeed({ action: "feed_fetch_preset", preset_id: presetId });
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
