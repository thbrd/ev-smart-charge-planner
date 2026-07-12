DOMAIN = "ev_smart_charge"
PLATFORMS = ["sensor", "number", "switch", "text"]

CONF_PROFILE_NAME = "profile_name"
CONF_SOC_ENTITY = "soc_entity"
CONF_PLUG_ENTITY = "plug_entity"
CONF_CHARGING_ENTITY = "charging_entity"
CONF_TARGET_ENTITY = "target_entity"
CONF_CHARGER_STATE_ENTITY = "charger_state_entity"
CONF_CHARGER_SWITCH_ENTITY = "charger_switch_entity"
CONF_POWER_ENTITY = "power_entity"
CONF_SESSION_ENERGY_ENTITY = "session_energy_entity"
CONF_TARIFF_ENTITY = "tariff_entity"
CONF_TARIFF_PROVIDER = "tariff_provider"
CONF_SOLAR_FORECAST_ENTITY = "solar_forecast_entity"
CONF_SOLAR_NOW_ENTITY = "solar_now_entity"
CONF_CONTROL_MODE = "control_mode"

CONF_BATTERY_CAPACITY = "battery_capacity_kwh"
CONF_CHARGE_POWER = "charge_power_kw"
CONF_EFFICIENCY = "charge_efficiency"
CONF_TARGET_SOC = "target_soc_percent"
CONF_ERE_RATE = "ere_rate_eur_per_kwh"
CONF_PETROL_PRICE = "petrol_price_eur_per_liter"
CONF_PETROL_CONSUMPTION = "petrol_l_per_100km"
CONF_AI_ENABLED = "ai_enabled"
CONF_AI_MODE = "ai_mode"
CONF_AI_API_KEY = "ai_api_key"
CONF_AI_MODEL = "ai_model"

CONF_TELEGRAM_ENABLED = "telegram_enabled"
CONF_TELEGRAM_SERVICE = "telegram_service"
CONF_TELEGRAM_CHAT_ID = "telegram_chat_id"
CONF_TELEGRAM_TEMPLATE_TEST = "telegram_template_test"
CONF_TELEGRAM_TEMPLATE_PLAN = "telegram_template_plan"
CONF_TELEGRAM_TEMPLATE_START = "telegram_template_start"
CONF_TELEGRAM_TEMPLATE_DONE = "telegram_template_done"
CONF_TELEGRAM_TEMPLATE_STOP = "telegram_template_stop"
CONF_TELEGRAM_TEMPLATE_BLOCKED = "telegram_template_blocked"

AI_MODES = ["local", "explain", "choose_candidate"]
TARIFF_PROVIDERS = ["auto", "zonneplan", "tibber", "anwb", "generic"]
CONTROL_MODES = ["monitor", "hacs"]
DEFAULTS = {
    CONF_BATTERY_CAPACITY: 91.0,
    CONF_CHARGE_POWER: 11.0,
    CONF_EFFICIENCY: 0.90,
    CONF_TARGET_SOC: 95.0,
    CONF_ERE_RATE: 0.12,
    CONF_PETROL_PRICE: 2.30,
    CONF_PETROL_CONSUMPTION: 9.0,
    CONF_AI_ENABLED: False,
    CONF_AI_MODE: "local",
    CONF_AI_MODEL: "gpt-5.4-mini",
    CONF_TARIFF_PROVIDER: "auto",
    CONF_CONTROL_MODE: "monitor",
    CONF_TELEGRAM_ENABLED: False,
    CONF_TELEGRAM_SERVICE: "telegram_bot.send_message",
    CONF_TELEGRAM_CHAT_ID: "",
    CONF_TELEGRAM_TEMPLATE_TEST: "🧪 EV Smart Charge test\nStatus: {status}\nSoC: {soc}%\nDoel: {target}%\nPlan: {plan_start} - {plan_end}",
    CONF_TELEGRAM_TEMPLATE_PLAN: "🧠 EV-plan gemaakt\nDoel: {target}%\nStart: {plan_start}\nKlaar: {plan_end}\nNodig: {plan_kwh} kWh\nKosten: €{plan_cost}\nERE: €{plan_ere}\nNetto: €{plan_net}",
    CONF_TELEGRAM_TEMPLATE_START: "🚗 EV laden gestart\nSoC: {soc}% → {target}%\nVerwacht: {plan_kwh} kWh\nVerwacht klaar: {plan_end}",
    CONF_TELEGRAM_TEMPLATE_DONE: "✅ EV laden klaar\nGeladen: {session_kwh} kWh\nKosten: €{session_cost}\nERE: €{session_ere}\nNetto: €{session_net}",
    CONF_TELEGRAM_TEMPLATE_STOP: "🛑 EV laden handmatig gestopt\nGeladen: {session_kwh} kWh\nKosten: €{session_cost}\nERE: €{session_ere}\nNetto: €{session_net}",
    CONF_TELEGRAM_TEMPLATE_BLOCKED: "🛡️ EV laden geblokkeerd\nDe veiligheidscontrole staat laden niet toe.\nSoC: {soc}%\nPeblar: {charger_state}"
}

SERVICE_CREATE_PLAN = "create_plan"
SERVICE_SIMULATE_PLAN = "simulate_plan"
SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_RESET = "reset"
SERVICE_STATUS = "status"
SERVICE_TELEGRAM_TEST = "telegram_test"
SERVICE_TELEGRAM_SEND = "telegram_send"
SERVICE_TEST_FLEX = "test_flex"
SERVICE_TEST_PLAN = "test_plan"
SERVICE_UPDATE_SETUP = "update_setup"
SERVICE_TEST_CONNECTION = "test_connection"

SETUP_ENTITY_KEYS = (
    CONF_SOC_ENTITY,
    CONF_PLUG_ENTITY,
    CONF_CHARGING_ENTITY,
    CONF_TARGET_ENTITY,
    CONF_CHARGER_STATE_ENTITY,
    CONF_CHARGER_SWITCH_ENTITY,
    CONF_POWER_ENTITY,
    CONF_SESSION_ENERGY_ENTITY,
    CONF_TARIFF_ENTITY,
    CONF_SOLAR_FORECAST_ENTITY,
    CONF_SOLAR_NOW_ENTITY,
)

TELEGRAM_EVENTS = ["test", "plan", "start", "done", "stop", "blocked"]
TELEGRAM_TEMPLATE_KEYS = {
    "test": CONF_TELEGRAM_TEMPLATE_TEST,
    "plan": CONF_TELEGRAM_TEMPLATE_PLAN,
    "start": CONF_TELEGRAM_TEMPLATE_START,
    "done": CONF_TELEGRAM_TEMPLATE_DONE,
    "stop": CONF_TELEGRAM_TEMPLATE_STOP,
    "blocked": CONF_TELEGRAM_TEMPLATE_BLOCKED,
}
