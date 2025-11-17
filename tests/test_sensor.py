from datetime import datetime
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


async def test_sensors(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=OPTIONS)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    with patch.object(AutomatedCoverControlDataUpdateCoordinator, "_async_update_data") as mock:
        mock.return_value = AutomatedCoverControlData(
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
