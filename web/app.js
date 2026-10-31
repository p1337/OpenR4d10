const byId = (id) => document.getElementById(id);
let presetSignature = "";
let weatherSignature = "";
let weatherAnimationFrames = [];
let weatherAnimationIndex = 0;
let latestWeather = null;
let weatherRefreshPending = false;

function activateTab(name) {
  for (const button of document.querySelectorAll("[data-tab]")) {
    button.setAttribute("aria-selected", button.dataset.tab === name ? "true" : "false");
  }
  for (const panel of document.querySelectorAll("[data-tab-panel]")) {
    panel.hidden = panel.dataset.tabPanel !== name;
  }
  if (name === "weather") ensureWeatherFrames();
}

for (const button of document.querySelectorAll("[data-tab]")) {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
}
const requestedTab = new URLSearchParams(window.location.search).get("tab");
if ([...document.querySelectorAll("[data-tab]")].some((item) => item.dataset.tab === requestedTab)) {
  activateTab(requestedTab);
}

function refreshDeviceScreen() {
  const image = byId("device-screen-preview");
  image.src = `/api/device-screen.png?t=${Date.now()}`;
}

byId("device-screen-preview").addEventListener("load", () => {
  setText("device-screen-status", "240 × 280 · live");
});
byId("device-screen-preview").addEventListener("error", () => {
  setText("device-screen-status", "Native Ansicht nicht verfügbar");
});

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
  items.forEach((service, index) => {
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
    const actions = document.createElement("div");
    actions.className = "service-card-actions";
    const up = libraryButton("↑", "service_move", { service_id: service.service_id, direction: -1 });
    const down = libraryButton("↓", "service_move", { service_id: service.service_id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === items.length - 1;
    actions.append(up, down);
    if (service.service_id !== "system") {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.textContent = service.enabled ? "Deaktivieren" : "Aktivieren";
      toggle.addEventListener("click", () => sendControl("service_set_enabled", {
        service_id: service.service_id,
        enabled: !service.enabled,
      }));
      actions.append(toggle);
    }
    card.append(actions);
    grid.append(card);
  });
  renderPresets(catalog);
  renderLibrary(catalog);
  renderWeather(catalog);
}

function setWeatherAnimation(frames) {
  weatherAnimationFrames = Array.isArray(frames) ? frames : [];
  weatherAnimationIndex = 0;
  showWeatherFrame();
}

function showWeatherFrame() {
  const image = byId("weather-image");
  const empty = byId("weather-empty");
  if (!weatherAnimationFrames.length) {
    image.hidden = true;
    empty.hidden = false;
    setText("weather-frame-time", "Noch keine Frames im lokalen Cache");
    return;
  }
  const frame = weatherAnimationFrames[weatherAnimationIndex % weatherAnimationFrames.length];
  image.src = frame.url;
  image.hidden = false;
  empty.hidden = true;
  setText("weather-frame-time", `${frame.timestamp} · Frame ${weatherAnimationIndex + 1}/${weatherAnimationFrames.length}`);
}

function renderWeather(catalog) {
  const weather = catalog?.weather || {};
  const channels = Array.isArray(weather.channels) ? weather.channels : [];
  latestWeather = weather;
  const selected = channels.find((item) => item.id === weather.active_channel_id) || channels[0] || null;
  const signature = JSON.stringify([channels, weather.active_channel_id]);
  if (signature !== weatherSignature) {
    weatherSignature = signature;
    setText("weather-channel-name", selected?.name, "Kein Wetterkanal");
    setWeatherAnimation(selected?.frames || []);
  }
  const list = byId("weather-channel-list");
  list.replaceChildren();
  channels.forEach((channel, index) => {
    const row = document.createElement("li");
    if (channel.id === weather.active_channel_id) row.dataset.active = "true";
    const copy = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = `${channel.channel}. ${channel.name}`;
    const bbox = document.createElement("small");
    bbox.textContent = Array.isArray(channel.bbox) ? `S/W/N/O ${channel.bbox.join(" / ")}` : "Ausschnitt nicht konfiguriert";
    copy.append(name, bbox);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const up = libraryButton("↑", "weather_channel_move", { channel_id: channel.id, direction: -1 });
    const down = libraryButton("↓", "weather_channel_move", { channel_id: channel.id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === channels.length - 1;
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Anzeigen";
    open.addEventListener("click", () => weatherCommand("weather_open", { channel_id: channel.id }, true));
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "Ändern";
    edit.addEventListener("click", () => editWeatherChannel(channel));
    actions.append(open, up, down, edit, libraryButton("Löschen", "weather_channel_delete", { channel_id: channel.id }));
    row.append(copy, actions);
    list.append(row);
  });
  if (!channels.length) {
    const row = document.createElement("li");
    row.textContent = "Keine Wetterkanäle konfiguriert.";
    list.append(row);
  }
  const weatherPanel = document.querySelector('[data-tab-panel="weather"]');
  if (weatherPanel && !weatherPanel.hidden && selected && !selected.frames?.length) {
    window.setTimeout(ensureWeatherFrames, 0);
  }
}

async function weatherCommand(action, extra = {}, refreshFrames = false) {
  const output = byId("weather-status");
  output.textContent = refreshFrames ? "DWD-Bilder werden aktualisiert …" : "Änderung wird gespeichert …";
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    if (refreshFrames) {
      await fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "weather_refresh", channel_id: payload.channel_id || extra.channel_id }),
      }).then(async (item) => {
        const body = await item.json();
        if (!item.ok) throw new Error(body.error || `HTTP ${item.status}`);
        output.textContent = `${body.frames} DWD-Frames lokal bereit.`;
      });
    } else {
      output.textContent = "Wetterkonfiguration gespeichert.";
    }
    await refresh();
  } catch (error) {
    output.textContent = `Wetterfehler: ${error.message}`;
  } finally {
    weatherRefreshPending = false;
  }
}

function ensureWeatherFrames() {
  if (weatherRefreshPending) return;
  const channels = Array.isArray(latestWeather?.channels) ? latestWeather.channels : [];
  const selected = channels.find((item) => item.id === latestWeather?.active_channel_id) || channels[0];
  if (!selected || selected.frames?.length) return;
  weatherRefreshPending = true;
  weatherCommand("weather_open", { channel_id: selected.id }, true);
}

function editWeatherChannel(channel) {
  byId("weather-channel-id").value = String(channel.id);
  byId("weather-channel-name-input").value = channel.name;
  const bbox = Array.isArray(channel.bbox) ? channel.bbox : ["", "", "", ""];
  ["weather-south", "weather-west", "weather-north", "weather-east"].forEach((id, index) => {
    byId(id).value = String(bbox[index] ?? "");
  });
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
  const stations = Array.isArray(catalog?.stations) ? catalog.stations : [];
  const feeds = Array.isArray(presets.feeds) ? presets.feeds : [];
  const signature = JSON.stringify([stations, feeds]);
  if (signature === presetSignature) return;
  presetSignature = signature;
  const grid = byId("radio-preset-grid");
  grid.replaceChildren();
  stations.forEach((station, index) => {
    const card = document.createElement("article");
    card.className = "radio-preset-card";

    const artwork = document.createElement("div");
    artwork.className = "radio-artwork";
    artwork.dataset.initials = initials(station.name);
    if (station.artwork) {
      const image = document.createElement("img");
      image.src = station.artwork;
      image.alt = `${station.name} Senderbild`;
      image.loading = "lazy";
      image.addEventListener("load", () => artwork.classList.add("has-image"));
      image.addEventListener("error", () => image.remove());
      artwork.append(image);
    }

    const copy = document.createElement("div");
    copy.className = "radio-preset-copy";
    const name = document.createElement("strong");
    name.textContent = station.name;
    const detail = document.createElement("span");
    detail.textContent = `${station.country} · ${station.genre}`;
    copy.append(name, detail);

    const actions = document.createElement("div");
    actions.className = "radio-preset-actions";
    const up = libraryButton("↑", "station_move", { station_id: station.id, direction: -1 });
    const down = libraryButton("↓", "station_move", { station_id: station.id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === stations.length - 1;
    actions.append(
      libraryButton("Play", "station_play", { station_id: station.id }),
      up,
      down,
      libraryButton("Löschen", "station_delete", { station_id: station.id }),
    );
    card.append(artwork, copy, actions);
    grid.append(card);
  });
  if (!stations.length) {
    const empty = document.createElement("p");
    empty.className = "services-note";
    empty.textContent = "Die Senderliste ist leer. Unten kann ein Sender angelegt werden.";
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
  stations.forEach((station, index) => {
    const row = document.createElement("li");
    const artwork = document.createElement("div");
    artwork.className = "station-row-artwork";
    artwork.dataset.initials = initials(station.name);
    if (station.artwork) {
      const image = document.createElement("img");
      image.src = station.artwork;
      image.alt = `${station.name} Senderbild`;
      image.loading = "lazy";
      image.addEventListener("error", () => image.remove());
      artwork.append(image);
    }
    const label = document.createElement("span");
    label.className = "station-row-copy";
    const name = document.createElement("strong");
    name.textContent = station.name;
    const detail = document.createElement("small");
    detail.textContent = `${station.country} · ${station.genre}`;
    label.append(name, detail);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const up = libraryButton("↑", "station_move", { station_id: station.id, direction: -1 });
    const down = libraryButton("↓", "station_move", { station_id: station.id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === stations.length - 1;
    actions.append(
      libraryButton("Play", "station_play", { station_id: station.id }),
      up,
      down,
      libraryButton("Löschen", "station_delete", { station_id: station.id }),
    );
    row.append(artwork, label, actions);
    stationList.append(row);
  });
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
  renderUpdate(data.update || {});
  renderDeviceState(data.device_ui);
  renderServices(data.services || {});
  renderSettings(data.services?.settings || {});
}

function renderSettings(settings) {
  const brightness = settings.display_brightness_percent;
  if (!Number.isInteger(brightness) || brightness < 0 || brightness > 100) return;
  const input = byId("display-brightness");
  if (document.activeElement !== input) input.value = String(brightness);
  setText("display-brightness-value", `${input.value}%`);
}

function renderUpdate(update) {
  const state = update.state || "idle";
  const busy = ["queued", "running", "rebooting"].includes(state);
  const button = byId("system-update");
  button.disabled = busy;
  button.textContent = state === "queued"
    ? "Update wartet …"
    : state === "running"
      ? "Update läuft …"
      : state === "rebooting"
        ? "Neustart läuft …"
        : "Update installieren";
  const suffix = update.version ? ` · Version ${update.version}` : "";
  setText("update-status", `${update.message || "Kein Update läuft."}${suffix}`);
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
      ? "PTT aktiv"
      : state.ptt_context_active
        ? "PTT-Dienst bereit"
        : state.menu_open
          ? "PTT / Q = eine Menüebene zurück"
          : "Kein aktiver PTT-Dienst"
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
    refreshDeviceScreen();
  } catch (error) {
    renderOffline();
  }
}

async function sendControl(action, extra = {}) {
  const output = action.startsWith("weather_") ? byId("weather-status") : byId("control-result");
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
      output.textContent = payload.deleted ? "Eintrag gelöscht." : "Eintrag nicht gefunden.";
    } else if (typeof payload.moved === "boolean") {
      output.textContent = payload.moved ? "Reihenfolge gespeichert." : "Eintrag ist bereits am Listenrand.";
    } else {
      output.textContent = `${payload.playback?.state || "stopped"} · ${payload.recording?.state || "stopped"}`;
    }
    await refresh();
  } catch (error) {
    output.textContent = `Fehler: ${error.message}`;
  }
}

const displayBrightness = byId("display-brightness");
displayBrightness.addEventListener("input", () => {
  setText("display-brightness-value", `${displayBrightness.value}%`);
});
displayBrightness.addEventListener("change", async () => {
  const status = byId("display-brightness-status");
  const brightness = Number(displayBrightness.value);
  displayBrightness.disabled = true;
  status.textContent = "Helligkeit wird gespeichert …";
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "display_brightness",
        brightness_percent: brightness,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    const saved = payload.settings?.display_brightness_percent;
    displayBrightness.value = String(saved);
    setText("display-brightness-value", `${saved}%`);
    status.textContent = `Displayhelligkeit ${saved}% dauerhaft gespeichert.`;
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
    await refresh();
  } finally {
    displayBrightness.disabled = false;
  }
});

byId("system-update").addEventListener("click", async () => {
  if (!window.confirm("Aktuelle OpenR4d10-Version installieren? Das Gerät startet danach automatisch neu.")) return;
  const button = byId("system-update");
  const output = byId("update-status");
  button.disabled = true;
  output.textContent = "Update wird angefordert …";
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "system_update", confirmed: true }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderUpdate(payload.update || {});
  } catch (error) {
    output.textContent = `Updatefehler: ${error.message}`;
    button.disabled = false;
  }
});

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
    refreshDeviceScreen();
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
        ? (state.ptt_active ? "PTT aktiv" : state.menu_open ? "PTT / Q = Zurück" : "Eingabe übernommen")
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

byId("weather-refresh").addEventListener("click", () => {
  const channels = Array.isArray(latestWeather?.channels) ? latestWeather.channels : [];
  const selected = channels.find((item) => item.id === latestWeather?.active_channel_id) || channels[0];
  if (!selected) {
    byId("weather-status").textContent = "Zuerst einen Wetterkanal anlegen.";
    return;
  }
  weatherRefreshPending = true;
  weatherCommand("weather_open", { channel_id: selected.id }, true);
});

byId("weather-channel-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const rawId = byId("weather-channel-id").value;
  const request = {
    name: byId("weather-channel-name-input").value,
    bbox: ["weather-south", "weather-west", "weather-north", "weather-east"].map((id) => Number(byId(id).value)),
  };
  if (rawId) request.channel_id = Number(rawId);
  await weatherCommand("weather_channel_save", request);
  event.currentTarget.reset();
  byId("weather-channel-id").value = "";
});

byId("weather-channel-cancel").addEventListener("click", () => {
  byId("weather-channel-form").reset();
  byId("weather-channel-id").value = "";
  byId("weather-status").textContent = "Neuer Ausschnitt kann angelegt werden.";
});

refresh();
window.setInterval(refresh, 2000);
window.setInterval(() => {
  if (!weatherAnimationFrames.length) return;
  weatherAnimationIndex = (weatherAnimationIndex + 1) % weatherAnimationFrames.length;
  showWeatherFrame();
}, 1400);
