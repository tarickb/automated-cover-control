import logging
from datetime import UTC, datetime, timedelta

import time_machine
from homeassistant.components import button, cover, demo, sun, switch
from homeassistant.components.cover import ATTR_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import state_attr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_unordered import unordered

from custom_components.automated_cover_control.const import (
    CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION,
    CONF_CALC_ROUNDING,
    CONF_DEFAULT_COVER_POSITION,
    CONF_DISTANCE_FROM_WINDOW,
    CONF_END_TIME,
    CONF_ENTITIES,
    CONF_INVERT,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MINIMUM_CHANGE_TIME,
    CONF_RETURN_TO_DEFAULT_AT_END_TIME,
    CONF_START_TIME,
    CONF_WINDOW_AZIMUTH,
    CONF_WINDOW_HEIGHT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

TEST_COVER = "cover.living_room_window"
DEFAULT_OPTIONS = {
    CONF_DEFAULT_COVER_POSITION: 100.0,
    CONF_DISTANCE_FROM_WINDOW: 0.1,
    CONF_ENTITIES: [TEST_COVER],
    CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
    CONF_WINDOW_AZIMUTH: 90.0,
    CONF_WINDOW_HEIGHT: 1.0,
    CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION: 20,
    CONF_MINIMUM_CHANGE_TIME: {},
    CONF_CALC_ROUNDING: -1,  # Demo cover only moves in 10% increments.
}


def tm_as_datetime(tm: time_machine.Coordinates):
    return datetime.fromtimestamp(tm.time(), tz=UTC)


async def tm_tick_manually(
    hass: HomeAssistant,
    tm: time_machine.Coordinates,
    delta: timedelta,
    increment: timedelta = timedelta(seconds=1),
):
    await tm_advance_to(hass, tm, tm_as_datetime(tm) + delta, increment)


async def tm_advance_to(
    hass: HomeAssistant,
    tm: time_machine.Coordinates,
    target_time: datetime,
    increment: timedelta = timedelta(seconds=1),
):
    if target_time < tm_as_datetime(tm):
        raise Exception(f"Target time is in the past! Target = {target_time}, now = {tm_as_datetime(tm)}")
    while tm_as_datetime(tm) < target_time:
        tm.shift(increment)
        async_fire_time_changed(hass, tm_as_datetime(tm))
        await hass.async_block_till_done()
    _LOGGER.debug("[advance_to] advanced time to %s", tm_as_datetime(tm))


# Must be done with frozen time!
async def setup_home_assistant_test(hass: HomeAssistant):
    # San Francisco, CA
    hass.config.latitude = 37.7620405311152
    hass.config.longitude = -122.4349247380084
    hass.config.elevation = 0
    hass.config.time_zone = "US/Pacific"

    await async_setup_component(hass, "homeassistant", {})
    await async_setup_component(hass, sun.DOMAIN, {sun.DOMAIN: {}})
    await async_setup_component(hass, demo.DOMAIN, {demo.DOMAIN: {}})
    await hass.async_block_till_done()


async def test_default(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-26T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-26T19:50:00+00:00"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "off"

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:04:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "30"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "on"
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    # Advance to peak sun.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "100"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "on"

    # Demo cover round position to multiples of 10.
    assert state_attr(hass, TEST_COVER, "current_position") == 100

    # And now advance to later in the day, but before sunset, where the sun not in front of the window.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T22:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "100"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "off"
    assert state_attr(hass, TEST_COVER, "current_position") == 100

    # Advance to past sunset.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T01:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Should still be in the same state an hour later.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T02:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert state_attr(hass, TEST_COVER, "current_position") == 20


async def test_with_manual_overrides(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS | {CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 30}}
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:04:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "30"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    # Manually move the cover.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 20},
        blocking=True,
    )
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "on"

    # Advance 20 minutes; should still be under manual control.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:24:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "under_manual_control"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "on"
    assert (
        "manually_controlled"
        in hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").attributes
    )
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").attributes[
        "manually_controlled"
    ] == [TEST_COVER]
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Advance to peak sun.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "100"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"
    assert state_attr(hass, TEST_COVER, "current_position") == 100

    # And now advance to later in the day, but before sunset, where the sun not in front of the window.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T22:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "100"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert state_attr(hass, TEST_COVER, "current_position") == 100

    # Advance to past sunset.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T01:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Should still be in the same state an hour later.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T02:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert state_attr(hass, TEST_COVER, "current_position") == 20


async def test_with_manual_overrides_and_reset_button(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS | {CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 30}}
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:04:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "30"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    # Manually move the cover.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 20},
        blocking=True,
    )
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "on"

    # Advance 5 minutes; should still be under manual control.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:09:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "under_manual_control"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "on"
    assert (
        "manually_controlled"
        in hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").attributes
    )
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").attributes[
        "manually_controlled"
    ] == [TEST_COVER]
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Press reset button.
    await hass.services.async_call(
        button.DOMAIN,
        button.SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.foo_automated_cover_control_reset_manual_override"},
        blocking=True,
    )

    # Should be back to automated control.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "30"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"
    assert state_attr(hass, TEST_COVER, "current_position") == 30


async def test_with_manual_overrides_and_switch(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS | {CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 30}}
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:04:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "30"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    # Disable detection of overrides.
    await hass.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_detection_of_manual_overrides",
        },
        blocking=True,
    )

    # Manually move the cover; it'll start reverting before the demo cover has had a chance to update.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 20},
        blocking=True,
    )
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 30

    # Advance 5 minutes; should still be unchanged.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:09:00Z"),
        increment=timedelta(minutes=1),
    )
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 30

    # Re-enable detection of overrides.
    await hass.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_detection_of_manual_overrides",
        },
        blocking=True,
    )

    # Manually move the cover.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 20},
        blocking=True,
    )
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Advance 5 minutes; should still be under manual control.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:14:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "under_manual_control"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "on"
    assert (
        "manually_controlled"
        in hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").attributes
    )
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").attributes[
        "manually_controlled"
    ] == [TEST_COVER]
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Disable detection of overrides, again.
    await hass.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_detection_of_manual_overrides",
        },
        blocking=True,
    )

    # Should be back to automated control.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "40"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"
    assert state_attr(hass, TEST_COVER, "current_position") == 40


async def test_with_configured_start_time(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS | {
        CONF_START_TIME: "12:30:00",  # Local
    }
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-26T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-26T19:50:00+00:00"

    # Should stay in the same position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "outside_control_time_range"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "unknown"
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # And now advance past sunrise but before the start time.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:29:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "outside_control_time_range"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "unknown"

    # Advance past start time.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:31:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "70"
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    # Give demo cover time to move.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 70

    # And now advance to later in the day, but before sunset, where the sun not in front of the window.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T22:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "100"
    assert state_attr(hass, TEST_COVER, "current_position") == 100

    # Advance to past sunset.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T01:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Should still be in the same state an hour later.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T02:45:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert state_attr(hass, TEST_COVER, "current_position") == 20


async def test_with_configured_end_time(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS | {
        CONF_END_TIME: "14:00:00",  # Local
        CONF_RETURN_TO_DEFAULT_AT_END_TIME: True,
    }
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )
    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-26T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-26T19:50:00+00:00"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:30:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "60"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    # Demo cover round position to multiples of 10.
    assert state_attr(hass, TEST_COVER, "current_position") == 60

    # And now advance to configured end time
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T21:01:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "end_time_reached"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []

    # Give demo cover time to move.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Should still be in the same state a few hours later.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T03:00:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "end_time_reached"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # And then should tick back over to a new day.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-27T08:01:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "20"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_not_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == unordered(
        ["solar_elevation_out_of_range", "after_sunset_or_before_sunrise"]
    )
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Sun start/end times should change too.
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-27T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-27T19:50:00+00:00"


async def test_inverted(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS | {CONF_INVERT: True}
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-26T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-26T19:50:00+00:00"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "off"

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:04:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "70"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == ["inverted"]
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "on"
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 70


async def test_with_long_time_threshold(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T13:00:00Z")  # Well before sunrise.
    options = DEFAULT_OPTIONS | {CONF_MINIMUM_CHANGE_TIME: {"minutes": 30}}
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-26T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-26T19:50:00+00:00"

    # Should move to sunset position, after we've passed the minimum-change-time threshold.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T14:00:00Z"),
        increment=timedelta(minutes=1),
    )
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "off"

    # And now advance past sunrise.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:04:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "30"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "on"
    assert hass.states.get("binary_sensor.foo_automated_cover_control_manual_override_detected").state == "off"

    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 30

    # Advance to near sun.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:36:00Z"),
        increment=timedelta(minutes=1),
    )
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "80"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "per_cover_reasons") == {
        TEST_COVER: "time_threshold_disallowed"
    }
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "on"


async def test_switch_off(hass: HomeAssistant):
    # San Francisco, CA
    # sunrise: 2025-10-26 07:29:00 local  sunset: 2025-10-26 18:17:00 local
    #          2025-10-26 14:29:00 UTC            2025-10-27 01:17:00 UTC
    now = datetime.fromisoformat("2025-10-26T14:00:00Z")  # Right before sunrise.
    options = DEFAULT_OPTIONS
    traveller = time_machine.travel(now)
    tm = traveller.start()

    # Set up test harness.
    await setup_home_assistant_test(hass)

    # Set the last-updated time for the cover to now.
    await hass.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: TEST_COVER, ATTR_POSITION: 80},
        blocking=True,
    )

    # Demo cover moves at 10% per second
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 80

    # More than the time threshold for cover changes
    tm.shift(delta=timedelta(seconds=5))
    await hass.async_block_till_done()

    # Set up automated cover control.
    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Ensure it's on.
    assert hass.states.get("switch.foo_automated_cover_control_enable_automated_control").state == "on"
    assert (
        hass.states.get("sensor.foo_automated_cover_control_sun_in_window_start").state == "2025-10-26T14:35:00+00:00"
    )
    assert hass.states.get("sensor.foo_automated_cover_control_sun_in_window_end").state == "2025-10-26T19:50:00+00:00"

    # Should move to sunset position.
    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 20
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "off"

    # Turn off automation
    await hass.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_automated_control",
        },
        blocking=True,
    )

    # Advance to peak sun.
    await tm_advance_to(
        hass,
        tm,
        datetime.fromisoformat("2025-10-26T19:45:00Z"),
        increment=timedelta(minutes=1),
    )

    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "unknown"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "automation_disabled"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "unknown"

    # Cover stays put.
    assert state_attr(hass, TEST_COVER, "current_position") == 20

    # Turn on automation
    await hass.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "switch.foo_automated_cover_control_enable_automated_control",
        },
        blocking=True,
    )

    # Cover moves.
    assert hass.states.get("sensor.foo_automated_cover_control_target_cover_position").state == "100"
    assert hass.states.get("sensor.foo_automated_cover_control_state").state == "sun_in_front_of_window"
    assert state_attr(hass, "sensor.foo_automated_cover_control_state", "tweaks") == []
    assert hass.states.get("binary_sensor.foo_automated_cover_control_sun_in_front_of_window").state == "on"

    await tm_tick_manually(hass, tm, timedelta(seconds=10))
    assert state_attr(hass, TEST_COVER, "current_position") == 100
