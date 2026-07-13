from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "custom_components/ev_smart_charge/frontend/ev-smart-charge-panel.js"
INIT = ROOT / "custom_components/ev_smart_charge/__init__.py"


def test_panel_uses_stable_event_delegation_and_pending_guard():
    source = FRONTEND.read_text()
    assert 'shadowRoot.addEventListener("click"' in source
    assert "this._pending" in source
    assert "event.preventDefault()" in source
    assert "_wire()" not in source
    assert "set hass(value)" in source
    assert "this._renderShell()" in source
    assert "this._refresh()" in source


def test_panel_resolves_only_known_ev_entity_names():
    source = FRONTEND.read_text()
    assert "ev_smart_charge_planner_${key}" in source
    assert "objectId.endsWith(`_ev_smart_charge_${key}`)" in source
    assert "objectId.endsWith(`_${key}`)" not in source


def test_panel_cache_version_is_bumped_with_frontend_contract():
    source = INIT.read_text()
    assert 'PANEL_CACHE_VERSION = "0.5.3"' in source
    assert "module_url" in source
