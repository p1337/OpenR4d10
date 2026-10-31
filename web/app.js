const byId = (id) => document.getElementById(id);
const SUPPORTED_LOCALES = new Set(["en", "de", "pl", "fr", "es"]);
const LOCALE_STORAGE_KEY = "openr4d10.web.language";
let translations = {};
let currentLocale = "en";
let latestStatus = null;
let latestDeviceState = null;
let presetSignature = "";
let weatherSignature = "";
let weatherAnimationFrames = [];
let weatherAnimationIndex = 0;
let latestWeather = null;
let weatherRefreshPending = false;
let serviceSearchQuery = "";

function t(key, variables = {}) {
  const template = translations[currentLocale]?.[key] ?? translations.en?.[key] ?? key;
  return String(template).replace(/\{\{([a-z_]+)\}\}/g, (_match, name) => String(variables[name] ?? ""));
}

function applyTranslations() {
  document.documentElement.lang = currentLocale;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const element of document.querySelectorAll("[data-i18n-placeholder]")) {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  }
  for (const element of document.querySelectorAll("[data-i18n-aria-label]")) {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  }
  for (const element of document.querySelectorAll("[data-i18n-alt]")) {
    element.alt = t(element.dataset.i18nAlt);
  }
}

function preferredLocale() {
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (SUPPORTED_LOCALES.has(saved)) return saved;
  } catch (_error) {
    // A blocked localStorage must not prevent the local dashboard from loading.
  }
  for (const candidate of navigator.languages || [navigator.language]) {
    const language = String(candidate || "").toLowerCase().split("-", 1)[0];
    if (SUPPORTED_LOCALES.has(language)) return language;
  }
  return "en";
}

function setLocale(locale, persist = true) {
  currentLocale = SUPPORTED_LOCALES.has(locale) ? locale : "en";
  byId("language-select").value = currentLocale;
  if (persist) {
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, currentLocale);
    } catch (_error) {
      // The selected language still applies for this page view.
    }
  }
  applyTranslations();
  presetSignature = "";
  weatherSignature = "";
  if (latestStatus) render(latestStatus);
}

async function initializeI18n() {
  try {
    const response = await fetch("/i18n.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (!Array.isArray(payload?.locales) || !payload.messages || typeof payload.messages !== "object") {
      throw new Error("invalid translation catalog");
    }
    const localeIndexes = new Map(payload.locales.map((locale, index) => [locale, index]));
    if ([...SUPPORTED_LOCALES].some((locale) => !localeIndexes.has(locale))) {
      throw new Error("incomplete translation locale list");
    }
    translations = Object.fromEntries([...SUPPORTED_LOCALES].map((locale) => [locale, {}]));
    for (const [key, values] of Object.entries(payload.messages)) {
      if (!Array.isArray(values) || values.length !== payload.locales.length) continue;
      for (const locale of SUPPORTED_LOCALES) {
        translations[locale][key] = values[localeIndexes.get(locale)];
      }
    }
  } catch (_error) {
    translations = {};
  }
  setLocale(preferredLocale(), false);
}

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
  setText("device-screen-status", t("240 × 280 · live"));
});
byId("device-screen-preview").addEventListener("error", () => {
  setText("device-screen-status", t("Native view unavailable"));
});

function setText(id, value, fallback = "–") {
  byId(id).textContent = value === null || value === undefined || value === "" ? fallback : String(value);
}

function formatUptime(seconds) {
  if (!Number.isFinite(seconds)) return "–";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return t("{{days}} d {{hours}} h", { days, hours });
  if (hours) return t("{{hours}} h {{minutes}} min", { hours, minutes });
  return t("{{minutes}} minutes", { minutes });
}

function adapterLabel(value) {
  const labels = {
    system: t("System data"),
    command: t("Connected"),
    file: t("File output"),
    whisplay: "Whisplay LCD",
    unconfigured: t("Not configured"),
    unknown: t("Unknown"),
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
    ready: t("Ready"),
    configuration_required: t("Configuration required"),
    missing_dependency: t("Package missing"),
    adapter_error: t("Adapter unavailable"),
    disabled: t("Disabled"),
  };
  return labels[value] || value;
}

function normalizedSearchText(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase(currentLocale);
}

function serviceMatchesSearch(service, detail) {
  const query = normalizedSearchText(serviceSearchQuery.trim());
  if (!query) return true;
  const metadata = [
    JSON.stringify(service),
    t(service.name),
    t(service.description),
    readinessLabel(service.readiness),
    detail,
  ].join(" ");
  return normalizedSearchText(metadata).includes(query);
}

function renderServices(catalog) {
  const list = byId("service-list");
  const items = Array.isArray(catalog?.items) ? catalog.items : [];
  list.replaceChildren();
  setText("service-count", items.length
    ? t("{{ready}}/{{total}} ready", { ready: catalog.ready, total: catalog.total })
    : t("No data"));
  let visibleCount = 0;
  items.forEach((service, index) => {
    const detailText = service.missing_executables?.length
      ? t("Missing: {{items}}", { items: service.missing_executables.join(", ") })
      : service.implementation === "native"
        ? t("OpenR4d10 Core")
        : service.implementation === "official_api"
          ? t("Official login required")
          : t("Local adapter");
    if (!serviceMatchesSearch(service, detailText)) return;
    visibleCount += 1;

    const row = document.createElement("li");
    row.className = "service-row";
    row.dataset.readiness = service.readiness;

    const mark = document.createElement("span");
    mark.className = "service-row-mark";
    mark.textContent = initials(t(service.name));

    const heading = document.createElement("div");
    heading.className = "service-row-heading";
    const name = document.createElement("strong");
    name.textContent = t(service.name);
    const state = document.createElement("span");
    state.textContent = readinessLabel(service.readiness);
    heading.append(name, state);

    const description = document.createElement("p");
    description.textContent = t(service.description);
    const detail = document.createElement("small");
    detail.textContent = detailText;
    const copy = document.createElement("div");
    copy.className = "service-row-copy";
    copy.append(heading, description, detail);
    const actions = document.createElement("div");
    actions.className = "service-row-actions";
    const up = libraryButton("↑", "service_move", { service_id: service.service_id, direction: -1 });
    const down = libraryButton("↓", "service_move", { service_id: service.service_id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === items.length - 1;
    actions.append(up, down);
    if (service.service_id !== "system") {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.textContent = service.enabled ? t("Disable") : t("Enable");
      toggle.addEventListener("click", () => sendControl("service_set_enabled", {
        service_id: service.service_id,
        enabled: !service.enabled,
      }));
      actions.append(toggle);
    }
    row.append(mark, copy, actions);
    list.append(row);
  });
  if (!visibleCount) {
    const empty = document.createElement("li");
    empty.className = "service-list-empty";
    empty.textContent = t("No services match this search.");
    list.append(empty);
  }
  renderPresets(catalog);
  renderLibrary(catalog);
  renderWeather(catalog);
}

byId("service-search").addEventListener("input", (event) => {
  serviceSearchQuery = event.target.value;
  if (latestStatus?.services) renderServices(latestStatus.services);
});

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
    setText("weather-frame-time", t("No frames in the local cache yet"));
    return;
  }
  const frame = weatherAnimationFrames[weatherAnimationIndex % weatherAnimationFrames.length];
  image.src = frame.url;
  image.hidden = false;
  empty.hidden = true;
  setText("weather-frame-time", t("{{timestamp}} · frame {{current}}/{{total}}", {
    timestamp: frame.timestamp,
    current: weatherAnimationIndex + 1,
    total: weatherAnimationFrames.length,
  }));
}

function renderWeather(catalog) {
  const weather = catalog?.weather || {};
  const channels = Array.isArray(weather.channels) ? weather.channels : [];
  latestWeather = weather;
  const selected = channels.find((item) => item.id === weather.active_channel_id) || channels[0] || null;
  const signature = JSON.stringify([channels, weather.active_channel_id]);
  if (signature !== weatherSignature) {
    weatherSignature = signature;
    setText("weather-channel-name", selected?.name, t("No weather channel"));
    setText("weather-provider", selected?.provider, "DWD");
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
    bbox.textContent = Array.isArray(channel.bbox)
      ? t("S/W/N/E {{bbox}}", { bbox: channel.bbox.join(" / ") })
      : t("Region not configured");
    copy.append(name, bbox);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const up = libraryButton("↑", "weather_channel_move", { channel_id: channel.id, direction: -1 });
    const down = libraryButton("↓", "weather_channel_move", { channel_id: channel.id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === channels.length - 1;
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = t("Show");
    open.addEventListener("click", () => weatherCommand("weather_open", { channel_id: channel.id }, true));
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = t("Edit");
    edit.addEventListener("click", () => editWeatherChannel(channel));
    actions.append(open, up, down, edit, libraryButton(t("Delete"), "weather_channel_delete", { channel_id: channel.id }));
    row.append(copy, actions);
    list.append(row);
  });
  if (!channels.length) {
    const row = document.createElement("li");
    row.textContent = t("No weather channels configured.");
    list.append(row);
  }
  const weatherPanel = document.querySelector('[data-tab-panel="weather"]');
  if (weatherPanel && !weatherPanel.hidden && selected && !selected.frames?.length) {
    window.setTimeout(ensureWeatherFrames, 0);
  }
}

async function weatherCommand(action, extra = {}, refreshFrames = false) {
  const output = byId("weather-status");
  output.textContent = refreshFrames ? t("Refreshing DWD images …") : t("Saving change …");
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
        output.textContent = t("{{frames}} DWD frames ready locally.", { frames: body.frames });
      });
    } else {
      output.textContent = t("Weather configuration saved.");
    }
    await refresh();
  } catch (error) {
    output.textContent = t("Weather error: {{message}}", { message: error.message });
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
  const feeds = Array.isArray(presets.feeds) ? presets.feeds : [];
  const signature = JSON.stringify(feeds);
  if (signature === presetSignature) return;
  presetSignature = signature;
  const feedSelect = byId("feed-preset");
  const selected = feedSelect.value;
  feedSelect.replaceChildren(new Option(t("Select news source …"), ""));
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
      image.alt = t("Artwork for {{station}}", { station: station.name });
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
    const play = libraryButton(t("Play"), "station_play", { station_id: station.id });
    play.classList.add("library-play");
    up.disabled = index === 0;
    down.disabled = index === stations.length - 1;
    actions.append(
      play,
      up,
      down,
      libraryButton(t("Delete"), "station_delete", { station_id: station.id }),
    );
    row.append(artwork, label, actions);
    stationList.append(row);
  });
  if (!stations.length) {
    const row = document.createElement("li");
    row.textContent = t("No stations saved yet.");
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
      : t("Size unknown");
    label.textContent = `${item.title} · ${size}`;
    row.append(label, libraryButton(t("Play"), "media_play", { media_id: item.id }));
    mediaList.append(row);
  }
  if (!media.length) {
    const row = document.createElement("li");
    row.textContent = t("No local audio files scanned yet.");
    mediaList.append(row);
  }
}

function render(data) {
  latestStatus = data;
  const frame = data.frame || {};
  const fields = frame.fields || {};
  const receiver = fields.receiver || {};
  const power = fields.power || {};
  const adapters = data.adapters || {};
  const severity = frame.severity || "info";
  const displayOpen = adapters.display === "unconfigured";
  const powerOpen = adapters.power === "unconfigured";

  let heroTitle = t("OpenR4d10 is ready.");
  let heroCopy = t("All configured services provide current data.");
  if (displayOpen && powerOpen) {
    heroTitle = t("System online. Display and power are not configured yet.");
    heroCopy = t("The web interface is running. Display and power are waiting for verified hardware adapters.");
  } else if (displayOpen) {
    heroTitle = t("System online. Display is not configured yet.");
    heroCopy = t("The web interface and power query are running; the display adapter is not configured yet.");
  } else if (powerOpen) {
    heroTitle = t("System and display online. Power telemetry is not configured yet.");
    heroCopy = t("The Whisplay is connected. Only verified PiSugar telemetry is still missing.");
  }

  byId("connection").dataset.state = "online";
  setText("connection-label", t("Service connected"));
  setText("hero-title", heroTitle);
  setText("hero-copy", heroCopy);
  setText("hostname", receiver.hostname, "OpenR4d10");
  setText("updated", frame.timestamp ? new Date(frame.timestamp).toLocaleString(currentLocale) : t("just now"));
  setText("version", `v${data.version || "–"}`);

  setText("receiver-state", receiver.state === "online" ? t("Online") : adapterLabel(adapters.receiver));
  setText("receiver-detail", receiver.hostname
    ? t("Source: {{hostname}}", { hostname: receiver.hostname })
    : t("Status source active"));
  setText("power-state", power.state === "unconfigured" ? t("PiSugar present") : t(power.state));
  setText(
    "power-detail",
    adapters.power === "unconfigured"
      ? t("Battery operation confirmed · telemetry not configured")
      : t("PiSugar telemetry connected")
  );
  setText("display-state", adapters.display === "unconfigured" ? t("Headless") : t("Connected"));
  setText("display-detail", adapters.display === "unconfigured"
    ? t("Whisplay adapter missing")
    : t("Backend: {{backend}}", { backend: adapters.display }));
  setText("uptime", formatUptime(receiver.uptime_seconds));
  setText("load", receiver.load_1m);

  setText("screen-title", t(frame.title || "Service is starting"));
  setText("screen-body", t(frame.body || "Please wait a moment."));
  byId("status-orb").dataset.severity = severity;
  setAdapter("receiver-adapter", adapters.receiver);
  setAdapter("display-adapter", adapters.display);
  setAdapter("power-adapter", adapters.power);
  setText("footer-status", t("Last updated: {{time}}", { time: new Date().toLocaleTimeString(currentLocale) }));
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
    ? t("Update queued …")
    : state === "running"
      ? t("Update running …")
      : state === "rebooting"
        ? t("Restarting …")
        : t("Install update");
  const suffix = update.version ? t(" · version {{version}}", { version: update.version }) : "";
  setText("update-status", `${t(update.message || "No update is running.")}${suffix}`);
}

function renderDeviceState(state) {
  if (!state) return;
  latestDeviceState = state;
  setText("device-volume", Number.isInteger(state.volume) ? `${state.volume}%` : null);
  setText("device-squelch", state.squelch);
  setText("device-channel", Number.isInteger(state.channel) ? String(state.channel).padStart(3, "0") : null);
  setText("device-service", state.service);
  const pttButton = byId("ptt-button");
  pttButton.setAttribute("aria-pressed", state.ptt_active ? "true" : "false");
  setText(
    "device-ptt",
    state.ptt_active
      ? t("PTT active")
      : state.ptt_context_active
        ? t("PTT service ready")
        : state.menu_open
          ? t("Backspace = back one menu level")
          : t("No active PTT service")
  );
}

function renderOffline() {
  byId("connection").dataset.state = "offline";
  setText("connection-label", t("Service unavailable"));
  setText("hero-title", t("Connection interrupted"));
  setText("hero-copy", t("The interface is waiting for the OpenR4d10 service."));
  setText("footer-status", t("Retrying …"));
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
      output.textContent = payload.enabled ? t("Service enabled.") : t("Service disabled.");
    } else if (Number.isInteger(payload.scanned)) {
      output.textContent = t("{{count}} media files scanned.", { count: payload.scanned });
    } else if (Number.isInteger(payload.station_id)) {
      output.textContent = t("Station saved.");
    } else if (typeof payload.deleted === "boolean") {
      output.textContent = payload.deleted ? t("Entry deleted.") : t("Entry not found.");
    } else if (typeof payload.moved === "boolean") {
      output.textContent = payload.moved ? t("Order saved.") : t("Entry is already at the edge of the list.");
    } else {
      output.textContent = `${payload.playback?.state || "stopped"} · ${payload.recording?.state || "stopped"}`;
    }
    await refresh();
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
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
  status.textContent = t("Saving brightness …");
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
    status.textContent = t("Display brightness {{brightness}}% saved permanently.", { brightness: saved });
  } catch (error) {
    status.textContent = t("Error: {{message}}", { message: error.message });
    await refresh();
  } finally {
    displayBrightness.disabled = false;
  }
});

byId("system-update").addEventListener("click", async () => {
  if (!window.confirm(t("Install the latest OpenR4d10 version? The device will restart automatically afterwards."))) return;
  const button = byId("system-update");
  const output = byId("update-status");
  button.disabled = true;
  output.textContent = t("Requesting update …");
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
    output.textContent = t("Update error: {{message}}", { message: error.message });
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
      output.textContent = t("Channel {{channel}} · {{name}}", {
        channel: payload.selected_preset.channel,
        name: payload.selected_preset.name,
      });
    } else if (payload.playback && request.control === "left_outer") {
      output.textContent = t("Playback volume {{volume}}%", { volume: payload.playback.volume });
    } else if (payload.playback && request.control === "right_press") {
      output.textContent = payload.playback.paused
        ? t("Playback paused")
        : t("Playback running");
    } else {
      output.textContent = request.control === "ptt"
        ? (state.ptt_active ? t("PTT active") : state.menu_open ? t("Backspace = Back") : t("Input accepted"))
        : `${state.service || t("Device")} · ${state.title || t("Input accepted")}`;
    }
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
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

function keyboardDeviceRequest(code) {
  const request = keyboardDeviceInputs[code];
  if (!request) return null;
  if (latestDeviceState?.menu_open && request.control === "right_outer") {
    return { ...request, steps: -request.steps };
  }
  return request;
}

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
  if (event.code === "Backspace") {
    event.preventDefault();
    if (!event.repeat) setPttInput(true);
    return;
  }
  const request = keyboardDeviceRequest(event.code);
  if (!request) return;
  event.preventDefault();
  if (event.repeat && !Object.hasOwn(request, "steps")) return;
  postDeviceInput(request);
});

document.addEventListener("keyup", (event) => {
  if (event.code !== "Backspace") return;
  if (isEditableTarget(event.target) && !pttKeyActive) return;
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
        link.textContent = item.title || item.summary || t("Untitled");
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        row.append(link);
      } else {
        row.textContent = item.title || item.summary || t("Untitled");
      }
      output.append(row);
    }
  } catch (error) {
    const row = document.createElement("li");
    row.textContent = t("Error: {{message}}", { message: error.message });
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
    byId("control-result").textContent = t("Please select a news source first.");
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
    image.alt = t("Camera image {{width}} × {{height}}", {
      width: payload.camera.width,
      height: payload.camera.height,
    });
  } catch (error) {
    image.hidden = true;
    byId("control-result").textContent = t("Camera error: {{message}}", { message: error.message });
  }
});

byId("weather-refresh").addEventListener("click", () => {
  const channels = Array.isArray(latestWeather?.channels) ? latestWeather.channels : [];
  const selected = channels.find((item) => item.id === latestWeather?.active_channel_id) || channels[0];
  if (!selected) {
    byId("weather-status").textContent = t("Create a weather channel first.");
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
  byId("weather-status").textContent = t("A new region can now be created.");
});

byId("language-select").addEventListener("change", (event) => {
  setLocale(event.currentTarget.value);
});

initializeI18n().finally(() => {
  refresh();
  window.setInterval(refresh, 2000);
  window.setInterval(() => {
    if (!weatherAnimationFrames.length) return;
    weatherAnimationIndex = (weatherAnimationIndex + 1) % weatherAnimationFrames.length;
    showWeatherFrame();
  }, 1400);
});
