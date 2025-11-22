from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.automated_cover_control.const import (
    CONF_DEFAULT_COVER_POSITION,
    CONF_DISTANCE_FROM_WINDOW,
    CONF_ENTITIES,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_WINDOW_AZIMUTH,
    CONF_WINDOW_HEIGHT,
    DOMAIN,
)

OPTIONS = {
    CONF_DEFAULT_COVER_POSITION: 100.0,
    CONF_DISTANCE_FROM_WINDOW: 0.1,
    CONF_ENTITIES: ["cover.foo"],
    CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
    CONF_WINDOW_AZIMUTH: 200.0,
    CONF_WINDOW_HEIGHT: 1.0,
}


async def test_sensors(hass: HomeAssistant, return_fake_cover_data):
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_refresh()

    state = hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start")
    assert state
    assert state.state == "2025-01-01T00:00:01+00:00"

    state = hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end")
    assert state
    assert state.state == "2025-01-01T23:59:59+00:00"

    state = hass.states.get("sensor.foo_automated_cover_control_target_cover_position")
    assert state
    assert state.state == "66"

    state = hass.states.get("sensor.foo_automated_cover_control_state")
    assert state
    assert state.state == "sun_not_in_front_of_window"
    assert state.attributes["tweaks"] == ["after_sunset_or_before_sunrise"]
