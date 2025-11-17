from unittest.mock import patch

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
from custom_components.automated_cover_control.coordinator import (
    AutomatedCoverControlData,
    AutomatedCoverControlDataUpdateCoordinator,
)

OPTIONS = {
    CONF_DEFAULT_COVER_POSITION: 100.0,
    CONF_DISTANCE_FROM_WINDOW: 0.1,
    CONF_ENTITIES: ["cover.foo"],
    CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
    CONF_WINDOW_AZIMUTH: 200.0,
    CONF_WINDOW_HEIGHT: 1.0,
}

STATES_TEMPLATE = {
    "sun_in_window_start": None,
    "sun_in_window_end": None,
    "target_position": None,
    "reason": None,
    "tweaks": [],
    "manual_override": None,
    "covers_under_manual_control": [],
    "sun_in_front_of_window": None,
}


async def test_sun_in_front_of_window_sensor(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    with patch.object(AutomatedCoverControlDataUpdateCoordinator, "_async_update_data") as mock:
        mock.return_value = AutomatedCoverControlData(
            attributes={}, states=dict(STATES_TEMPLATE, sun_in_front_of_window=False)
        )
        await coordinator.async_refresh()

        state = hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window")
        assert state
        assert state.state == "off"

        mock.return_value = AutomatedCoverControlData(
            attributes={}, states=dict(STATES_TEMPLATE, sun_in_front_of_window=True)
        )
        await coordinator.async_refresh()

        state = hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window")
        assert state
        assert state.state == "on"


async def test_manual_override_detected_sensor(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    with patch.object(AutomatedCoverControlDataUpdateCoordinator, "_async_update_data") as mock:
        mock.return_value = AutomatedCoverControlData(
            attributes={}, states=dict(STATES_TEMPLATE, manual_override=False)
        )
        await coordinator.async_refresh()

        state = hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected")
        assert state
        assert state.state == "off"
        assert len(state.attributes["manually_controlled"]) == 0

        mock.return_value = AutomatedCoverControlData(
            attributes={},
            states=dict(
                STATES_TEMPLATE,
                manual_override=True,
                covers_under_manual_control=["foo"],
            ),
        )
        await coordinator.async_refresh()

        state = hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected")
        assert state
        assert state.state == "on"
        assert state.attributes["manually_controlled"] == ["foo"]
