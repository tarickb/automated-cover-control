import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_unordered import unordered

from custom_components.automated_cover_control.const import (
    CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_ENABLED,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_DEFAULT_COVER_POSITION,
    CONF_DISTANCE_FROM_WINDOW,
    CONF_END_TIME,
    CONF_END_TIME_ENTITY,
    CONF_ENTITIES,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_INVERT,
    CONF_LUX_ENTITY,
    CONF_LUX_THRESHOLD,
    CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS,
    CONF_MANUAL_OVERRIDE_IGNORE_NON_USER_TRIGGERED_CHANGES,
    CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT,
    CONF_MAX_SOLAR_ELEVATION,
    CONF_MAXIMUM_COVER_POSITION,
    CONF_MIN_SOLAR_ELEVATION,
    CONF_MINIMUM_CHANGE_PERCENTAGE,
    CONF_MINIMUM_CHANGE_TIME,
    CONF_MINIMUM_COVER_POSITION,
    CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW,
    CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW,
    CONF_PRESENCE_ENTITY,
    CONF_RETURN_TO_DEFAULT_AT_END_TIME,
    CONF_START_TIME,
    CONF_START_TIME_ENTITY,
    CONF_SUNRISE_OFFSET,
    CONF_SUNSET_OFFSET,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_STATE,
    CONF_WINDOW_AZIMUTH,
    CONF_WINDOW_HEIGHT,
    CONF_WINDOW_SENSOR_ENTITY,
    DOMAIN,
)


async def test_option_flow_window(hass: HomeAssistant, return_fake_cover_data) -> None:
    options = {
        CONF_DEFAULT_COVER_POSITION: 100.0,
        CONF_DISTANCE_FROM_WINDOW: 0.1,
        CONF_ENTITIES: ["cover.foo"],
        CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
        CONF_WINDOW_AZIMUTH: 200.0,
        CONF_WINDOW_HEIGHT: 1.0,
    }

    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == unordered(["window", "cover_position", "sensor", "automation", "manual_override"])

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "window"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_DISTANCE_FROM_WINDOW: 0.1,
            CONF_WINDOW_AZIMUTH: 200.0,
            CONF_WINDOW_HEIGHT: 1.0,
            CONF_MIN_SOLAR_ELEVATION: 40,
            CONF_MAX_SOLAR_ELEVATION: 30,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "window"
    assert result["errors"] == {CONF_MAX_SOLAR_ELEVATION: "max_solar_elevation_less_than_min"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_DISTANCE_FROM_WINDOW: 0.1,
            CONF_WINDOW_AZIMUTH: 200.0,
            CONF_WINDOW_HEIGHT: 1.0,
            CONF_MIN_SOLAR_ELEVATION: 30,
            CONF_MAX_SOLAR_ELEVATION: 40,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result
    assert result["data"] == options | {
        CONF_MIN_SOLAR_ELEVATION: 30,
        CONF_MAX_SOLAR_ELEVATION: 40,
        # Default options become part of the config.
        CONF_FOV_LEFT: 90,
        CONF_FOV_RIGHT: 90,
        CONF_BLIND_SPOT_ENABLED: False,
    }
    await hass.async_block_till_done()


async def test_option_flow_blind_spot(hass: HomeAssistant, return_fake_cover_data) -> None:
    options = {
        CONF_BLIND_SPOT_ENABLED: True,
        CONF_DEFAULT_COVER_POSITION: 100.0,
        CONF_DISTANCE_FROM_WINDOW: 0.1,
        CONF_ENTITIES: ["cover.foo"],
        CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
        CONF_WINDOW_AZIMUTH: 200.0,
        CONF_WINDOW_HEIGHT: 1.0,
    }

    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == unordered(
        [
            "window",
            "blind_spot",
            "cover_position",
            "sensor",
            "automation",
            "manual_override",
        ]
    )

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "blind_spot"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "blind_spot"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_BLIND_SPOT_LEFT: 20,
            CONF_BLIND_SPOT_RIGHT: 10,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "blind_spot"
    assert result["errors"] == {CONF_BLIND_SPOT_RIGHT: "blind_spot_right_less_than_left"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_BLIND_SPOT_LEFT: 10,
            CONF_BLIND_SPOT_RIGHT: 20,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result
    assert result["data"] == options | {
        CONF_BLIND_SPOT_ENABLED: True,
        CONF_BLIND_SPOT_LEFT: 10.0,
        CONF_BLIND_SPOT_RIGHT: 20.0,
    }
    await hass.async_block_till_done()


async def test_option_flow_cover_position(hass: HomeAssistant, return_fake_cover_data) -> None:
    options = {
        CONF_DEFAULT_COVER_POSITION: 70.0,
        CONF_MAXIMUM_COVER_POSITION: 80.0,
        CONF_ENTITIES: ["cover.foo"],
    }

    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == unordered(["window", "cover_position", "sensor", "automation", "manual_override"])

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "cover_position"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "cover_position"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ENTITIES: ["cover.foo"],
            CONF_DEFAULT_COVER_POSITION: 75.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result
    assert result["data"] == {
        # Should remove CONF_MAXIMUM_COVER_POSITION.
        CONF_ENTITIES: ["cover.foo"],
        CONF_DEFAULT_COVER_POSITION: 75.0,
        # Default options become part of the config.
        CONF_INVERT: False,
        CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: False,
        CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: False,
    }
    await hass.async_block_till_done()


async def test_option_flow_sensor(hass: HomeAssistant, return_fake_cover_data) -> None:
    options = {
        CONF_PRESENCE_ENTITY: "binary_sensor.foo",
        CONF_WEATHER_ENTITY: "weather.foo",
        CONF_WEATHER_STATE: ["clear", "cloudy"],
    }

    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == unordered(["window", "cover_position", "sensor", "automation", "manual_override"])

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "sensor"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sensor"

    with pytest.raises(InvalidData) as ex:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_PRESENCE_ENTITY: "binary_sensor.foo",
                CONF_WEATHER_ENTITY: "weather.foo",
                # Invalid weather state.
                CONF_WEATHER_STATE: ["xyz"],
            },
        )
    assert "weather_state" in str(ex.value)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PRESENCE_ENTITY: "binary_sensor.foo",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result
    assert result["data"] == {
        # Should remove weather options.
        CONF_PRESENCE_ENTITY: "binary_sensor.foo",
        # Default options become part of the config.
        CONF_LUX_THRESHOLD: 1000.0,
        CONF_WEATHER_STATE: ["sunny", "partlycloudy", "cloudy", "clear"],
    }
    await hass.async_block_till_done()


async def test_option_flow_automation(hass: HomeAssistant, return_fake_cover_data) -> None:
    options = {
        CONF_SUNSET_OFFSET: {"minutes": 10},
        CONF_START_TIME_ENTITY: "input_datetime.foo",
        CONF_RETURN_TO_DEFAULT_AT_END_TIME: False,
    }

    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == unordered(["window", "cover_position", "sensor", "automation", "manual_override"])

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "automation"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "automation"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SUNRISE_OFFSET: {"minutes": 30},
            CONF_SUNSET_OFFSET: {"minutes": 20},
            CONF_START_TIME_ENTITY: "input_datetime.bar",
            CONF_RETURN_TO_DEFAULT_AT_END_TIME: True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result
    assert result["data"] == {
        CONF_SUNRISE_OFFSET: {"minutes": 30},
        CONF_SUNSET_OFFSET: {"minutes": 20},
        CONF_START_TIME_ENTITY: "input_datetime.bar",
        CONF_RETURN_TO_DEFAULT_AT_END_TIME: True,
        # Default options become part of the config.
        CONF_MINIMUM_CHANGE_PERCENTAGE: 1,
        CONF_MINIMUM_CHANGE_TIME: {"minutes": 2},
    }
    await hass.async_block_till_done()


async def test_option_flow_manual_override(hass: HomeAssistant, return_fake_cover_data) -> None:
    options = {
        CONF_MANUAL_OVERRIDE_DURATION: {"hours": 5},
    }

    entry = MockConfigEntry(domain=DOMAIN, data={"name": "foo"}, options=options)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result["menu_options"] == unordered(["window", "cover_position", "sensor", "automation", "manual_override"])

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "manual_override"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_override"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MANUAL_OVERRIDE_DURATION: {"hours": 1},
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result
    assert result["data"] == {
        CONF_MANUAL_OVERRIDE_DURATION: {"hours": 1},
        # Default options become part of the config.
        CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: False,
        CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS: False,
        CONF_MANUAL_OVERRIDE_IGNORE_NON_USER_TRIGGERED_CHANGES: False,
    }
    await hass.async_block_till_done()


async def test_initial_config_flow(hass: HomeAssistant, return_fake_cover_data) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"name": "foo"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "window"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_WINDOW_AZIMUTH: 123,
            CONF_WINDOW_HEIGHT: 1.23,
            CONF_DISTANCE_FROM_WINDOW: 0.123,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "cover_position"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_ENTITIES: ["cover.foo"],
            CONF_DEFAULT_COVER_POSITION: 30,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sensor"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "automation"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_override"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "foo Automated Cover Control"
    assert result["data"] == {"name": "foo"}
    assert result["options"] == {
        CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION: None,
        CONF_BLIND_SPOT_ELEVATION: None,
        CONF_BLIND_SPOT_ENABLED: False,
        CONF_BLIND_SPOT_LEFT: None,
        CONF_BLIND_SPOT_RIGHT: None,
        CONF_DEFAULT_COVER_POSITION: 30.0,
        CONF_DISTANCE_FROM_WINDOW: 0.123,
        CONF_END_TIME: None,
        CONF_END_TIME_ENTITY: None,
        CONF_ENTITIES: ["cover.foo"],
        CONF_FOV_LEFT: 90.0,
        CONF_FOV_RIGHT: 90.0,
        CONF_INVERT: False,
        CONF_LUX_ENTITY: None,
        CONF_LUX_THRESHOLD: 1000.0,
        CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD: None,
        CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 15},
        CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS: False,
        CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: False,
        CONF_MAXIMUM_COVER_POSITION: None,
        CONF_MAX_SOLAR_ELEVATION: None,
        CONF_MINIMUM_CHANGE_PERCENTAGE: 1.0,
        CONF_MINIMUM_CHANGE_TIME: {"minutes": 2},
        CONF_MINIMUM_COVER_POSITION: None,
        CONF_MIN_SOLAR_ELEVATION: None,
        CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: False,
        CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: False,
        CONF_PRESENCE_ENTITY: None,
        CONF_RETURN_TO_DEFAULT_AT_END_TIME: False,
        CONF_START_TIME: None,
        CONF_START_TIME_ENTITY: None,
        CONF_SUNRISE_OFFSET: None,
        CONF_SUNSET_OFFSET: None,
        CONF_WEATHER_ENTITY: None,
        CONF_WEATHER_STATE: ["sunny", "partlycloudy", "cloudy", "clear"],
        CONF_WINDOW_AZIMUTH: 123.0,
        CONF_WINDOW_HEIGHT: 1.23,
        CONF_WINDOW_SENSOR_ENTITY: None,
    }


async def test_initial_config_flow_with_blind_spot(hass: HomeAssistant, return_fake_cover_data) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={"name": "foo"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "window"
    assert result["errors"] is None

    # invalid elevation
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_WINDOW_AZIMUTH: 123,
            CONF_WINDOW_HEIGHT: 1.23,
            CONF_DISTANCE_FROM_WINDOW: 0.123,
            CONF_FOV_LEFT: 30,
            CONF_FOV_RIGHT: 90,
            CONF_BLIND_SPOT_ENABLED: True,
            CONF_MIN_SOLAR_ELEVATION: 40,
            CONF_MAX_SOLAR_ELEVATION: 30,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "window"
    assert result["errors"] == {CONF_MAX_SOLAR_ELEVATION: "max_solar_elevation_less_than_min"}

    # valid elevation
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_WINDOW_AZIMUTH: 123,
            CONF_WINDOW_HEIGHT: 1.23,
            CONF_DISTANCE_FROM_WINDOW: 0.123,
            CONF_FOV_LEFT: 30,
            CONF_FOV_RIGHT: 90,
            CONF_BLIND_SPOT_ENABLED: True,
            CONF_MIN_SOLAR_ELEVATION: 30,
            CONF_MAX_SOLAR_ELEVATION: 40,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "blind_spot"
    assert result["errors"] is None

    # invalid blind spot
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_BLIND_SPOT_LEFT: 12, CONF_BLIND_SPOT_RIGHT: 11},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "blind_spot"
    assert result["errors"] == {CONF_BLIND_SPOT_RIGHT: "blind_spot_right_less_than_left"}

    # valid blind spot
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_BLIND_SPOT_LEFT: 11, CONF_BLIND_SPOT_RIGHT: 12},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "cover_position"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_ENTITIES: ["cover.foo"],
            CONF_DEFAULT_COVER_POSITION: 30,
            CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION: 31,
            CONF_MAXIMUM_COVER_POSITION: 80,
            CONF_MINIMUM_COVER_POSITION: 20,
            CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: True,
            CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: True,
            CONF_INVERT: False,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sensor"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PRESENCE_ENTITY: "binary_sensor.presence",
            CONF_WINDOW_SENSOR_ENTITY: "binary_sensor.window",
            CONF_LUX_ENTITY: "sensor.lux",
            CONF_LUX_THRESHOLD: 10000,
            CONF_WEATHER_ENTITY: "weather.foo",
            CONF_WEATHER_STATE: ["cloudy", "fog"],
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "automation"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SUNSET_OFFSET: {"minutes": 12},
            CONF_SUNRISE_OFFSET: {"minutes": 23},
            CONF_START_TIME: "01:23:00",
            CONF_START_TIME_ENTITY: "input_datetime.start",
            CONF_END_TIME: "23:23:00",
            CONF_END_TIME_ENTITY: "input_datetime.end",
            CONF_MINIMUM_CHANGE_PERCENTAGE: 2,
            CONF_MINIMUM_CHANGE_TIME: {"hours": 23},
            CONF_RETURN_TO_DEFAULT_AT_END_TIME: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual_override"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MANUAL_OVERRIDE_DURATION: {"hours": 12},
            CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: True,
            CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD: 33,
            CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS: True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "foo Automated Cover Control"
    assert result["data"] == {"name": "foo"}
    assert result["options"] == {
        CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION: 31.0,
        CONF_BLIND_SPOT_ELEVATION: None,
        CONF_BLIND_SPOT_ENABLED: True,
        CONF_BLIND_SPOT_LEFT: 11.0,
        CONF_BLIND_SPOT_RIGHT: 12.0,
        CONF_DEFAULT_COVER_POSITION: 30.0,
        CONF_DISTANCE_FROM_WINDOW: 0.123,
        CONF_END_TIME: "23:23:00",
        CONF_END_TIME_ENTITY: "input_datetime.end",
        CONF_ENTITIES: ["cover.foo"],
        CONF_FOV_LEFT: 30.0,
        CONF_FOV_RIGHT: 90.0,
        CONF_INVERT: False,
        CONF_LUX_ENTITY: "sensor.lux",
        CONF_LUX_THRESHOLD: 10000.0,
        CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD: 33,
        CONF_MANUAL_OVERRIDE_DURATION: {"hours": 12},
        CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS: True,
        CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: True,
        CONF_MAXIMUM_COVER_POSITION: 80,
        CONF_MAX_SOLAR_ELEVATION: 40,
        CONF_MINIMUM_CHANGE_PERCENTAGE: 2.0,
        CONF_MINIMUM_CHANGE_TIME: {"hours": 23},
        CONF_MINIMUM_COVER_POSITION: 20,
        CONF_MIN_SOLAR_ELEVATION: 30,
        CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: True,
        CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: True,
        CONF_PRESENCE_ENTITY: "binary_sensor.presence",
        CONF_RETURN_TO_DEFAULT_AT_END_TIME: True,
        CONF_START_TIME: "01:23:00",
        CONF_START_TIME_ENTITY: "input_datetime.start",
        CONF_SUNRISE_OFFSET: {"minutes": 23},
        CONF_SUNSET_OFFSET: {"minutes": 12},
        CONF_WEATHER_ENTITY: "weather.foo",
        CONF_WEATHER_STATE: ["cloudy", "fog"],
        CONF_WINDOW_AZIMUTH: 123.0,
        CONF_WINDOW_HEIGHT: 1.23,
        CONF_WINDOW_SENSOR_ENTITY: "binary_sensor.window",
    }
