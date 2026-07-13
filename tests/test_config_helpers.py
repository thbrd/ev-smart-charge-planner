import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).parents[1]
PACKAGE = "ev_smart_charge_test_package"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/ev_smart_charge")]
sys.modules[PACKAGE] = package


def _load(module_name: str):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{module_name}",
        ROOT / "custom_components/ev_smart_charge" / f"{module_name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


const = _load("const")
helpers = _load("config_helpers")


def test_entity_data_wins_over_legacy_option_value():
    values = helpers.merged_entry_values(
        {const.CONF_SOC_ENTITY: "sensor.new_soc"},
        {const.CONF_SOC_ENTITY: "sensor.old_soc", const.CONF_CHARGE_POWER: 7},
    )

    assert values[const.CONF_SOC_ENTITY] == "sensor.new_soc"
    assert values[const.CONF_CHARGE_POWER] == 7


def test_legacy_entity_options_are_removed_before_save():
    options = helpers.without_entity_options({
        const.CONF_SOC_ENTITY: "sensor.old_soc",
        const.CONF_AI_ENABLED: True,
    })

    assert const.CONF_SOC_ENTITY not in options
    assert options[const.CONF_AI_ENABLED] is True


def test_legacy_entity_options_are_migrated_once_to_config_data():
    data, options = helpers.canonical_entry_storage(
        {},
        {
            const.CONF_SOC_ENTITY: "sensor.legacy_soc",
            const.CONF_AI_ENABLED: True,
        },
    )

    assert data[const.CONF_SOC_ENTITY] == "sensor.legacy_soc"
    assert const.CONF_SOC_ENTITY not in options
    assert options[const.CONF_AI_ENABLED] is True


if __name__ == "__main__":
    test_entity_data_wins_over_legacy_option_value()
    test_legacy_entity_options_are_removed_before_save()
    test_legacy_entity_options_are_migrated_once_to_config_data()
    print("config helper tests: PASS")
