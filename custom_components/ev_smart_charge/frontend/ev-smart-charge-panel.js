/* EV Smart Charge sidebar panel. Stateful, dependency-free Home Assistant UI. */

class EvSmartChargePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._initialized = false;
    this._pending = new Set();
    this._draft = { setup: {}, fields: {} };
    this._noticeTimer = null;
    this._setupSignature = "";
    this._activeSection = "overview";
  }

  set hass(value) {
    this._hass = value;
    if (!this._initialized) {
      this._renderShell();
      this._initialized = true;
    }
    this._refresh();
  }

  set panel(value) {
    this._panel = value;
  }

  _entity(domain, key) {
    const canonical = `${domain}.ev_smart_charge_${key}`;
    if (this._hass?.states?.[canonical]) return canonical;

    // HA can prefix the object ID with the device name after an import or rename.
    // Accept only known EV Smart Charge forms; never match a generic suffix.
    const exactObjectIds = new Set([
      `ev_smart_charge_${key}`,
      `ev_smart_charge_planner_${key}`,
    ]);
    const match = Object.keys(this._hass?.states || {}).find((entityId) => {
      const [candidateDomain, objectId] = entityId.split(".", 2);
      return candidateDomain === domain && (
        exactObjectIds.has(objectId) ||
        objectId.endsWith(`_ev_smart_charge_${key}`) ||
        objectId.endsWith(`_ev_smart_charge_planner_${key}`)
      );
    });
    return match || canonical;
  }

  _state(domain, key, fallback = "—") {
    const state = this._hass?.states?.[this._entity(domain, key)];
    return state ? state.state : fallback;
  }

  _attributes(domain, key) {
    return this._hass?.states?.[this._entity(domain, key)]?.attributes || {};
  }

  _configured() {
    return this._state("sensor", "setup_status", "needs_configuration") === "ready";
  }

  _time(value) {
    if (!value || value === "—") return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? String(value)
      : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  _number(value, digits = 2) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString("nl-NL", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }) : "—";
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  _metric(label, domain, key, unit = "", digits = 2) {
    const raw = this._state(domain, key);
    const numeric = Number(raw);
    const value = Number.isFinite(numeric) ? this._number(numeric, digits) : raw;
    return `<div class="metric"><span>${label}</span><strong>${this._escape(value)}${unit}</strong></div>`;
  }

  _metrics(items) {
    return items.map((item) => this._metric(...item)).join("");
  }

  _setupFields() {
    const setup = this._attributes("sensor", "setup_status");
    const configuration = setup.configuration || {};
    const labels = {
      soc_entity: "Auto SoC — accupercentage",
      plug_entity: "Auto aangesloten — connected/disconnected",
      charging_entity: "Auto laadstatus — charging/not charging",
      target_entity: "Auto doelpercentage — optioneel",
      charger_state_entity: "Laadpaalstatus — charging/suspended/no EV",
      charger_switch_entity: "Laadpaal aan/uit — on/off",
      power_entity: "Laadvermogen — W/kW",
      session_energy_entity: "Sessie-energie — kWh",
      tariff_entity: "Tarief + forecast",
      solar_forecast_entity: "Zonneforecast — optioneel",
      solar_now_entity: "Zonnevermogen nu — optioneel",
    };
    return Object.entries(labels).map(([key, label]) => {
      const current = this._draft.setup[key] ?? configuration[key] ?? "";
      const candidates = [...(setup.candidates?.[key] || [])];
      if (current && !candidates.some((candidate) => candidate.entity_id === current)) {
        candidates.unshift({ entity_id: current, name: current, reason: "opgeslagen koppeling" });
      }
      const options = candidates.map((candidate) => `<option value="${this._escape(candidate.entity_id)}" ${candidate.entity_id === current ? "selected" : ""}>${this._escape(candidate.name || candidate.entity_id)}${candidate.reason ? ` — ${this._escape(candidate.reason)}` : ""}</option>`).join("");
      return `<label class="setup-field"><span>${label}</span><select data-setup-key="${key}"><option value="">Niet gekoppeld</option>${options}</select></label>`;
    }).join("");
  }

  _renderShell() {
    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main>
        <header class="hero">
          <div><p class="eyebrow">EV SMART CHARGE</p><h1>Laadplanner</h1><p class="muted">Lokaal plannen, optionele AI-keuze en veilige bediening</p></div>
          <button class="secondary" data-action="open-settings">⚙ Instellingen</button>
        </header>
        <nav class="nav" aria-label="EV Smart Charge secties">
          <button data-section="overview" class="active">Overzicht</button>
          <button data-section="tests">Testen</button>
          <button data-section="telegram">Telegram</button>
          <button data-section="setup">Apparaat en sensoren</button>
          <button data-section="settings">Instellingen</button>
        </nav>
        <div class="notice" role="status" aria-live="polite"></div>
        <div id="configuration-warning" class="warning" hidden></div>

        <section id="section-overview" class="section">
          <div class="section-heading"><div><p class="eyebrow">LIVE</p><h2>Overzicht</h2></div><span id="control-mode-badge" class="badge"></span></div>
          <div class="card"><h3>Live status</h3><div id="live-metrics" class="metrics"></div></div>
          <div class="card"><h3>Forecast</h3><div id="forecast-metrics" class="metrics"></div><div id="forecast-rows" class="forecast"></div></div>
          <div class="columns">
            <div class="card"><h3>Laadplan</h3><div id="plan-metrics" class="metrics"></div><div class="form-row"><label>Doelpercentage<input id="target-soc" type="number" min="50" max="100" step="5"></label><label>Deadline<input id="deadline" type="time"></label></div><div class="button-row"><button data-action="plan-today">📅 Vandaag</button><button data-action="plan-flex">🌞 Flexibel</button><button data-action="plan-deadline">⏰ Deadline</button></div><p id="control-mode-note" class="muted"></p><div class="button-row"><button class="primary" data-action="start">▶ Start</button><button data-action="stop">■ Stop</button><button data-action="reset">↻ Reset</button></div></div>
            <div class="card"><h3>Huidige sessie</h3><div id="session-metrics" class="metrics"></div><h3 class="subheading">Periodeoverzicht</h3><div id="period-metrics" class="periods"></div></div>
          </div>
        </section>

        <section id="section-tests" class="section" hidden>
          <div class="section-heading"><div><p class="eyebrow">DRY RUN</p><h2>Testplannen</h2></div><span class="badge neutral">Schakelt niets</span></div>
          <div class="card"><p class="muted">De tests lezen de actuele sensorwaarden en tariefforecast. Er wordt geen plan opgeslagen, geen sessie gestart en geen laadpaal geschakeld.</p><div class="button-row"><button data-action="test-flex">🧪 Test flex</button><button data-action="test-plan">🧪 Test plan</button></div><div id="test-metrics" class="metrics"></div><div id="test-windows" class="windows"></div></div>
        </section>

        <section id="section-telegram" class="section" hidden>
          <div class="section-heading"><div><p class="eyebrow">MESSAGES</p><h2>Telegram</h2></div><span id="telegram-badge" class="badge"></span></div>
          <div class="card"><p class="muted">Gebruik deze knoppen om berichten handmatig te testen. Ze starten geen laadactie.</p><div class="button-row"><button class="primary" data-action="telegram-test">✈ Testbericht</button><button data-action="telegram-plan">Plan</button><button data-action="telegram-start">Start</button><button data-action="telegram-done">Klaar</button><button data-action="telegram-stop">Stop</button><button data-action="telegram-blocked">Veiligheid</button></div><div class="templates"><label>Testbericht<textarea data-template-key="telegram_template_test"></textarea></label><label>Planbericht<textarea data-template-key="telegram_template_plan"></textarea></label><label>Startbericht<textarea data-template-key="telegram_template_start"></textarea></label><label>Klaarbericht<textarea data-template-key="telegram_template_done"></textarea></label><label>Stopbericht<textarea data-template-key="telegram_template_stop"></textarea></label><label>Veiligheidsbericht<textarea data-template-key="telegram_template_blocked"></textarea></label></div></div>
        </section>

        <section id="section-setup" class="section" hidden>
          <div class="section-heading"><div><p class="eyebrow">SETUP</p><h2>Apparaat en sensoren</h2></div><button data-action="open-settings">Geavanceerde instellingen</button></div>
          <div class="card"><p class="muted">Selecteer hier de bron-entiteiten. De suggesties komen uit Home Assistant. Controleer vooral SoC, laadpaalstatus, aan/uit-switch, laadvermogen, sessie-energie en tarief + forecast.</p><div id="setup-fields" class="setup-grid"></div><div class="setup-options"><label>Energieprovider<select data-setup-key="tariff_provider"><option value="auto">Automatisch</option><option value="zonneplan">Zonneplan</option><option value="tibber">Tibber</option><option value="anwb">ANWB Dynamisch</option><option value="generic">Generiek</option></select></label><label>Besturing<select data-setup-key="control_mode"><option value="monitor">Alleen monitoren/testen (Node-RED)</option><option value="hacs">HACS mag besturen</option></select></label></div><div class="button-row"><button class="primary" data-action="setup-save">Koppelingen opslaan</button><button data-action="setup-test">Verbinding testen</button></div><div id="connection-summary" class="connection-summary"></div><div id="connection-checks" class="connection-checks"></div></div>
        </section>

        <section id="section-settings" class="section" hidden>
          <div class="section-heading"><div><p class="eyebrow">CONFIGURATION</p><h2>Plannerinstellingen</h2></div><button data-action="open-settings">Home Assistant instellingen</button></div>
          <div class="card"><p class="muted">Deze waarden worden als Home Assistant-entiteiten opgeslagen. AI blijft optioneel; lokaal plannen werkt zonder API-sleutel.</p><div class="settings-grid"><label class="toggle"><input id="ai-enabled" type="checkbox"><span>AI gebruiken</span></label><label>Doelpercentage<input data-number-key="target_soc_percent" type="number" min="50" max="100" step="5"></label><label>Laadvermogen<input data-number-key="charge_power_kw" type="number" min="1" max="50" step="0.1"></label><label>Accucapaciteit<input data-number-key="battery_capacity_kwh" type="number" min="1" max="200" step="0.1"></label><label>Laadefficiëntie<input data-number-key="charge_efficiency" type="number" min="0.5" max="1" step="0.01"></label><label>ERE per kWh<input data-number-key="ere_rate_eur_per_kwh" type="number" min="-1" max="2" step="0.01"></label></div></div>
        </section>
      </main>`;
    this.shadowRoot.addEventListener("click", (event) => this._handleClick(event));
    this.shadowRoot.addEventListener("input", (event) => this._handleInput(event));
    this.shadowRoot.addEventListener("change", (event) => this._handleChange(event));
  }

  _handleClick(event) {
    const sectionButton = event.target.closest?.("[data-section]");
    if (sectionButton) {
      this._activeSection = sectionButton.dataset.section;
      this._updateSections();
      return;
    }
    const button = event.target.closest?.("[data-action]");
    if (!button || button.disabled) return;
    event.preventDefault();
    event.stopPropagation();
    const action = button.dataset.action;
    if (action === "open-settings") {
      window.location.href = "/config/integrations/integration/ev_smart_charge";
      return;
    }
    if (action === "plan-today") return this._run(action, "Plan voor vandaag", () => this._service("ev_smart_charge", "create_plan", { mode: "today", target_soc: this._target() }));
    if (action === "plan-flex") return this._run(action, "Flexibel plan", () => this._service("ev_smart_charge", "create_plan", { mode: "flex", target_soc: this._target() }));
    if (action === "plan-deadline") return this._run(action, "Deadlineplan", () => this._service("ev_smart_charge", "create_plan", this._planData("deadline")));
    if (action === "test-flex") return this._run(action, "Test flex", () => this._service("ev_smart_charge", "test_flex", { target_soc: this._target() }));
    if (action === "test-plan") return this._run(action, "Test plan", () => this._service("ev_smart_charge", "test_plan", { target_soc: this._target() }));
    if (action === "setup-save") return this._run(action, "Koppelingen opslaan", () => this._saveSetup());
    if (action === "setup-test") return this._run(action, "Verbindingstest", () => this._service("ev_smart_charge", "test_connection"));
    if (action === "start") return this._control(action, "Start", "start");
    if (action === "stop") return this._control(action, "Stop", "stop");
    if (action === "reset") return this._run(action, "Reset", () => this._service("ev_smart_charge", "reset"));
    if (action === "telegram-test") return this._run(action, "Telegram test", () => this._service("ev_smart_charge", "telegram_test"));
    if (action.startsWith("telegram-")) return this._run(action, "Telegrambericht", () => this._service("ev_smart_charge", "telegram_send", { event: action.replace("telegram-", "") }));
  }

  _handleInput(event) {
    const target = event.target;
    if (target.id === "target-soc" || target.id === "deadline") this._draft.fields[target.id] = target.value;
    if (target.dataset?.setupKey) this._draft.setup[target.dataset.setupKey] = target.value;
    if (target.dataset?.templateKey) this._draft.fields[target.dataset.templateKey] = target.value;
    if (target.dataset?.numberKey) this._draft.fields[target.dataset.numberKey] = target.value;
  }

  _handleChange(event) {
    const target = event.target;
    if (target.dataset?.setupKey) this._draft.setup[target.dataset.setupKey] = target.value;
    if (target.id === "ai-enabled") {
      const service = target.checked ? "turn_on" : "turn_off";
      this._run("ai-enabled", "AI-instelling", () => this._service("switch", service, { entity_id: this._entity("switch", "ai_enabled") }));
    }
    if (target.dataset?.numberKey) {
      this._run(`number-${target.dataset.numberKey}`, "Instelling opslaan", () => this._service("number", "set_value", { entity_id: this._entity("number", target.dataset.numberKey), value: Number(target.value) }));
    }
    if (target.dataset?.templateKey) {
      this._run(`template-${target.dataset.templateKey}`, "Template opslaan", () => this._service("text", "set_value", { entity_id: this._entity("text", target.dataset.templateKey), value: target.value }));
    }
  }

  _control(action, label, service) {
    const mode = this._setupConfiguration().control_mode || "monitor";
    if (mode !== "hacs") {
      this._notice(`${label} is geblokkeerd: Besturing staat op monitor (Node-RED).`, "warning");
      this._activeSection = "setup";
      this._updateSections();
      return;
    }
    return this._run(action, label, () => this._service("ev_smart_charge", service));
  }

  async _run(key, label, operation) {
    if (this._pending.has(key)) return;
    const button = this.shadowRoot.querySelector(`[data-action="${key}"]`);
    this._pending.add(key);
    if (button) {
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = "Bezig…";
    }
    try {
      await operation();
      this._notice(`${label}: uitgevoerd`, "success");
    } catch (error) {
      this._notice(`${label}: mislukt — ${error.message || error}`, "error");
    } finally {
      this._pending.delete(key);
      if (button) {
        button.disabled = false;
        button.textContent = button.dataset.originalText || label;
      }
      this._refresh();
    }
  }

  async _service(domain, service, data = {}) {
    if (!this._hass) throw new Error("Home Assistant is nog niet beschikbaar");
    await this._hass.callService(domain, service, data);
  }

  _target() {
    const value = Number(this._draft.fields["target-soc"] ?? this.shadowRoot.querySelector("#target-soc")?.value ?? 95);
    if (!Number.isFinite(value) || value < 50 || value > 100 || value % 5 !== 0) throw new Error("Doelpercentage moet 50 t/m 100 zijn in stappen van 5");
    return value;
  }

  _planData(mode) {
    const data = { mode, target_soc: this._target() };
    const deadline = this._draft.fields.deadline ?? this.shadowRoot.querySelector("#deadline")?.value ?? "";
    if (mode === "deadline") {
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(deadline)) throw new Error("Kies eerst een geldige deadline");
      data.deadline = `${deadline}:00`;
    }
    return data;
  }

  async _saveSetup() {
    const data = {};
    this.shadowRoot.querySelectorAll("[data-setup-key]").forEach((input) => {
      data[input.dataset.setupKey] = input.value;
    });
    await this._service("ev_smart_charge", "update_setup", data);
    this._draft.setup = {};
  }

  _setupConfiguration() {
    return this._attributes("sensor", "setup_status").configuration || {};
  }

  _notice(message, kind = "success") {
    const node = this.shadowRoot.querySelector(".notice");
    if (!node) return;
    node.textContent = message;
    node.className = `notice visible ${kind}`;
    window.clearTimeout(this._noticeTimer);
    this._noticeTimer = window.setTimeout(() => node.classList.remove("visible"), 5000);
  }

  _updateSections() {
    this.shadowRoot.querySelectorAll("[data-section]").forEach((button) => button.classList.toggle("active", button.dataset.section === this._activeSection));
    this.shadowRoot.querySelectorAll(".section").forEach((section) => { section.hidden = section.id !== `section-${this._activeSection}`; });
  }

  _setInput(id, value) {
    const input = this.shadowRoot.querySelector(`#${id}`);
    if (!input || this.shadowRoot.activeElement === input) return;
    input.value = value ?? "";
  }

  _refreshSetup() {
    const setup = this._attributes("sensor", "setup_status");
    const configuration = setup.configuration || {};
    const checks = setup.checks || {};
    // Live check values change every polling cycle. They must not rebuild the
    // form, otherwise a selected dropdown value can be lost before Save is
    // pressed. Rebuild only when the available options or saved connections
    // actually change.
    const signature = JSON.stringify({ configuration, candidates: setup.candidates || {} });
    if (signature !== this._setupSignature) {
      const fields = this.shadowRoot.querySelector("#setup-fields");
      if (fields) fields.innerHTML = this._setupFields();
      ["tariff_provider", "control_mode"].forEach((key) => {
        const input = this.shadowRoot.querySelector(`[data-setup-key="${key}"]`);
        if (input && this.shadowRoot.activeElement !== input) input.value = this._draft.setup[key] ?? configuration[key] ?? (key === "control_mode" ? "monitor" : "auto");
      });
      this._setupSignature = signature;
    }
    const summary = this.shadowRoot.querySelector("#connection-summary");
    const setupStatus = this._state("sensor", "setup_status", "needs_configuration");
    const checkValues = Object.values(checks);
    const good = checkValues.filter((check) => check.status === "ok").length;
    const attention = checkValues.filter((check) => ["missing", "unavailable", "warning"].includes(check.status)).length;
    if (summary) summary.innerHTML = `Live: <strong>${this._escape(setupStatus)}</strong> · ${good}/${checkValues.length} bruikbaar` + (attention ? ` · ${attention} aandachtspunt${attention === 1 ? "" : "en"}` : "");
    const checkList = this.shadowRoot.querySelector("#connection-checks");
    if (checkList) {
      const ordered = Object.entries(checks);
      checkList.innerHTML = ordered.length ? `<h3 class="subheading">Koppelingcontrole</h3>${ordered.map(([key, check]) => {
        const status = check.status || "missing";
        const statusLabel = status === "ok" ? "Goed" : status === "optional" ? "Optioneel" : status === "warning" ? "Controleren" : "Niet goed";
        const icon = status === "ok" ? "✓" : status === "optional" ? "–" : status === "warning" ? "!" : "×";
        return `<div class="connection-row ${this._escape(status)}"><span class="connection-icon">${icon}</span><div><strong>${this._escape(check.label || key)}</strong><small>${this._escape(check.entity_id || "Niet gekoppeld")} · ${this._escape(check.detail || "Geen status")}</small></div><b>${statusLabel}</b></div>`;
      }).join("")}` : `<h3 class="subheading">Koppelingcontrole</h3><p class="muted">Nog geen gekoppelde entities. Kies de bronnen hierboven en sla ze op.</p>`;
    }
  }

  _refreshDynamicLists() {
    const tariffSlots = this._attributes("sensor", "tariff_slots").slots || [];
    const forecast = this.shadowRoot.querySelector("#forecast-rows");
    if (forecast) forecast.innerHTML = tariffSlots.length ? tariffSlots.slice(0, 32).map((slot) => { const start = slot.start_at || slot.start || slot.datetime || slot.timestamp; const end = slot.end_at || slot.end; const price = slot.eur_per_kwh ?? slot.price_eur_per_kwh ?? slot.price ?? slot.value ?? slot.tariff; return `<div class="forecast-row"><span>${this._time(start)}${end ? `–${this._time(end)}` : ""}</span><strong>€${this._number(price, 3)}/kWh</strong></div>`; }).join("") : `<p class="muted">Geen tariefforecast beschikbaar.</p>`;
    const windows = this._attributes("sensor", "test_windows").windows || [];
    const testWindows = this.shadowRoot.querySelector("#test-windows");
    if (testWindows) testWindows.innerHTML = `<h3>Gekozen prijsblokken</h3>${windows.length ? windows.map((window) => `<div class="window"><span>${this._time(window.start_at)}–${this._time(window.end_at)}</span><strong>${this._number(window.kwh, 2)} kWh</strong><span>€${this._number(window.price_eur_per_kwh, 3)}/kWh</span><span>€${this._number(window.cost_eur, 2)}</span></div>`).join("") : `<p class="muted">Nog geen testresultaat. Kies Test flex of Test plan.</p>`}`;
  }

  _refresh() {
    if (!this._hass || !this._initialized) return;
    const configured = this._configured();
    const warning = this.shadowRoot.querySelector("#configuration-warning");
    if (warning) {
      const setupStatus = this._state("sensor", "setup_status", "needs_configuration");
      warning.hidden = configured;
      warning.innerHTML = setupStatus === "needs_configuration"
        ? "<strong>Bronnen nog niet gekoppeld</strong><br>Open de sectie Apparaat en sensoren of de configuratie van deze integratie en kies de juiste entities."
        : "<strong>Koppeling controleren</strong><br>Een of meer gekoppelde entities zijn niet beschikbaar of leveren nog geen tariefforecast. Bekijk de groene en rode regels bij Apparaat en sensoren.";
    }
    const mode = this._setupConfiguration().control_mode || "monitor";
    const modeBadge = this.shadowRoot.querySelector("#control-mode-badge");
    if (modeBadge) { modeBadge.textContent = mode === "hacs" ? "HACS-besturing actief" : "Monitor / Node-RED"; modeBadge.className = `badge ${mode === "hacs" ? "good" : "neutral"}`; }
    const telegramEnabled = this._state("switch", "telegram_enabled", "off") === "on";
    const telegramBadge = this.shadowRoot.querySelector("#telegram-badge");
    if (telegramBadge) { telegramBadge.textContent = telegramEnabled ? "Ingeschakeld" : "Uitgeschakeld"; telegramBadge.className = `badge ${telegramEnabled ? "good" : "neutral"}`; }
    const controlNote = this.shadowRoot.querySelector("#control-mode-note");
    if (controlNote) controlNote.textContent = mode === "hacs" ? "HACS-besturing is actief. Start en Stop kunnen de laadpaalswitch bedienen." : "Monitor-modus is actief. Node-RED blijft besturen; Start en Stop via deze pagina zijn daarom geblokkeerd.";
    this._setInput("target-soc", this._draft.fields["target-soc"] ?? this._state("number", "target_soc_percent", "95"));
    this._setInput("deadline", this._draft.fields.deadline ?? "");
    this.shadowRoot.querySelectorAll("[data-template-key]").forEach((input) => { const key = input.dataset.templateKey; this._setInputValue(input, this._draft.fields[key] ?? this._state("text", key, "")); });
    this.shadowRoot.querySelectorAll("[data-number-key]").forEach((input) => { const key = input.dataset.numberKey; this._setInputValue(input, this._draft.fields[key] ?? this._state("number", key, "")); });
    const aiInput = this.shadowRoot.querySelector("#ai-enabled");
    if (aiInput && this.shadowRoot.activeElement !== aiInput) aiInput.checked = this._state("switch", "ai_enabled", "off") === "on";
    const metrics = {
      live: [["Planstatus", "sensor", "status"], ["SoC", "sensor", "soc", "%", 1], ["Laadvermogen", "sensor", "power_kw", " kW"], ["Huidig tarief", "sensor", "current_tariff", " €/kWh", 3], ["Auto aangesloten", "sensor", "plug_state"], ["Laadpaalstatus", "sensor", "charger_state"], ["Peblar switch", "sensor", "charger_switch_state"], ["Sessie-energie", "sensor", "session_energy_source_kwh", " kWh"], ["Tariefblokken", "sensor", "tariff_slots"]],
      forecast: [["Zonneforecast", "sensor", "solar_forecast_kwh", " kWh"], ["Zonvermogen nu", "sensor", "solar_now_w", " W"], ["Auto laadstatus", "sensor", "charging_state"], ["Doelstatus", "sensor", "target_state"]],
      plan: [["Start", "sensor", "plan_start"], ["Verwacht klaar", "sensor", "plan_end"], ["Benodigd", "sensor", "plan_kwh", " kWh"], ["Kosten", "sensor", "plan_cost", " €"], ["ERE", "sensor", "plan_ere", " €"], ["Netto", "sensor", "plan_net", " €"]],
      session: [["Geladen", "sensor", "session_kwh", " kWh"], ["Kosten", "sensor", "session_cost", " €"], ["ERE", "sensor", "session_ere", " €"], ["Netto", "sensor", "session_net", " €"]],
      test: [["Teststatus", "sensor", "test_status"], ["Testmodus", "sensor", "test_mode"], ["Toelichting", "sensor", "test_reason"], ["Start", "sensor", "test_start"], ["Klaar", "sensor", "test_end"], ["Benodigd", "sensor", "test_kwh", " kWh"], ["Netto", "sensor", "test_net", " €"]],
    };
    Object.entries(metrics).forEach(([name, items]) => { const node = this.shadowRoot.querySelector(`#${name}-metrics`); if (node) node.innerHTML = this._metrics(items); });
    const period = this.shadowRoot.querySelector("#period-metrics");
    if (period) period.innerHTML = ["today", "month", "year"].map((key) => `<div><h4>${key === "today" ? "Vandaag" : key === "month" ? "Deze maand" : "Dit jaar"}</h4>${this._metric("kWh", "sensor", `${key}_kwh`)}${this._metric("Netto", "sensor", `${key}_net`, " €")}${this._metric("Sessies", "sensor", `${key}_sessions`)}</div>`).join("");
    this._refreshDynamicLists();
    this._refreshSetup();
    this._updateSections();
  }

  _setInputValue(input, value) {
    if (this.shadowRoot.activeElement !== input) input.value = value ?? "";
  }

  _styles() {
    return `
      :host { --ev-accent:#ff9f1c; --ev-cyan:#35c2d8; --ev-green:#56c596; display:block; color:var(--primary-text-color); background:var(--primary-background-color); min-height:100vh; }
      * { box-sizing:border-box; } main { max-width:1180px; margin:0 auto; padding:28px 24px 54px; } .hero { display:flex; justify-content:space-between; align-items:center; gap:22px; padding:24px 26px; margin-bottom:14px; background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:16px; box-shadow:0 10px 28px rgba(0,0,0,.14); } .eyebrow { color:var(--ev-accent); font-size:11px; font-weight:800; letter-spacing:1.7px; margin:0 0 7px; } h1 { font-size:32px; line-height:1.1; margin:0; } h2 { font-size:23px; margin:0; } h3 { font-size:17px; margin:0 0 15px; } h4 { font-size:15px; margin:0 0 8px; } .muted { color:var(--secondary-text-color); line-height:1.45; } .nav { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:18px; padding:7px; background:var(--secondary-background-color); border:1px solid var(--divider-color); border-radius:12px; } .nav button { flex:1 1 150px; } .nav button.active { background:var(--ev-accent); color:#171717; border-color:transparent; font-weight:700; } .section-heading { display:flex; justify-content:space-between; align-items:end; gap:16px; margin:0 0 14px; } .card { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:12px; padding:20px; margin-bottom:16px; box-shadow:0 5px 16px rgba(0,0,0,.08); } .columns { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; } .metrics { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; } .metric { background:var(--secondary-background-color); border-left:3px solid var(--ev-cyan); border-radius:7px; padding:10px 12px; min-width:0; } .metric span { display:block; color:var(--secondary-text-color); font-size:12px; margin-bottom:5px; } .metric strong { display:block; font-size:17px; line-height:1.25; overflow-wrap:anywhere; } .periods { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; } .periods > div { border-top:3px solid var(--ev-accent); background:var(--secondary-background-color); border-radius:8px; padding:12px; } .periods .metric { background:transparent; border-left:0; padding:3px 0; } .form-row,.button-row,.setup-options { display:flex; flex-wrap:wrap; gap:9px; margin-top:15px; } .settings-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; } .toggle { flex-direction:row; align-items:center; min-height:46px; } .toggle input { width:20px; height:20px; } label { display:flex; flex-direction:column; gap:5px; color:var(--secondary-text-color); font-size:13px; flex:1 1 170px; } input,textarea,select { width:100%; color:var(--primary-text-color); background:var(--input-fill-color,transparent); border:1px solid var(--divider-color); border-radius:7px; font:inherit; padding:9px 10px; } textarea { min-height:82px; resize:vertical; } button { color:var(--primary-text-color); background:var(--secondary-background-color); border:1px solid var(--divider-color); border-radius:8px; padding:9px 13px; cursor:pointer; font:inherit; transition:filter .15s ease,border-color .15s ease; } button:hover:not(:disabled) { filter:brightness(1.13); border-color:var(--ev-cyan); } button:disabled { opacity:.55; cursor:wait; } button.primary { background:var(--ev-accent); color:#171717; border-color:transparent; font-weight:700; } .secondary { white-space:nowrap; } .badge { display:inline-flex; align-items:center; border-radius:999px; padding:6px 10px; font-size:12px; background:rgba(255,159,28,.18); color:var(--ev-accent); white-space:nowrap; } .badge.good { background:rgba(86,197,150,.18); color:var(--ev-green); } .badge.neutral { background:var(--secondary-background-color); color:var(--secondary-text-color); } .warning { background:rgba(255,159,28,.15); border:1px solid rgba(255,159,28,.55); border-radius:9px; padding:13px 15px; margin-bottom:15px; line-height:1.45; } .notice { min-height:0; opacity:0; margin:0; padding:0; transition:opacity .2s; } .notice.visible { opacity:1; min-height:32px; margin:0 0 10px; padding:8px 12px; border-radius:7px; background:rgba(86,197,150,.13); color:var(--ev-green); } .notice.warning { color:var(--ev-accent); background:rgba(255,159,28,.13); } .notice.error { color:var(--error-color,#ef5350); background:rgba(239,83,80,.13); } .forecast,.windows { margin-top:16px; border-top:1px solid var(--divider-color); padding-top:13px; max-height:330px; overflow:auto; } .forecast-row { display:flex; justify-content:space-between; gap:14px; padding:8px 10px; border-bottom:1px solid var(--divider-color); font-size:14px; } .forecast-row:nth-child(even) { background:var(--secondary-background-color); } .window { display:grid; grid-template-columns:1.2fr .9fr 1fr .7fr; gap:8px; padding:9px 0; border-bottom:1px solid var(--divider-color); font-size:14px; } .window strong,.window span:last-child { text-align:right; } .setup-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:11px; margin-top:16px; } .connection-summary { margin-top:15px; padding:11px 13px; background:var(--secondary-background-color); border-radius:7px; color:var(--secondary-text-color); line-height:1.5; } .connection-checks { margin-top:15px; } .connection-row { display:grid; grid-template-columns:30px minmax(0,1fr) auto; align-items:center; gap:10px; padding:10px 12px; border:1px solid var(--divider-color); border-left:4px solid var(--secondary-text-color); border-radius:8px; margin-top:7px; background:var(--secondary-background-color); } .connection-row.ok { border-left-color:var(--ev-green); } .connection-row.missing,.connection-row.unavailable { border-left-color:var(--error-color,#ef5350); } .connection-row.warning { border-left-color:var(--ev-accent); } .connection-row.optional { border-left-color:var(--secondary-text-color); } .connection-icon { width:22px; height:22px; display:grid; place-items:center; border-radius:50%; font-weight:800; background:rgba(239,83,80,.16); color:var(--error-color,#ef5350); } .connection-row.ok .connection-icon { background:rgba(86,197,150,.16); color:var(--ev-green); } .connection-row.warning .connection-icon { background:rgba(255,159,28,.16); color:var(--ev-accent); } .connection-row.optional .connection-icon { background:var(--secondary-background-color); color:var(--secondary-text-color); } .connection-row small { display:block; color:var(--secondary-text-color); margin-top:3px; overflow-wrap:anywhere; } .connection-row b { font-size:12px; color:var(--secondary-text-color); } .connection-row.ok b { color:var(--ev-green); } .connection-row.missing b,.connection-row.unavailable b { color:var(--error-color,#ef5350); } .connection-row.warning b { color:var(--ev-accent); } .subheading { margin-top:22px; } @media (max-width:800px) { main { padding:18px 13px 34px; } .hero,.section-heading { align-items:flex-start; flex-direction:column; } .columns,.periods,.setup-grid,.settings-grid { grid-template-columns:1fr; } .metrics { grid-template-columns:1fr 1fr; } h1 { font-size:28px; } .window { grid-template-columns:1fr 1fr; } .window strong,.window span:last-child { text-align:left; } } @media (max-width:500px) { .metrics { grid-template-columns:1fr; } .nav button { flex-basis:100%; } }`;
  }
}

customElements.define("ev-smart-charge-panel", EvSmartChargePanel);
