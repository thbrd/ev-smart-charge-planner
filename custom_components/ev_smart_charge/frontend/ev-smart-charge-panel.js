/* EV Smart Charge sidebar panel. No external frontend dependencies. */

class EvSmartChargePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._lastRender = "";
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  set panel(value) {
    this._panel = value;
  }

  _resolveEntity(entityId) {
    if (!this._hass?.states || !entityId) return entityId;
    if (this._hass.states[entityId]) return entityId;

    const separator = entityId.indexOf(".");
    if (separator < 0) return entityId;
    const domain = entityId.slice(0, separator);
    const objectId = entityId.slice(separator + 1);
    const prefix = "ev_smart_charge_";
    const suffix = objectId.startsWith(prefix) ? objectId.slice(prefix.length) : objectId;
    if (!suffix) return entityId;

    const match = Object.keys(this._hass.states).find((candidate) => {
      if (!candidate.startsWith(`${domain}.`)) return false;
      const candidateObjectId = candidate.slice(domain.length + 1);
      return candidateObjectId === suffix || candidateObjectId.endsWith(`_${suffix}`);
    });
    return match || entityId;
  }

  _state(entityId, fallback = "—") {
    const state = this._hass?.states?.[this._resolveEntity(entityId)];
    return state ? state.state : fallback;
  }

  _attributes(entityId) {
    return this._hass?.states?.[this._resolveEntity(entityId)]?.attributes || {};
  }

  _integrationConfigured() {
    const states = this._hass?.states || {};
    return Object.keys(states).some((entityId) => {
      const objectId = entityId.split(".").slice(1).join(".");
      return objectId === "ev_smart_charge" || objectId.includes("_ev_smart_charge_") || objectId.startsWith("ev_smart_charge_");
    });
  }

  _time(value) {
    if (!value || value === "—") return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  _testWindows() {
    const windows = this._attributes("sensor.ev_smart_charge_test_windows").windows || [];
    if (!windows.length) return "<p class=\"muted\">Nog geen testresultaat. Kies Test flex of Test plan.</p>";
    return windows.map((window) => `<div class="window"><span>${this._time(window.start_at)}–${this._time(window.end_at)}</span><strong>${this._formatNumber(window.kwh, 2)} kWh</strong><span>€${this._formatNumber(window.price_eur_per_kwh, 3)}/kWh</span><span>€${this._formatNumber(window.cost_eur, 2)}</span></div>`).join("");
  }

  _forecastRows() {
    const slots = this._attributes("sensor.ev_smart_charge_tariff_slots").slots || [];
    if (!slots.length) return "<p class=\"muted\">Geen tariefforecast beschikbaar.</p>";
    return slots.slice(0, 24).map((slot) => {
      const start = slot.start_at || slot.start || slot.datetime || slot.timestamp;
      const price = slot.eur_per_kwh ?? slot.price_eur_per_kwh ?? slot.price ?? slot.value ?? slot.tariff;
      return `<div class="forecast-row"><span>${this._time(start)}</span><strong>€${this._formatNumber(price, 3)}/kWh</strong></div>`;
    }).join("");
  }

  _number(entityId, digits = 2) {
    const value = Number(this._state(entityId, ""));
    return Number.isFinite(value) ? value.toFixed(digits) : "—";
  }

  _formatNumber(value, digits = 2) {
    const number = Number(value);
    return Number.isFinite(number)
      ? number.toLocaleString("nl-NL", { minimumFractionDigits: digits, maximumFractionDigits: digits })
      : String(value ?? "—");
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async _service(domain, service, data = {}) {
    if (!this._hass) return false;
    try {
      await this._hass.callService(domain, service, data);
      this._notice("Actie uitgevoerd");
      window.setTimeout(() => this._render(), 250);
      return true;
    } catch (error) {
      this._notice(`Actie mislukt: ${error.message || error}`);
      return false;
    }
  }

  async _test(label) {
    const target = Number(this.shadowRoot.querySelector("#target-soc")?.value || 95);
    const service = label === "test flex" ? "test_flex" : "test_plan";
    const completed = await this._service("ev_smart_charge", service, { target_soc: target });
    if (!completed) {
      await this._service("ev_smart_charge", "simulate_plan", { mode: "flex", target_soc: target });
    }
  }

  _notice(message) {
    const node = this.shadowRoot.querySelector(".notice");
    if (!node) return;
    node.textContent = message;
    node.classList.add("visible");
    window.clearTimeout(this._noticeTimer);
    this._noticeTimer = window.setTimeout(() => node.classList.remove("visible"), 3000);
  }

  _plan(mode) {
    const target = Number(this.shadowRoot.querySelector("#target-soc")?.value || 95);
    const deadline = this.shadowRoot.querySelector("#deadline")?.value || "";
    const data = { mode, target_soc: target };
    if (mode === "deadline" && deadline) data.deadline = `${deadline}:00`;
    this._service("ev_smart_charge", "create_plan", data);
  }

  _saveSetup() {
    const data = {};
    this.shadowRoot.querySelectorAll("[data-setup-key]").forEach((input) => {
      data[input.dataset.setupKey] = input.value;
    });
    this._service("ev_smart_charge", "update_setup", data);
  }

  _wire() {
    this.shadowRoot.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.action;
        if (action === "plan-today") this._plan("today");
        if (action === "plan-flex") this._plan("flex");
        if (action === "plan-deadline") this._plan("deadline");
        if (action === "test-flex") this._test("test flex");
        if (action === "test-plan") this._test("test plan");
        if (action === "setup-save") this._saveSetup();
        if (action === "setup-test") this._service("ev_smart_charge", "test_connection");
        if (action === "start") this._service("ev_smart_charge", "start");
        if (action === "stop") this._service("ev_smart_charge", "stop");
        if (action === "reset") this._service("ev_smart_charge", "reset");
        if (action === "telegram-test") {
          this._service("ev_smart_charge", "telegram_test");
        } else if (action.startsWith("telegram-")) {
          this._service("ev_smart_charge", "telegram_send", { event: action.replace("telegram-", "") });
        }
        if (action === "open-settings") window.location.href = "/config/integrations/integration/ev_smart_charge";
      });
    });

    this.shadowRoot.querySelectorAll("[data-text-entity]").forEach((input) => {
      input.addEventListener("change", () => {
        this._service("text", "set_value", {
          entity_id: this._resolveEntity(input.dataset.textEntity),
          value: input.value,
        });
      });
    });

    this.shadowRoot.querySelectorAll("[data-number-entity]").forEach((input) => {
      input.addEventListener("change", () => {
        this._service("number", "set_value", {
          entity_id: this._resolveEntity(input.dataset.numberEntity),
          value: Number(input.value),
        });
      });
    });

    const ai = this._state("switch.ev_smart_charge_ai_enabled", "off") === "on";
    this.shadowRoot.querySelector("#ai-enabled")?.addEventListener("change", (event) => {
      this._service("switch", event.target.checked ? "turn_on" : "turn_off", {
        entity_id: this._resolveEntity("switch.ev_smart_charge_ai_enabled"),
      });
    });
    const aiInput = this.shadowRoot.querySelector("#ai-enabled");
    if (aiInput) aiInput.checked = ai;
  }

  _card(title, body, className = "") {
    return `<section class="card ${className}"><h2>${title}</h2>${body}</section>`;
  }

  _metric(label, entityId, unit = "", digits = 2) {
    const raw = this._state(entityId);
    const value = raw === "—" ? raw : (Number.isFinite(Number(raw)) ? this._formatNumber(raw, digits) : raw);
    return `<div class="metric"><span>${label}</span><strong>${this._escape(value)}${unit}</strong></div>`;
  }

  _template(entityId, label) {
    return `<label class="template"><span>${label}</span><textarea data-text-entity="${entityId}">${this._escape(this._state(entityId, ""))}</textarea></label>`;
  }

  _setupField(key, label) {
    const setup = this._attributes("sensor.ev_smart_charge_setup_status");
    const configuration = setup.configuration || {};
    const candidates = setup.candidates?.[key] || [];
    const current = configuration[key] || "";
    const options = [...candidates];
    if (current && !options.some((candidate) => candidate.entity_id === current)) {
      options.unshift({ entity_id: current, name: `${current} (huidige keuze)`, reason: "opgeslagen koppeling" });
    }
    return `<label class="setup-field"><span>${label}</span><select data-setup-key="${key}"><option value="">Niet gekoppeld</option>${options.map((candidate) => `<option value="${this._escape(candidate.entity_id)}" ${candidate.entity_id === current ? "selected" : ""}>${this._escape(candidate.name || candidate.entity_id)} — ${this._escape(candidate.reason || "suggestie")}</option>`).join("")}</select></label>`;
  }

  _setupCard() {
    const setup = this._attributes("sensor.ev_smart_charge_setup_status");
    const configuration = setup.configuration || {};
    const provider = configuration.tariff_provider || "auto";
    const controlMode = configuration.control_mode || "monitor";
    return this._card("Setup wizard", `<p class="muted">De wizard zoekt passende entities op basis van naam, apparaatklasse en eenheid. Controleer de suggesties en sla ze daarna op.</p>
      <div class="setup-grid">
        ${this._setupField("soc_entity", "Auto SoC — accupercentage")}
        ${this._setupField("plug_entity", "Auto aangesloten — connected/disconnected")}
        ${this._setupField("charging_entity", "Auto laadstatus — charging/not charging")}
        ${this._setupField("target_entity", "Auto doelpercentage — optioneel")}
        ${this._setupField("charger_state_entity", "Laadpaalstatus — charging/suspended/no EV")}
        ${this._setupField("charger_switch_entity", "Laadpaal aan/uit — on/off")}
        ${this._setupField("power_entity", "Laadvermogen — W/kW")}
        ${this._setupField("session_energy_entity", "Sessie-energie — kWh")}
        ${this._setupField("tariff_entity", "Tarief + forecast")}
        ${this._setupField("solar_forecast_entity", "Zonneforecast — optioneel")}
        ${this._setupField("solar_now_entity", "Zonnevermogen nu — optioneel")}
        <label class="setup-field"><span>Energieprovider</span><select data-setup-key="tariff_provider"><option value="auto" ${provider === "auto" ? "selected" : ""}>Automatisch</option><option value="zonneplan" ${provider === "zonneplan" ? "selected" : ""}>Zonneplan</option><option value="tibber" ${provider === "tibber" ? "selected" : ""}>Tibber</option><option value="anwb" ${provider === "anwb" ? "selected" : ""}>ANWB Dynamisch</option><option value="generic" ${provider === "generic" ? "selected" : ""}>Generiek</option></select></label>
        <label class="setup-field"><span>Besturing</span><select data-setup-key="control_mode"><option value="monitor" ${controlMode === "monitor" ? "selected" : ""}>Alleen monitoren/testen (Node-RED)</option><option value="hacs" ${controlMode === "hacs" ? "selected" : ""}>HACS mag besturen</option></select></label>
      </div>
      <div class="button-row"><button class="primary" data-action="setup-save">Koppelingen opslaan</button><button data-action="setup-test">Verbinding testen</button><button data-action="open-settings">Geavanceerde instellingen</button></div>
      <div class="connection-summary">Status: <strong>${this._escape(this._state("sensor.ev_smart_charge_setup_status"))}</strong> · Test: <strong>${this._escape(this._state("sensor.ev_smart_charge_connection_test_status"))}</strong><br>${this._escape(this._state("sensor.ev_smart_charge_connection_test_reason", "Nog niet getest"))}</div>`);
  }

  _render() {
    if (!this._hass || !this.shadowRoot) return;
    const active = this.shadowRoot.activeElement;
    if (active && ["INPUT", "TEXTAREA"].includes(active.tagName)) return;

    const ai = this._state("switch.ev_smart_charge_ai_enabled", "off") === "on";
    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main>
        <header class="hero">
          <div>
            <p class="eyebrow">EV SMART CHARGE</p>
            <h1>Laadplanner</h1>
            <p class="muted">Lokale planning met optionele AI-keuze</p>
          </div>
          <button class="secondary" data-action="open-settings">⚙ Instellingen</button>
        </header>

        <div class="notice" role="status"></div>

        ${this._integrationConfigured() ? "" : `<div class="warning"><strong>Integratie nog niet gekoppeld</strong><br>Open Instellingen → Apparaten & diensten → EV Smart Charge Planner en configureer de sensorverbindingen. Daarna verschijnen de entities in dit panel.</div>`}

        ${this._setupCard()}

        ${this._card("Live status", `<div class="metrics">
          ${this._metric("Planstatus", "sensor.ev_smart_charge_status")}
          ${this._metric("SoC", "sensor.ev_smart_charge_soc", "%", 1)}
          ${this._metric("Laadvermogen", "sensor.ev_smart_charge_power_kw", " kW")}
          ${this._metric("Huidig tarief", "sensor.ev_smart_charge_current_tariff", " €/kWh")}
          ${this._metric("Auto aangesloten", "sensor.ev_smart_charge_plug_state")}
          ${this._metric("Laadpaalstatus", "sensor.ev_smart_charge_charger_state")}
          ${this._metric("Peblar switch", "sensor.ev_smart_charge_charger_switch_state")}
          ${this._metric("Sessie-energie", "sensor.ev_smart_charge_session_energy_source_kwh", " kWh")}
          ${this._metric("Tariefblokken", "sensor.ev_smart_charge_tariff_slots")}
        </div>`)}

        ${this._card("Forecast", `<div class="metrics">
          ${this._metric("Zonneforecast", "sensor.ev_smart_charge_solar_forecast_kwh", " kWh")}
          ${this._metric("Zonvermogen nu", "sensor.ev_smart_charge_solar_now_w", " W")}
          ${this._metric("Auto laadstatus", "sensor.ev_smart_charge_charging_state")}
          ${this._metric("Doelstatus", "sensor.ev_smart_charge_target_state")}
        </div><p class="muted">De tariefsensor wordt lokaal gelezen en aan de planner doorgegeven.</p><div class="forecast"><h3>Beschikbare tarieven</h3>${this._forecastRows()}</div>`)}

        <div class="columns">
          ${this._card("Laadplan", `<div class="metrics">
            ${this._metric("Start", "sensor.ev_smart_charge_plan_start")}
            ${this._metric("Verwacht klaar", "sensor.ev_smart_charge_plan_end")}
            ${this._metric("Benodigd", "sensor.ev_smart_charge_plan_kwh", " kWh")}
            ${this._metric("Kosten", "sensor.ev_smart_charge_plan_cost", " €")}
            ${this._metric("ERE", "sensor.ev_smart_charge_plan_ere", " €")}
            ${this._metric("Netto", "sensor.ev_smart_charge_plan_net", " €")}
          </div>
          <div class="form-row"><label>Doelpercentage<input id="target-soc" type="number" min="50" max="100" step="5" value="${this._escape(this._state("number.ev_smart_charge_target_soc_percent", "95"))}"></label><label>Deadline<input id="deadline" type="time"></label></div>
          <div class="button-row"><button data-action="plan-today">📅 Vandaag</button><button data-action="plan-flex">🌞 Flexibel</button><button data-action="plan-deadline">⏰ Deadline</button></div>
          <div class="button-row"><button class="primary" data-action="start">▶ Start</button><button data-action="stop">■ Stop</button><button data-action="reset">↻ Reset</button></div>`)}

          ${this._card("Huidige sessie", `<div class="metrics">
            ${this._metric("Geladen", "sensor.ev_smart_charge_session_kwh", " kWh")}
            ${this._metric("Kosten", "sensor.ev_smart_charge_session_cost", " €")}
            ${this._metric("ERE", "sensor.ev_smart_charge_session_ere", " €")}
            ${this._metric("Netto", "sensor.ev_smart_charge_session_net", " €")}
          </div>`)}
        </div>

        ${this._card("Overzichten", `<div class="periods">
          <div><h3>Vandaag</h3>${this._metric("kWh", "sensor.ev_smart_charge_today_kwh")} ${this._metric("Netto", "sensor.ev_smart_charge_today_net", " €")} ${this._metric("Sessies", "sensor.ev_smart_charge_today_sessions")}</div>
          <div><h3>Deze maand</h3>${this._metric("kWh", "sensor.ev_smart_charge_month_kwh")} ${this._metric("Netto", "sensor.ev_smart_charge_month_net", " €")} ${this._metric("Sessies", "sensor.ev_smart_charge_month_sessions")}</div>
          <div><h3>Dit jaar</h3>${this._metric("kWh", "sensor.ev_smart_charge_year_kwh")} ${this._metric("Netto", "sensor.ev_smart_charge_year_net", " €")} ${this._metric("Sessies", "sensor.ev_smart_charge_year_sessions")}</div>
        </div>`)}

        ${this._card("🧪 Testplannen", `<p class="muted">Deze tests lezen de actuele tarieven en forecast uit. Er wordt niets opgeslagen en de Peblar wordt nooit geschakeld.</p>
          <div class="button-row"><button data-action="test-flex">🧪 Test flex</button><button data-action="test-plan">🧪 Test plan</button></div>
          <div class="metrics test-summary">
            ${this._metric("Teststatus", "sensor.ev_smart_charge_test_status")}
            ${this._metric("Testmodus", "sensor.ev_smart_charge_test_mode")}
            ${this._metric("Toelichting", "sensor.ev_smart_charge_test_reason")}
            ${this._metric("Start", "sensor.ev_smart_charge_test_start")}
            ${this._metric("Klaar", "sensor.ev_smart_charge_test_end")}
            ${this._metric("Benodigd", "sensor.ev_smart_charge_test_kwh", " kWh")}
            ${this._metric("Netto", "sensor.ev_smart_charge_test_net", " €")}
          </div>
          <div class="windows"><h3>Gekozen prijsblokken</h3>${this._testWindows()}</div>`)}

        ${this._card("Telegram", `<div class="button-row"><button class="primary" data-action="telegram-test">✈ Test</button><button data-action="telegram-plan">Plan</button><button data-action="telegram-start">Start</button><button data-action="telegram-done">Klaar</button><button data-action="telegram-stop">Stop</button><button data-action="telegram-blocked">Veiligheid</button></div>
          <div class="templates">
            ${this._template("text.ev_smart_charge_telegram_template_test", "Testbericht")}
            ${this._template("text.ev_smart_charge_telegram_template_plan", "Planbericht")}
            ${this._template("text.ev_smart_charge_telegram_template_start", "Startbericht")}
            ${this._template("text.ev_smart_charge_telegram_template_done", "Klaarbericht")}
            ${this._template("text.ev_smart_charge_telegram_template_stop", "Stopbericht")}
            ${this._template("text.ev_smart_charge_telegram_template_blocked", "Veiligheidsbericht")}
          </div>`)}

        ${this._card("Instellingen", `<div class="settings-grid">
          <label class="toggle"><input id="ai-enabled" type="checkbox" ${ai ? "checked" : ""}><span>AI gebruiken</span></label>
          <label>Doelpercentage<input data-number-entity="number.ev_smart_charge_target_soc_percent" type="number" min="50" max="100" step="5" value="${this._escape(this._state("number.ev_smart_charge_target_soc_percent", "95"))}"></label>
          <label>Laadvermogen<input data-number-entity="number.ev_smart_charge_charge_power_kw" type="number" min="1" max="50" step="0.1" value="${this._escape(this._state("number.ev_smart_charge_charge_power_kw", "11"))}"></label>
          <label>Accucapaciteit<input data-number-entity="number.ev_smart_charge_battery_capacity_kwh" type="number" min="1" max="200" step="0.1" value="${this._escape(this._state("number.ev_smart_charge_battery_capacity_kwh", "91"))}"></label>
          <label>Efficiëntie<input data-number-entity="number.ev_smart_charge_charge_efficiency" type="number" min="0.5" max="1" step="0.01" value="${this._escape(this._state("number.ev_smart_charge_charge_efficiency", "0.9"))}"></label>
          <label>ERE per kWh<input data-number-entity="number.ev_smart_charge_ere_rate_eur_per_kwh" type="number" min="-1" max="2" step="0.01" value="${this._escape(this._state("number.ev_smart_charge_ere_rate_eur_per_kwh", "0.12"))}"></label>
        </div>
        <p class="muted">Sensorverbindingen, Telegram-service, chat-ID en API-key beheer je via de Home Assistant-integratie-instellingen.</p>`)}
      </main>`;
    this._wire();
  }

  _styles() {
    return `
      :host { --ev-accent:#ff9f1c; --ev-cyan:#35c2d8; --ev-green:#56c596; display:block; color:var(--primary-text-color); background:var(--primary-background-color); min-height:100vh; }
      * { box-sizing:border-box; }
      main { max-width:1180px; margin:0 auto; padding:32px 26px 52px; }
      .hero { display:flex; justify-content:space-between; align-items:center; gap:22px; padding:24px 26px; margin-bottom:22px; background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,.14); }
      .eyebrow { color:var(--ev-accent); font-size:12px; font-weight:800; letter-spacing:1.8px; margin:0 0 8px; }
      h1 { font-size:34px; line-height:1.1; margin:0; letter-spacing:.2px; }
      h2 { font-size:18px; margin:0 0 16px; }
      h3 { font-size:15px; margin:0 0 12px; }
      .muted { color:var(--secondary-text-color); margin:8px 0 0; line-height:1.45; }
      .warning { background:rgba(255,159,28,.16); border:1px solid rgba(255,159,28,.55); color:var(--primary-text-color); border-radius:10px; padding:14px 16px; margin-bottom:18px; line-height:1.45; }
      .card { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:14px; padding:22px; margin-bottom:18px; box-shadow:0 6px 18px rgba(0,0,0,.1); }
      .card h2 { display:flex; align-items:center; gap:10px; }
      .columns { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }
      .metrics { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
      .metric { background:var(--secondary-background-color); border-left:3px solid var(--ev-cyan); border-radius:8px; padding:11px 13px; min-width:0; }
      .metric span { display:block; color:var(--secondary-text-color); font-size:12px; margin-bottom:6px; }
      .metric strong { display:block; font-size:18px; line-height:1.25; overflow-wrap:anywhere; }
      .periods { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
      .periods > div { border-top:3px solid var(--ev-accent); background:var(--secondary-background-color); border-radius:9px; padding:14px; }
      .periods .metric { background:transparent; border-left:0; padding:4px 0; margin-bottom:4px; }
      .setup-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:16px; }
      .setup-field { min-width:0; }
      select { width:100%; color:var(--primary-text-color); background:var(--input-fill-color,transparent); border:1px solid var(--divider-color); border-radius:8px; font:inherit; padding:10px 11px; }
      .connection-summary { margin-top:16px; padding:12px 14px; background:var(--secondary-background-color); border-radius:8px; color:var(--secondary-text-color); line-height:1.5; }
      .connection-summary strong { color:var(--primary-text-color); }
      .form-row,.button-row,.settings-grid { display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }
      label { display:flex; flex-direction:column; gap:6px; color:var(--secondary-text-color); font-size:13px; flex:1 1 160px; }
      input,textarea { color:var(--primary-text-color); background:var(--input-fill-color,transparent); border:1px solid var(--divider-color); border-radius:8px; font:inherit; padding:10px 11px; }
      textarea { min-height:76px; resize:vertical; width:100%; }
      button { color:var(--primary-text-color); background:var(--secondary-background-color); border:1px solid var(--divider-color); border-radius:9px; padding:10px 14px; cursor:pointer; font:inherit; transition:transform .15s ease,filter .15s ease,border-color .15s ease; }
      button:hover { filter:brightness(1.14); transform:translateY(-1px); border-color:var(--ev-cyan); }
      button.primary { background:var(--ev-accent); color:#161616; border-color:transparent; font-weight:700; }
      .secondary { white-space:nowrap; }
      .templates { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-top:18px; }
      .windows { margin-top:18px; border-top:1px solid var(--divider-color); padding-top:14px; }
      .window { display:grid; grid-template-columns:1.2fr .9fr 1fr .7fr; gap:10px; padding:10px 0; border-bottom:1px solid var(--divider-color); font-size:14px; }
      .window strong { text-align:right; }
      .window span:last-child { text-align:right; }
      .forecast { margin-top:18px; border-top:1px solid var(--divider-color); padding-top:14px; max-height:300px; overflow:auto; }
      .forecast-row { display:flex; justify-content:space-between; gap:16px; padding:8px 10px; border-bottom:1px solid var(--divider-color); font-size:14px; }
      .forecast-row:nth-child(even) { background:var(--secondary-background-color); }
      .toggle { flex:0 0 auto; flex-direction:row; align-items:center; justify-content:flex-start; min-width:150px; padding-top:26px; }
      .toggle input { width:20px; height:20px; }
      .notice { min-height:0; opacity:0; color:var(--success-color,#43a047); margin:0 0 0; transition:opacity .2s; }
      .notice.visible { min-height:22px; opacity:1; margin-bottom:10px; }
      @media (max-width:800px) { main { padding:18px 14px 32px; } .columns,.periods,.templates,.setup-grid { grid-template-columns:1fr; } .hero { align-items:flex-start; flex-direction:column; } h1 { font-size:28px; } .window { grid-template-columns:1fr 1fr; } .window strong,.window span:last-child { text-align:left; } }
    `;
  }
}

customElements.define("ev-smart-charge-panel", EvSmartChargePanel);
