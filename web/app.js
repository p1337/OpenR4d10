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
let stationSearchQuery = "";
let stationLanguageFilter = "";
let stationCategoryFilter = "";
let stationLibraryView = "active";
let podcastSearchQuery = "";
let brandmeisterTalkgroups = [];
let brandmeisterCatalog = [];
let brandmeisterCatalogQuery = "";
let brandmeisterCatalogSignature = "";
let brandmeisterReceiver = null;

const BRANDMEISTER_FLAGS = new Map([
  ["204", "🇳🇱"], ["208", "🇫🇷"], ["214", "🇪🇸"], ["222", "🇮🇹"],
  ["228", "🇨🇭"], ["232", "🇦🇹"], ["234", "🇬🇧"], ["235", "🇬🇧"],
  ["260", "🇵🇱"], ["262", "🇩🇪"], ["268", "🇵🇹"], ["302", "🇨🇦"],
  ["310", "🇺🇸"], ["311", "🇺🇸"], ["312", "🇺🇸"], ["313", "🇺🇸"],
  ["314", "🇺🇸"], ["315", "🇺🇸"], ["316", "🇺🇸"], ["505", "🇦🇺"],
]);

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

function solixMetricText(service) {
  if (service.service_id !== "anker_solix") return "";
  const metrics = service.adapter?.metrics;
  if (!metrics || typeof metrics !== "object") return "";
  const values = [
    ["solar_w", "PV", "W"],
    ["home_w", t("Home"), "W"],
    ["grid_w", t("Grid"), "W"],
    ["battery_w", t("Battery"), "W"],
    ["battery_percent", t("Battery"), "%"],
    ["energy_today_kwh", t("Today"), "kWh"],
  ];
  return values
    .filter(([key]) => Number.isFinite(metrics[key]))
    .map(([key, label, unit]) => `${label} ${metrics[key]} ${unit}`)
    .join(" · ");
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
    const metricText = solixMetricText(service);
    if (metricText) {
      const metrics = document.createElement("small");
      metrics.className = "service-row-metrics";
      metrics.textContent = metricText;
      copy.append(metrics);
    }
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
  renderAmbient(catalog);
  renderWebcams(catalog);
  renderBrandmeisterTalkgroups(catalog.brandmeister || {});
  renderPodcasts(catalog);
  renderWeather(catalog);
  renderPlaybackActions(catalog.playback || {});
}

function renderPlaybackActions(playback) {
  const running = playback.state === "playing" && playback.paused !== true;
  for (const button of document.querySelectorAll('[data-action="pause"], [data-music-action="pause"]')) {
    button.textContent = t(running ? "Pause" : "Play");
    button.classList.toggle("play-action", !running);
    button.classList.toggle("accent-action", running);
  }
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

function renderRadioBuffer(buffer) {
  const state = buffer || {};
  const continuous = byId("radio-continuous");
  if (document.activeElement !== continuous) continuous.checked = state.continuous === true;
  let message = t("Waiting for a radio stream.");
  if (state.state === "connecting") message = t("Connecting the song buffer …");
  if (state.state === "buffering") {
    const track = state.artist && state.title
      ? `${state.artist} – ${state.title}`
      : state.stream_title || t("Title metadata is not available yet.");
    message = state.keep_current
      ? t("This song will be saved: {{track}}", { track })
      : t("Song buffer active: {{track}}", { track });
  }
  if (state.state === "error") message = t("Song buffer error: {{message}}", { message: state.error || "–" });
  setText("radio-buffer-status", message);
}

function stationMatchesFilters(station) {
  if (stationLanguageFilter && station.language !== stationLanguageFilter) return false;
  if (stationCategoryFilter && !station.categories?.includes(stationCategoryFilter)) return false;
  const query = normalizedSearchText(stationSearchQuery.trim());
  if (!query) return true;
  return normalizedSearchText([
    station.name,
    station.country,
    station.genre,
    station.language,
    station.description,
    ...(station.categories || []),
  ].join(" ")).includes(query);
}

function languageName(code) {
  try {
    return new Intl.DisplayNames([currentLocale], { type: "language" }).of(code) || code.toUpperCase();
  } catch (_error) {
    return code.toUpperCase();
  }
}

function stationRow(station, actions) {
  const row = document.createElement("li");
  row.dataset.language = station.language || "";
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
  const language = station.language ? languageName(station.language) : "–";
  detail.textContent = `${language} · ${station.country} · ${station.genre}`;
  label.append(name, detail);
  row.append(artwork, label, actions);
  return row;
}

function selectStationLibraryView(view) {
  stationLibraryView = view === "catalog" ? "catalog" : "active";
  const active = stationLibraryView === "active";
  byId("station-active-tab").setAttribute("aria-selected", active ? "true" : "false");
  byId("station-catalog-tab").setAttribute("aria-selected", active ? "false" : "true");
  byId("station-active-panel").hidden = !active;
  byId("station-catalog-panel").hidden = active;
}

function renderLibrary(catalog) {
  const stations = Array.isArray(catalog?.stations) ? catalog.stations : [];
  const presets = Array.isArray(catalog?.presets?.stations) ? catalog.presets.stations : [];
  const languages = [...new Set(presets.map((item) => item.language).filter(Boolean))].sort();
  const categories = [...new Set(presets.flatMap((item) => item.categories || []))].sort();
  const languageSelect = byId("station-language");
  const categorySelect = byId("station-category");
  const currentLanguage = stationLanguageFilter;
  const currentCategory = stationCategoryFilter;
  languageSelect.replaceChildren(new Option(t("All languages"), ""));
  for (const language of languages) languageSelect.add(new Option(languageName(language), language));
  categorySelect.replaceChildren(new Option(t("All categories"), ""));
  for (const category of categories) categorySelect.add(new Option(t(category), category));
  languageSelect.value = languages.includes(currentLanguage) ? currentLanguage : "";
  categorySelect.value = categories.includes(currentCategory) ? currentCategory : "";

  const stationList = byId("station-list");
  stationList.replaceChildren();
  const visibleStations = stations.filter(stationMatchesFilters);
  visibleStations.forEach((station) => {
    const index = stations.indexOf(station);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const up = libraryButton("↑", "station_move", { station_id: station.id, direction: -1 });
    const down = libraryButton("↓", "station_move", { station_id: station.id, direction: 1 });
    const play = libraryButton(t("Play"), "station_play", { station_id: station.id });
    play.classList.add("library-play");
    play.classList.add("play-action");
    up.disabled = index === 0;
    down.disabled = index === stations.length - 1;
    actions.append(
      play,
      up,
      down,
      libraryButton(t(station.preset_id ? "Deactivate" : "Delete"), "station_delete", { station_id: station.id }),
    );
    stationList.append(stationRow(station, actions));
  });
  setText("active-station-count", `${visibleStations.length} / ${stations.length}`);
  if (!visibleStations.length) {
    const row = document.createElement("li");
    row.textContent = t(stations.length ? "No stations match these filters." : "No stations saved yet.");
    stationList.append(row);
  }

  const activePresetIds = new Set(stations.map((item) => item.preset_id).filter(Boolean));
  const available = presets
    .filter((preset) => !activePresetIds.has(preset.preset_id))
    .filter(stationMatchesFilters)
    .sort((left, right) => (
      left.language.localeCompare(right.language) || left.name.localeCompare(right.name)
    ));
  const catalogList = byId("station-catalog-list");
  catalogList.replaceChildren();
  for (const preset of available) {
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const activate = document.createElement("button");
    activate.type = "button";
    activate.textContent = t("Activate");
    activate.classList.add("library-play");
    activate.addEventListener("click", async () => {
      if (await sendControl("preset_save", { preset_id: preset.preset_id })) {
        selectStationLibraryView("active");
      }
    });
    actions.append(activate);
    catalogList.append(stationRow(preset, actions));
  }
  const totalAvailable = presets.filter((preset) => !activePresetIds.has(preset.preset_id)).length;
  setText("catalog-station-count", `${available.length} / ${totalAvailable}`);
  if (!available.length) {
    const row = document.createElement("li");
    row.textContent = t(totalAvailable ? "No stations match these filters." : "All catalog stations are active.");
    catalogList.append(row);
  }
  selectStationLibraryView(stationLibraryView);

  const media = Array.isArray(catalog?.media) ? catalog.media : [];
  const mediaList = byId("media-list");
  mediaList.replaceChildren();
  let currentMediaFolder = null;
  for (const item of media) {
    const folder = typeof item.folder === "string" && item.folder ? item.folder : "Music";
    if (folder !== currentMediaFolder) {
      const heading = document.createElement("li");
      heading.className = "media-folder-row";
      heading.textContent = folder.replaceAll("/", " / ");
      mediaList.append(heading);
      currentMediaFolder = folder;
    }
    const row = document.createElement("li");
    row.className = "media-library-row";
    const artwork = document.createElement("div");
    artwork.className = "media-row-artwork";
    artwork.dataset.initials = initials(item.artist || item.title);
    if (item.cover) {
      const image = document.createElement("img");
      image.src = item.cover;
      image.alt = t("Cover for {{track}}", { track: item.title });
      image.loading = "lazy";
      image.addEventListener("error", () => image.remove());
      artwork.append(image);
    }
    const label = document.createElement("span");
    label.className = "media-row-copy";
    const size = Number.isFinite(item.size_bytes)
      ? `${(item.size_bytes / 1024 / 1024).toFixed(1)} MB`
      : t("Size unknown");
    const title = document.createElement("strong");
    title.textContent = item.artist ? `${item.artist} – ${item.title}` : item.title;
    const detail = document.createElement("small");
    detail.textContent = item.review_required ? `${size} · ${t("Check title")}` : size;
    label.append(title, detail);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const favorite = libraryButton(item.favorite ? "★" : "☆", "media_favorite", {
      media_id: item.id,
      favorite: !item.favorite,
    });
    favorite.classList.add("favorite-button");
    favorite.setAttribute("aria-label", item.favorite ? t("Remove favorite") : t("Add favorite"));
    const play = libraryButton(t("Play"), "media_play", { media_id: item.id });
    play.classList.add("library-play");
    play.classList.add("play-action");
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = t("Delete");
    remove.addEventListener("click", () => {
      if (window.confirm(t("Delete {{track}} permanently?", { track: title.textContent }))) {
        sendControl("media_delete", { media_id: item.id, confirmed: true });
      }
    });
    actions.append(favorite, play, remove);
    row.append(artwork, label, actions);
    mediaList.append(row);
  }
  if (!media.length) {
    const row = document.createElement("li");
    row.textContent = t("No local audio files scanned yet.");
    mediaList.append(row);
  }
}

function podcastButton(label, action, extra, primary = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  if (primary) button.classList.add("library-play");
  if (action === "podcast_play") button.classList.add("play-action");
  button.addEventListener("click", () => podcastCommand(action, extra));
  return button;
}

function renderPodcasts(catalog) {
  const podcasts = catalog?.podcasts || {};
  const subscriptions = Array.isArray(podcasts.subscriptions) ? podcasts.subscriptions : [];
  const subscriptionList = byId("podcast-subscription-list");
  subscriptionList.replaceChildren();
  subscriptions.forEach((subscription, index) => {
    const row = document.createElement("li");
    if (subscription.selected) row.dataset.active = "true";
    const copy = document.createElement("span");
    copy.className = "station-row-copy";
    const name = document.createElement("strong");
    name.textContent = subscription.name;
    const detail = document.createElement("small");
    detail.textContent = subscription.episode_count === null
      ? `${subscription.source} · ${t("Not loaded yet")}`
      : `${subscription.source} · ${t("{{count}} episodes", { count: subscription.episode_count })}`;
    copy.append(name, detail);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const up = podcastButton("↑", "podcast_move", { subscription_id: subscription.id, direction: -1 });
    const down = podcastButton("↓", "podcast_move", { subscription_id: subscription.id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === subscriptions.length - 1;
    actions.append(
      podcastButton(t("Update"), "podcast_refresh", { subscription_id: subscription.id }, true),
      up,
      down,
      podcastButton(t("Remove"), "podcast_unsubscribe", { subscription_id: subscription.id }),
    );
    row.append(copy, actions);
    subscriptionList.append(row);
  });
  setText("podcast-subscription-count", subscriptions.length);
  if (!subscriptions.length) {
    const row = document.createElement("li");
    row.textContent = t("No podcast subscriptions yet.");
    subscriptionList.append(row);
  }

  const query = normalizedSearchText(podcastSearchQuery.trim());
  const episodes = (Array.isArray(podcasts.episodes) ? podcasts.episodes : []).filter((episode) => (
    !query || normalizedSearchText([
      episode.title, episode.summary, episode.published, episode.duration,
    ].join(" ")).includes(query)
  ));
  const episodeList = byId("podcast-episode-list");
  episodeList.replaceChildren();
  for (const episode of episodes) {
    const row = document.createElement("li");
    const copy = document.createElement("span");
    copy.className = "station-row-copy";
    const title = document.createElement("strong");
    title.textContent = episode.title;
    const detail = document.createElement("small");
    detail.textContent = [episode.published, episode.duration].filter(Boolean).join(" · ");
    const summary = document.createElement("p");
    summary.textContent = episode.summary;
    copy.append(title, detail, summary);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    actions.append(podcastButton(t("Play"), "podcast_play", {
      subscription_id: podcasts.selected_subscription_id,
      episode_id: episode.episode_id,
    }, true));
    row.append(copy, actions);
    episodeList.append(row);
  }
  setText("podcast-episode-count", episodes.length);
  if (!episodes.length) {
    const row = document.createElement("li");
    row.textContent = t(subscriptions.length
      ? "Select Update on a subscription to load its episodes."
      : "Subscribe to a public podcast feed first.");
    episodeList.append(row);
  }
}

async function podcastCommand(action, extra = {}) {
  const output = byId("podcast-status");
  output.textContent = t("Working …");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    output.textContent = Number.isInteger(payload.episode_count)
      ? t("{{count}} episodes loaded.", { count: payload.episode_count })
      : action === "podcast_play"
        ? t("Episode is playing.")
        : action === "podcast_unsubscribe"
          ? t("Subscription removed.")
          : t("Podcast change saved.");
    await refresh();
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
  }
}

function ambientButton(label, action, extra, primary = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  if (primary) button.classList.add("library-play");
  if (action === "ambient_play") button.classList.add("play-action");
  button.addEventListener("click", () => ambientCommand(action, extra));
  return button;
}

function renderAmbient(catalog) {
  const scenes = Array.isArray(catalog?.ambient?.scenes) ? catalog.ambient.scenes : [];
  const list = byId("ambient-scene-list");
  list.replaceChildren();
  scenes.forEach((scene, index) => {
    const row = document.createElement("li");
    if (scene.active) row.dataset.active = "true";
    const artwork = document.createElement("span");
    artwork.className = "station-row-artwork ambient-row-artwork";
    artwork.dataset.initials = initials(scene.name);
    if (scene.artwork) {
      const image = document.createElement("img");
      image.src = scene.artwork;
      image.alt = "";
      image.loading = "eager";
      artwork.append(image);
    }
    const copy = document.createElement("span");
    copy.className = "station-row-copy";
    const name = document.createElement("strong");
    name.textContent = t(scene.name);
    const description = document.createElement("small");
    description.textContent = t(scene.description || "Custom ambient scene");
    const attribution = document.createElement("small");
    attribution.className = "ambient-attribution";
    if (scene.source_page) {
      const source = document.createElement("a");
      source.href = scene.source_page;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = scene.credit || t("Source");
      attribution.append(source);
    } else {
      attribution.textContent = scene.credit || t("User source");
    }
    if (scene.license_url) {
      attribution.append(document.createTextNode(" · "));
      const license = document.createElement("a");
      license.href = scene.license_url;
      license.target = "_blank";
      license.rel = "noopener noreferrer";
      license.textContent = scene.license_name || t("License");
      attribution.append(license);
    }
    copy.append(name, description, attribution);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const up = ambientButton("↑", "ambient_scene_move", { scene_id: scene.id, direction: -1 });
    const down = ambientButton("↓", "ambient_scene_move", { scene_id: scene.id, direction: 1 });
    up.disabled = index === 0;
    down.disabled = index === scenes.length - 1;
    actions.append(
      ambientButton(scene.active ? t("Play / Pause") : t("Play"), scene.active ? "ambient_toggle" : "ambient_play", { scene_id: scene.id }, true),
      up,
      down,
      ambientButton(t("Delete"), "ambient_scene_delete", { scene_id: scene.id }),
    );
    row.append(artwork, copy, actions);
    list.append(row);
  });
  setText("ambient-scene-count", scenes.length);
  if (!scenes.length) {
    const row = document.createElement("li");
    row.textContent = t("No soundscapes configured.");
    list.append(row);
  }

  const layers = Array.isArray(catalog?.ambient?.layers)
    ? catalog.ambient.layers.filter((item) => item.id !== "__save_favorite__")
    : [];
  const layerList = byId("ambient-layer-list");
  layerList.replaceChildren();
  const activeLayers = layers.filter((item) => item.enabled).length;
  setText("ambient-layer-count", `${activeLayers} / ${catalog?.ambient?.max_active_layers || 2}`);
  layers.forEach((layer) => {
    const row = document.createElement("li");
    if (layer.enabled) row.dataset.active = "true";
    const copy = document.createElement("span");
    copy.className = "station-row-copy";
    const name = document.createElement("strong");
    name.textContent = t(layer.name);
    const description = document.createElement("small");
    description.textContent = t(layer.description);
    copy.append(name, description);
    const actions = document.createElement("span");
    actions.className = "library-actions ambient-layer-actions";
    const toggle = ambientButton(
      layer.enabled ? t("On") : t("Off"),
      "ambient_layer_set",
      { layer_id: layer.id, enabled: !layer.enabled },
      layer.enabled,
    );
    const minus = ambientButton("−10", "ambient_layer_set", {
      layer_id: layer.id,
      volume: Math.max(0, layer.volume - 10),
    });
    const level = document.createElement("strong");
    level.className = "ambient-layer-level";
    level.textContent = `${layer.volume}%`;
    const plus = ambientButton("+10", "ambient_layer_set", {
      layer_id: layer.id,
      volume: Math.min(100, layer.volume + 10),
    });
    minus.disabled = layer.volume <= 0;
    plus.disabled = layer.volume >= 100;
    actions.append(toggle, minus, level, plus);
    row.append(copy, actions);
    layerList.append(row);
  });
}

async function ambientCommand(action, extra = {}) {
  const output = byId("ambient-status");
  output.textContent = t("Working …");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    output.textContent = action === "ambient_play" || action === "ambient_toggle"
      ? t("Soundscape playback changed.")
      : action === "ambient_scene_delete"
        ? t("Soundscape deleted.")
        : t("Soundscape change saved.");
    await refresh();
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
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
  setText(
    "power-state",
    Number.isInteger(power.battery_percent)
      ? `${power.battery_percent}%`
      : power.state === "unconfigured"
        ? t("PiSugar present")
        : t(power.state)
  );
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
  renderWifiRepair(data.wifi_repair || {});
  renderDeviceState(data.device_ui);
  renderServices(data.services || {});
  renderSettings(data.services?.settings || {});
  renderRadioBuffer(data.services?.radio_buffer || {});
}

function renderSettings(settings) {
  const language = settings.language;
  if (SUPPORTED_LOCALES.has(language) && language !== currentLocale) {
    setLocale(language);
  }
  const brightness = settings.display_brightness_percent;
  if (Number.isInteger(brightness) && brightness >= 0 && brightness <= 100) {
    const input = byId("display-brightness");
    if (document.activeElement !== input) input.value = String(brightness);
    setText("display-brightness-value", `${input.value}%`);
  }
  const accent = settings.accent_color;
  if (typeof accent === "string" && /^#[0-9a-f]{6}$/i.test(accent)) {
    const color = byId("display-accent-color");
    if (document.activeElement !== color) color.value = accent;
    document.documentElement.style.setProperty("--cyan", accent);
  }
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

function renderWifiRepair(repair) {
  const state = repair.state || "idle";
  const busy = ["queued", "running"].includes(state);
  const button = byId("wifi-repair-submit");
  button.disabled = busy;
  button.textContent = state === "queued"
    ? t("Wi-Fi repair queued …")
    : state === "running"
      ? t("Connecting Wi-Fi …")
      : t("Repair and connect Wi-Fi");
  setText("wifi-repair-status", t(repair.message || "No Wi-Fi repair is running."));
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
    } else if (payload.radio_buffer) {
      output.textContent = payload.radio_buffer.keep_current
        ? t("The current song will be saved at its next title boundary.")
        : t("Recording mode saved.");
    } else {
      output.textContent = `${payload.playback?.state || "stopped"} · ${payload.recording?.state || "stopped"}`;
    }
    await refresh();
    return true;
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
    return false;
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

async function saveDisplayAppearance() {
  const color = byId("display-accent-color");
  const status = byId("display-appearance-status");
  color.disabled = true;
  status.textContent = t("Saving appearance …");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "display_appearance",
        accent_color: color.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderSettings(payload.settings || {});
    status.textContent = t("Appearance saved permanently.");
  } catch (error) {
    status.textContent = t("Error: {{message}}", { message: error.message });
    await refresh();
  } finally {
    color.disabled = false;
  }
}

byId("display-accent-color").addEventListener("change", saveDisplayAppearance);

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

byId("wifi-repair-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const ssidInput = byId("wifi-ssid");
  const passphraseInput = byId("wifi-passphrase");
  const replaceExisting = byId("wifi-replace-existing").checked;
  const confirmed = byId("wifi-confirm").checked;
  if (!confirmed) return;
  if (!window.confirm(t("Apply this Wi-Fi configuration now? The browser connection may close."))) return;
  const button = byId("wifi-repair-submit");
  const output = byId("wifi-repair-status");
  button.disabled = true;
  output.textContent = t("Requesting Wi-Fi repair …");
  const request = {
    action: "wifi_repair",
    ssid: ssidInput.value,
    passphrase: passphraseInput.value,
    replace_existing: replaceExisting,
    confirmed: true,
  };
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderWifiRepair(payload.wifi_repair || {});
  } catch (error) {
    output.textContent = t("Wi-Fi repair error: {{message}}", { message: error.message });
    button.disabled = false;
  } finally {
    request.passphrase = "";
    passphraseInput.value = "";
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
  ArrowUp: { control: "right_outer", steps: -1 },
  ArrowDown: { control: "right_outer", steps: 1 },
  ArrowLeft: { control: "right_inner", steps: -1 },
  ArrowRight: { control: "right_inner", steps: 1 },
  Space: { control: "left_press" },
  Enter: { control: "right_press" },
};

function keyboardDeviceRequest(code) {
  return keyboardDeviceInputs[code] || null;
}

function isEditableTarget(target) {
  return target instanceof HTMLElement && (
    target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}

function deviceMenuOwnsArrowKey(code) {
  return latestDeviceState?.menu_open === true
    && ["ArrowUp", "ArrowDown"].includes(code);
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
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  if (isEditableTarget(event.target) && !deviceMenuOwnsArrowKey(event.code)) return;
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

byId("station-control").addEventListener("submit", async (event) => {
  event.preventDefault();
  const saved = await sendControl("station_add", {
    name: byId("station-name").value,
    source: byId("station-url").value,
  });
  if (saved) {
    byId("station-name").value = "";
    byId("station-url").value = "";
    selectStationLibraryView("active");
  }
});

for (const button of document.querySelectorAll("[data-station-view]")) {
  button.addEventListener("click", () => selectStationLibraryView(button.dataset.stationView));
}

byId("station-search").addEventListener("input", (event) => {
  stationSearchQuery = event.currentTarget.value;
  if (latestStatus?.services) renderLibrary(latestStatus.services);
});
byId("station-language").addEventListener("change", (event) => {
  stationLanguageFilter = event.currentTarget.value;
  if (latestStatus?.services) renderLibrary(latestStatus.services);
});
byId("station-category").addEventListener("change", (event) => {
  stationCategoryFilter = event.currentTarget.value;
  if (latestStatus?.services) renderLibrary(latestStatus.services);
});

byId("podcast-subscribe-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await podcastCommand("podcast_subscribe", { url: byId("podcast-feed-url").value });
  event.currentTarget.reset();
});

byId("ambient-scene-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await ambientCommand("ambient_scene_save", {
    name: byId("ambient-scene-name").value,
    source: byId("ambient-scene-url").value,
  });
  event.currentTarget.reset();
});

byId("ambient-favorite-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = byId("ambient-favorite-name").value.trim();
  await ambientCommand("ambient_favorite_save", name ? { name } : {});
  byId("ambient-favorite-name").value = "";
});

function brandmeisterFlag(talkgroup) {
  const text = String(talkgroup);
  return BRANDMEISTER_FLAGS.get(text.slice(0, 3)) || "🌐";
}

function selectedBrandmeisterTalkgroups() {
  return brandmeisterTalkgroups.filter((item) => item.enabled).map((item) => item.talkgroup);
}

function chooseBrandmeisterReplacement() {
  const active = brandmeisterTalkgroups.filter((item) => item.enabled);
  if (active.length < 5) return undefined;
  const choices = active
    .map((item, index) => `${index + 1}: TG ${item.talkgroup} · ${item.name}`)
    .join("\n");
  const answer = window.prompt(
    `${t("Five talkgroups are active. Which one should be replaced?")}\n\n${choices}\n\n${t("Enter a number from 1 to 5, or cancel.")}`,
    "1",
  );
  if (answer === null) return null;
  const index = Number(answer) - 1;
  if (!Number.isInteger(index) || !active[index]) {
    byId("brandmeister-hoseline-status").textContent = t("No talkgroup was replaced.");
    return null;
  }
  return active[index].talkgroup;
}

async function brandmeisterCommand(action, extra = {}) {
  const output = byId("brandmeister-hoseline-status");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    await refresh();
    return payload;
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
    return null;
  }
}

function renderBrandmeisterCatalog() {
  const list = byId("brandmeister-catalog-list");
  const query = brandmeisterCatalogQuery.trim().toLocaleLowerCase(currentLocale);
  const selected = new Map(brandmeisterTalkgroups.map((item) => [item.talkgroup, item]));
  const signature = `${currentLocale}|${query}|${brandmeisterCatalog.length}|${brandmeisterTalkgroups.map((item) => `${item.talkgroup}:${item.enabled}`).join(",")}`;
  if (signature === brandmeisterCatalogSignature) return;
  brandmeisterCatalogSignature = signature;
  list.replaceChildren();
  const matches = brandmeisterCatalog.filter((item) => {
    const haystack = `${item.talkgroup} ${item.name} ${item.country_code || ""}`.toLocaleLowerCase(currentLocale);
    return !query || haystack.includes(query);
  });
  for (const item of matches) {
    const row = document.createElement("li");
    const label = document.createElement("label");
    label.className = "station-row-copy";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selected.get(item.talkgroup)?.enabled === true;
    checkbox.addEventListener("change", async () => {
      const saved = selected.get(item.talkgroup);
      const replacement = checkbox.checked && saved?.enabled !== true
        ? chooseBrandmeisterReplacement()
        : undefined;
      if (replacement === null) {
        checkbox.checked = false;
        return;
      }
      if (saved) {
        await brandmeisterCommand("brandmeister_talkgroup_set", {
          channel_id: saved.id,
          enabled: checkbox.checked,
          ...(replacement === undefined ? {} : { replace_talkgroup: replacement }),
        });
      } else {
        await brandmeisterCommand("brandmeister_talkgroup_add", {
          talkgroup: item.talkgroup,
          name: item.name,
          enabled: checkbox.checked,
          ...(replacement === undefined ? {} : { replace_talkgroup: replacement }),
        });
      }
    });
    const copy = document.createElement("span");
    const strong = document.createElement("strong");
    strong.textContent = `${brandmeisterFlag(item.talkgroup)} TG ${item.talkgroup}`;
    const detail = document.createElement("small");
    detail.textContent = item.name;
    copy.append(strong, detail);
    label.append(checkbox, copy);
    row.append(label);
    list.append(row);
  }
}

function renderBrandmeisterTalkgroups(state = {}) {
  brandmeisterTalkgroups = Array.isArray(state.channels) ? state.channels : [];
  const list = byId("brandmeister-talkgroup-list");
  list.replaceChildren();
  const ordered = [...brandmeisterTalkgroups].sort((left, right) => Number(right.active === true) - Number(left.active === true));
  for (const item of ordered) {
    const row = document.createElement("li");
    row.dataset.active = item.active === true ? "true" : "false";
    const activityIcon = document.createElement("span");
    activityIcon.className = "brandmeister-activity-icon";
    activityIcon.setAttribute("aria-label", item.active ? t("Active now") : t("Waiting for activity"));
    const label = document.createElement("label");
    label.className = "station-row-copy";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = item.enabled;
    checkbox.addEventListener("change", async () => {
      const replacement = checkbox.checked && item.enabled !== true
        ? chooseBrandmeisterReplacement()
        : undefined;
      if (replacement === null) {
        checkbox.checked = false;
        return;
      }
      await brandmeisterCommand("brandmeister_talkgroup_set", {
        channel_id: item.id,
        enabled: checkbox.checked,
        ...(replacement === undefined ? {} : { replace_talkgroup: replacement }),
      });
    });
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = `${brandmeisterFlag(item.talkgroup)} TG ${item.talkgroup} · ${item.name}`;
    const participant = document.createElement("small");
    const identity = [item.alias, item.source ? `DMR ${item.source}` : ""].filter(Boolean).join(" · ");
    const switchState = item.enabled ? t("On") : t("Off");
    participant.textContent = item.active
      ? `${switchState} · ${t("Active now")} · ${identity || t("Talker identity not supplied")}`
      : identity
        ? `${switchState} · ${t("Last heard")} · ${identity}`
        : `${switchState} · ${t("Waiting for activity")}`;
    copy.append(title, participant);
    label.append(checkbox, copy);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = t("Delete");
    remove.addEventListener("click", () => brandmeisterCommand(
      "brandmeister_talkgroup_delete",
      { channel_id: item.id },
    ));
    actions.append(remove);
    row.append(activityIcon, label, actions);
    list.append(row);
  }
  byId("brandmeister-talkgroup-count").textContent = `${selectedBrandmeisterTalkgroups().length} / 5`;
  renderBrandmeisterCatalog();
  updateBrandmeisterState(state);
}

async function addBrandmeisterTalkgroup() {
  const input = byId("brandmeister-talkgroup");
  const talkgroup = Number(input.value);
  if (!Number.isInteger(talkgroup) || talkgroup <= 90 || talkgroup > 9999999) {
    byId("brandmeister-hoseline-status").textContent = t("Enter a valid talkgroup above 90.");
    return false;
  }
  await brandmeisterCommand("brandmeister_talkgroup_add", {
    talkgroup,
    enabled: selectedBrandmeisterTalkgroups().length < 5,
  });
  input.value = "";
  return true;
}

function updateBrandmeisterState(state) {
  const output = byId("brandmeister-hoseline-status");
  const call = byId("brandmeister-call");
  call.hidden = true;
  if (state.status === "connecting") output.textContent = t("Connecting to HoseLine …");
  if (["connected", "listening"].includes(state.status)) output.textContent = t("Listening to {{count}} talkgroups.", { count: state.talkgroups.length });
  if (["closed", "stopped"].includes(state.status)) output.textContent = t("HoseLine reception stopped.");
  if (state.status === "reconnecting") output.textContent = t("Reconnecting to HoseLine …");
  if (state.status === "error") output.textContent = t("HoseLine connection failed. Use the official player link below.");
  if (state.status === "call") {
    const destination = Number(state.destination);
    output.textContent = t("Active talkgroup: {{talkgroup}}", { talkgroup: destination || "–" });
    call.textContent = `${brandmeisterFlag(destination)} TG ${destination || "–"} · ${state.source || "–"}${state.alias ? ` · ${state.alias}` : ""}`;
    call.hidden = false;
  }
}

if (window.OpenR4d10HoseLine) {
  brandmeisterReceiver = new window.OpenR4d10HoseLine(updateBrandmeisterState);
}

byId("brandmeister-add-talkgroup").addEventListener("click", addBrandmeisterTalkgroup);

byId("brandmeister-hoseline-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (byId("brandmeister-talkgroup").value) await addBrandmeisterTalkgroup();
  await brandmeisterCommand("brandmeister_listen");
});

byId("brandmeister-device-stop").addEventListener("click", () => {
  brandmeisterCommand("brandmeister_stop");
});

byId("brandmeister-browser-listen").addEventListener("click", () => {
  const output = byId("brandmeister-hoseline-status");
  const talkgroups = selectedBrandmeisterTalkgroups();
  if (!talkgroups.length) {
    output.textContent = t("Activate at least one talkgroup.");
    return;
  }
  if (!brandmeisterReceiver) {
    output.textContent = t("HoseLine reception is unavailable in this browser.");
    return;
  }
  brandmeisterReceiver.connect(talkgroups).catch(() => updateBrandmeisterState({
    status: "error",
    talkgroups,
  }));
  byId("brandmeister-disconnect").disabled = false;
});

byId("brandmeister-disconnect").addEventListener("click", () => {
  brandmeisterReceiver?.disconnect();
  byId("brandmeister-disconnect").disabled = true;
});

byId("brandmeister-search").addEventListener("input", (event) => {
  brandmeisterCatalogQuery = event.currentTarget.value;
  renderBrandmeisterCatalog();
});

fetch("/api/brandmeister-talkgroups", { cache: "no-store" })
  .then((response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
  .then((payload) => {
    brandmeisterCatalog = Array.isArray(payload.talkgroups) ? payload.talkgroups : [];
    renderBrandmeisterCatalog();
  })
  .catch((error) => {
    byId("brandmeister-hoseline-status").textContent = t("Error: {{message}}", { message: error.message });
  });

byId("podcast-search").addEventListener("input", (event) => {
  podcastSearchQuery = event.currentTarget.value;
  if (latestStatus?.services) renderPodcasts(latestStatus.services);
});

byId("media-scan").addEventListener("click", () => sendControl("media_scan"));

byId("radio-continuous").addEventListener("change", (event) => {
  sendControl("radio_capture_mode", { enabled: event.currentTarget.checked });
});

for (const button of document.querySelectorAll("[data-music-action]")) {
  button.addEventListener("click", () => sendControl(button.dataset.musicAction));
}

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

async function cameraCommand(action, extra = {}) {
  const status = byId("camera-status");
  status.textContent = t("Working …");
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...extra }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    if (payload.camera && payload.camera_id) {
      const image = byId("camera-preview");
      image.src = `/api/camera/${payload.camera_id}?t=${Date.now()}`;
      image.hidden = false;
      image.alt = t("Camera image {{width}} × {{height}}", {
        width: payload.camera.width,
        height: payload.camera.height,
      });
    }
    status.textContent = action === "camera_delete"
      ? t("Camera deleted.")
      : action === "camera_refresh"
        ? t("Camera image updated.")
        : t("Camera change saved.");
    await refresh();
    return payload;
  } catch (error) {
    status.textContent = t("Camera error: {{message}}", { message: error.message });
    return null;
  }
}

function renderWebcams(catalog) {
  const cameras = Array.isArray(catalog?.webcams?.channels) ? catalog.webcams.channels : [];
  const list = byId("camera-list");
  list.replaceChildren();
  cameras.forEach((camera, index) => {
    const row = document.createElement("li");
    const copy = document.createElement("span");
    copy.className = "station-row-copy";
    const name = document.createElement("strong");
    name.textContent = camera.name;
    const detail = document.createElement("small");
    detail.textContent = `${camera.kind.toUpperCase()} · ${camera.source || t("Local source")}`;
    copy.append(name, detail);
    const actions = document.createElement("span");
    actions.className = "library-actions";
    const refreshButton = document.createElement("button");
    refreshButton.type = "button";
    refreshButton.className = "library-play";
    refreshButton.textContent = t("Show");
    refreshButton.addEventListener("click", () => cameraCommand("camera_refresh", { camera_id: camera.id }));
    const up = document.createElement("button");
    up.type = "button";
    up.textContent = "↑";
    up.disabled = index === 0;
    up.addEventListener("click", () => cameraCommand("camera_move", { camera_id: camera.id, direction: -1 }));
    const down = document.createElement("button");
    down.type = "button";
    down.textContent = "↓";
    down.disabled = index === cameras.length - 1;
    down.addEventListener("click", () => cameraCommand("camera_move", { camera_id: camera.id, direction: 1 }));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = t("Delete");
    remove.addEventListener("click", () => cameraCommand("camera_delete", { camera_id: camera.id }));
    actions.append(refreshButton, up, down, remove);
    row.append(copy, actions);
    list.append(row);
  });
  if (!cameras.length) {
    const empty = document.createElement("li");
    empty.textContent = t("No cameras configured.");
    list.append(empty);
  }
}

byId("camera-control").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = await cameraCommand("camera_add", {
    name: byId("camera-name").value,
    kind: byId("camera-kind").value,
    url: byId("camera-url").value,
  });
  if (payload) event.currentTarget.reset();
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

byId("language-select").addEventListener("change", async (event) => {
  const select = event.currentTarget;
  const language = select.value;
  const output = byId("control-result");
  setLocale(language);
  select.disabled = true;
  try {
    const response = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "display_language", language }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    setLocale(payload.settings?.language || language);
    output.textContent = t("Device language saved.");
    await refresh();
  } catch (error) {
    output.textContent = t("Error: {{message}}", { message: error.message });
    await refresh();
  } finally {
    select.disabled = false;
  }
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
