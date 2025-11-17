from datetime import datetime
from unittest.mock import DEFAULT, patch

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
)
from homeassistant.components.switch import (
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

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
)
from custom_components.automated_cover_control.why import (
    CoverControlReason,
    CoverControlTweaks,
)

OPTIONS = {
    CONF_DEFAULT_COVER_POSITION: 100.0,
    CONF_DISTANCE_FROM_WINDOW: 0.1,
    CONF_ENTITIES: ["cover.foo"],
    CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
    CONF_WINDOW_AZIMUTH: 200.0,
    CONF_WINDOW_HEIGHT: 1.0,
}


async def test_manual_override_switch(hass: HomeAssistant):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        _async_update_data=DEFAULT,
        async_enable_detection_of_manual_override=DEFAULT,
        async_disable_detection_of_manual_override=DEFAULT,
    ) as mocks:
        mocks["_async_update_data"].return_value = AutomatedCoverControlData(
            attributes={},
            states={
                "sun_in_window_start": datetime.fromisoformat("2025-01-01T00:00:01Z"),
                "sun_in_window_end": datetime.fromisoformat("2025-01-01T23:59:59Z"),
                "target_position": 66,
                "reason": CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW,
                "tweaks": [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE],
                "manual_override": None,
                "covers_under_manual_control": [],
                "sun_in_front_of_window": None,
            },
        )

        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("switch.foo_automated_cover_control_enable_detection_of_manual_overrides")
        assert state

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_detection_of_manual_overrides",
            },
            blocking=True,
        )
        mocks["async_disable_detection_of_manual_override"].assert_called_once()

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_detection_of_manual_overrides",
            },
            blocking=True,
        )
        mocks["async_enable_detection_of_manual_override"].assert_called()


async def test_control_switch(hass: HomeAssistant):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        _async_update_data=DEFAULT,
        async_enable_automated_control=DEFAULT,
        async_disable_automated_control=DEFAULT,
    ) as mocks:
        mocks["_async_update_data"].return_value = AutomatedCoverControlData(
            attributes={},
            states={
                "sun_in_window_start": datetime.fromisoformat("2025-01-01T00:00:01Z"),
                "sun_in_window_end": datetime.fromisoformat("2025-01-01T23:59:59Z"),
                "target_position": 66,
                "reason": CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW,
                "tweaks": [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE],
                "manual_override": None,
                "covers_under_manual_control": [],
                "sun_in_front_of_window": None,
            },
        )

        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("switch.foo_automated_cover_control_enable_automated_control")
        assert state

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_automated_control",
            },
            blocking=True,
        )
        mocks["async_disable_automated_control"].assert_called_once()

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_automated_control",
            },
            blocking=True,
        )
        mocks["async_enable_automated_control"].assert_called()


async def test_control_switch_no_covers(hass: HomeAssistant):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        _async_update_data=DEFAULT,
        async_enable_automated_control=DEFAULT,
        async_disable_automated_control=DEFAULT,
    ) as mocks:
        mocks["_async_update_data"].return_value = AutomatedCoverControlData(
            attributes={},
            states={
                "sun_in_window_start": datetime.fromisoformat("2025-01-01T00:00:01Z"),
                "sun_in_window_end": datetime.fromisoformat("2025-01-01T23:59:59Z"),
                "target_position": 66,
                "reason": CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW,
                "tweaks": [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE],
                "manual_override": None,
                "covers_under_manual_control": [],
                "sun_in_front_of_window": None,
            },
        )

        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS | {CONF_ENTITIES: []})
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("switch.foo_automated_cover_control_enable_automated_control")
        assert state is None


async def test_control_switch_last_state_on(hass: HomeAssistant):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        _async_update_data=DEFAULT,
        async_enable_automated_control=DEFAULT,
        async_disable_automated_control=DEFAULT,
    ) as mocks:
        mocks["_async_update_data"].return_value = AutomatedCoverControlData(
            attributes={},
            states={
                "sun_in_window_start": datetime.fromisoformat("2025-01-01T00:00:01Z"),
                "sun_in_window_end": datetime.fromisoformat("2025-01-01T23:59:59Z"),
                "target_position": 66,
                "reason": CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW,
                "tweaks": [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE],
                "manual_override": None,
                "covers_under_manual_control": [],
                "sun_in_front_of_window": None,
            },
        )
        mock_restore_cache(
            hass,
            (
                State(
                    "switch.foo_automated_cover_control_enable_automated_control",
                    STATE_ON,
                ),
            ),
        )

        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("switch.foo_automated_cover_control_enable_automated_control")
        assert state
        assert state.state == STATE_ON

        mocks["async_disable_automated_control"].assert_not_called()
        mocks["async_enable_automated_control"].assert_called()


async def test_control_switch_last_state_off(hass: HomeAssistant):
    with patch.multiple(
        "custom_components.automated_cover_control.coordinator.AutomatedCoverControlDataUpdateCoordinator",
        _async_update_data=DEFAULT,
        async_enable_automated_control=DEFAULT,
        async_disable_automated_control=DEFAULT,
    ) as mocks:
        mocks["_async_update_data"].return_value = AutomatedCoverControlData(
            attributes={},
            states={
                "sun_in_window_start": datetime.fromisoformat("2025-01-01T00:00:01Z"),
                "sun_in_window_end": datetime.fromisoformat("2025-01-01T23:59:59Z"),
                "target_position": 66,
                "reason": CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW,
                "tweaks": [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE],
                "manual_override": None,
                "covers_under_manual_control": [],
                "sun_in_front_of_window": None,
            },
        )
        mock_restore_cache(
            hass,
            (
                State(
                    "switch.foo_automated_cover_control_enable_automated_control",
                    STATE_OFF,
                ),
            ),
        )

        entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("switch.foo_automated_cover_control_enable_automated_control")
        assert state
        assert state.state == STATE_OFF

        mocks["async_disable_automated_control"].assert_called()
        mocks["async_enable_automated_control"].assert_not_called()
