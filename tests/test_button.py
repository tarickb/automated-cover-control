from unittest.mock import DEFAULT, patch

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
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


async def test_button(hass: HomeAssistant, return_fake_cover_data):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        async_reset_manual_override=DEFAULT,
    ) as mocks:
        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("button.foo_automated_cover_control_reset_manual_override")
        assert state

        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.foo_automated_cover_control_reset_manual_override",
            },
            blocking=True,
        )
        mocks["async_reset_manual_override"].assert_called_once()


async def test_button_with_no_covers(hass: HomeAssistant, return_fake_cover_data):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        async_reset_manual_override=DEFAULT,
    ):
        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS | {CONF_ENTITIES: []})
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("button.foo_automated_cover_control_reset_manual_override")
        assert state is None
