import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "discovery", Path(__file__).parents[1] / "custom_components/ev_smart_charge/discovery.py"
)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


class State:
    def __init__(self, entity_id, friendly_name, unit=None, forecast=None):
        self.entity_id = entity_id
        self.attributes = {"friendly_name": friendly_name}
        if unit:
            self.attributes["unit_of_measurement"] = unit
        if forecast is not None:
            self.attributes["forecast"] = forecast


class States:
    def __init__(self, states):
        self._states = states

    def async_all(self):
        return self._states


class Hass:
    def __init__(self, states):
        self.states = States(states)


def test_discovery_prefers_tariff_sensor_with_forecast():
    hass = Hass([
        State("sensor.random_price", "Random price", "EUR/kWh"),
        State("sensor.zonneplan_current_electricity_tariff", "Zonneplan current tariff", "EUR/kWh", forecast=[{}]),
    ])
    candidates = discovery.discover_entities(hass)["tariff_entity"]
    assert candidates[0]["entity_id"] == "sensor.zonneplan_current_electricity_tariff"


if __name__ == "__main__":
    test_discovery_prefers_tariff_sensor_with_forecast()
    print("discovery tests: PASS")
