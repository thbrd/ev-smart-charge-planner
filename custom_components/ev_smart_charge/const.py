DOMAIN = "ev_smart_charge"
PLATFORMS = ["sensor", "number", "switch"]

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
CONF_SOLAR_FORECAST_ENTITY = "solar_forecast_entity"
CONF_SOLAR_NOW_ENTITY = "solar_now_entity"

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

AI_MODES = ["local", "explain", "choose_candidate"]
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
    CONF_AI_MODEL: "gpt-5.4-mini"
}

SERVICE_CREATE_PLAN = "create_plan"
SERVICE_SIMULATE_PLAN = "simulate_plan"
SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_RESET = "reset"
SERVICE_STATUS = "status"
