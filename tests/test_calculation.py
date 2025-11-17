import logging
from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.core import State

from custom_components.automated_cover_control.calculation import (
    SunPosition,
    calculate_sun_tracking_vertical_cover_position,
)
from custom_components.automated_cover_control.config import (
    AutomationConfiguration,
    BlindSpotConfiguration,
    SensorConfiguration,
    WindowConfiguration,
)
from custom_components.automated_cover_control.log_context_adapter import (
    LogContextAdapter,
)
from custom_components.automated_cover_control.why import (
    CoverControlReason,
    CoverControlTweaks,
)


class FakeHass:
    class FakeConfig:
        latitude = 37.80
        longitude = -122.46
        time_zone = "America/Los_Angeles"
        elevation = 0

    config = FakeConfig()
    states = {}
    data = {}


def default_window_and_sun_params_with_expected_cover_percentage() -> [
    WindowConfiguration,
    SunPosition,
    int,
]:
    window_config = WindowConfiguration()
    window_config.window_azimuth = 86
    window_config.window_height = 1.67
    window_config.distance_from_window = 0.3

    sun = SunPosition()
    sun.solar_azimuth = 142.5
    sun.solar_elevation = 29.28
    sun.sunrise = datetime.fromisoformat("2025-10-31T08:00:00-08:00")
    sun.sunset = datetime.fromisoformat("2025-10-31T19:00:00-08:00")
    sun.now = datetime.fromisoformat("2025-10-31T10:40:00-08:00")

    return window_config, sun, 18


def test_normal_calculation():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99

    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # before sunrise
    sun.now = sun.sunrise - timedelta(hours=1)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 99
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]

    # after sunset
    sun.now = sun.sunset + timedelta(hours=1)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 99
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]


def test_normal_calculation_with_sun_offsets():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99
    automation_config.sunrise_offset = timedelta(minutes=45)
    automation_config.sunset_offset = timedelta(minutes=30)

    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # before sunrise but within offset
    sun.now = sun.sunrise - timedelta(minutes=44)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # before sunrise and before offset
    sun.now = sun.sunrise - timedelta(minutes=46)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 99
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]

    # after sunset but within offset
    sun.now = sun.sunset + timedelta(minutes=29)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # after sunset and after offset
    sun.now = sun.sunset + timedelta(minutes=31)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 99
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]


def test_with_min_max_solar_elevation():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99

    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()
    window_config.min_solar_elevation = sun.solar_elevation + 1
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 11
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.SOLAR_ELEVATION_OUT_OF_RANGE]

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()
    window_config.max_solar_elevation = sun.solar_elevation - 1
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 11
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.SOLAR_ELEVATION_OUT_OF_RANGE]


def test_with_blind_spot():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99

    blind_spot_config = BlindSpotConfiguration()
    blind_spot_config.enabled = True
    blind_spot_config.left = 10
    blind_spot_config.right = 20
    blind_spot_config.elevation = None

    sensor_config = SensorConfiguration()

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()
    sun.solar_azimuth = 142.5  # Results in a gamma of 146.5 with a window azimuth of 86.
    sun.solar_elevation = 29.28

    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    blind_spot_config.left = 140
    blind_spot_config.right = 150
    blind_spot_config.elevation = None
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 11
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.SUN_IN_BLIND_SPOT]

    blind_spot_config.left = 140
    blind_spot_config.right = 150
    blind_spot_config.elevation = 20
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    blind_spot_config.left = 140
    blind_spot_config.right = 150
    blind_spot_config.elevation = 30
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 11
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.SUN_IN_BLIND_SPOT]


def test_with_fov():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99

    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()
    window_config.fov_left = 0
    window_config.fov_right = 57
    sun.solar_azimuth = (
        142.5  # Results in a gamma of 146.5 with a window azimuth of 86, so just shy of 57 degrees right.
    )
    sun.solar_elevation = 29.28

    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    window_config.fov_left = 0
    window_config.fov_right = 56
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 11
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []


def test_window_sensor():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 33
    automation_config.before_sunrise_or_after_sunset_cover_position = 66

    blind_spot_config = BlindSpotConfiguration()

    sensor_config = SensorConfiguration()
    sensor_config.window_sensor_entity = "binary_sensor.window"

    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["binary_sensor.window"] = State(entity_id="binary_sensor.window", state=None)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["binary_sensor.window"] = State(entity_id="binary_sensor.window", state="invalid")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["binary_sensor.window"] = State(entity_id="binary_sensor.window", state="on")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.WINDOW_OPEN
    assert cp.tweaks == []

    sun.now = sun.sunrise - timedelta(hours=1)  # before sunrise
    hass.states["binary_sensor.window"] = State(entity_id="binary_sensor.window", state="on")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 66
    assert cp.reason == CoverControlReason.WINDOW_OPEN
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]

    sun.now = sun.sunset + timedelta(hours=1)  # after sunset
    hass.states["binary_sensor.window"] = State(entity_id="binary_sensor.window", state="on")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 66
    assert cp.reason == CoverControlReason.WINDOW_OPEN
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]


def test_presence():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 33
    automation_config.before_sunrise_or_after_sunset_cover_position = 66

    blind_spot_config = BlindSpotConfiguration()
    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "device_tracker.x"
    hass.states["device_tracker.x"] = State(entity_id="device_tracker.x", state=None)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.PRESENCE_NOT_DETECTED
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "device_tracker.x"
    hass.states["device_tracker.x"] = State(entity_id="device_tracker.x", state="foo")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.PRESENCE_NOT_DETECTED
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "device_tracker.x"
    hass.states["device_tracker.x"] = State(entity_id="device_tracker.x", state="home")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "zone.y"
    hass.states["zone.y"] = State(entity_id="zone.y", state=0)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.PRESENCE_NOT_DETECTED
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "zone.y"
    hass.states["zone.y"] = State(entity_id="zone.y", state=5)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "binary_sensor.y"
    hass.states["binary_sensor.y"] = State(entity_id="binary_sensor.y", state="off")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.PRESENCE_NOT_DETECTED
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "binary_sensor.y"
    hass.states["binary_sensor.y"] = State(entity_id="binary_sensor.y", state="on")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # Invalid domain falls back to presence-detected.
    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    sensor_config = SensorConfiguration()
    sensor_config.presence_entity = "bad_domain.foo"
    hass.states["bad_domain.foo"] = State(entity_id="bad_domain.foo", state="bar")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []


def test_weather():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 33
    automation_config.before_sunrise_or_after_sunset_cover_position = 66

    sensor_config = SensorConfiguration()
    sensor_config.weather_entity = "weather.z"
    sensor_config.weather_condition = ["sunny"]

    blind_spot_config = BlindSpotConfiguration()
    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["weather.z"] = State(entity_id="weather.z", state=None)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.WEATHER_CONDITIONS_NOT_MATCHED
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["weather.z"] = State(entity_id="weather.z", state="cloudy")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.WEATHER_CONDITIONS_NOT_MATCHED
    assert cp.tweaks == []

    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["weather.z"] = State(entity_id="weather.z", state="sunny")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # Defaults to sunny if no weather conditions defined.
    sensor_config.weather_condition = None
    sun.now = sun.sunrise + timedelta(hours=5)  # halfway between sunrise and sunset
    hass.states["weather.z"] = State(entity_id="weather.z", state="foo")
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []


def test_lux():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 33
    automation_config.before_sunrise_or_after_sunset_cover_position = 66

    sensor_config = SensorConfiguration()
    sensor_config.lux_entity = "lux.a"
    sensor_config.lux_threshold = 5000

    blind_spot_config = BlindSpotConfiguration()
    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()

    hass.states["lux.a"] = State(entity_id="lux.a", state=None)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    hass.states["lux.a"] = State(entity_id="lux.a", state=0)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 33
    assert cp.reason == CoverControlReason.LUX_BELOW_THRESHOLD
    assert cp.tweaks == []

    hass.states["lux.a"] = State(entity_id="lux.a", state=5001)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    # Defaults to above threshold if no threshold defined.
    sensor_config.lux_threshold = None
    hass.states["lux.a"] = State(entity_id="lux.a", state=0)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []


def test_min_position():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99

    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()
    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99
    automation_config.minimum_cover_position = 22
    automation_config.only_force_minimum_when_sun_in_front_of_window = False
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 22
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.CLIPPED_TO_MIN]

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 12
    automation_config.minimum_cover_position = 22
    automation_config.only_force_minimum_when_sun_in_front_of_window = True
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 22
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.CLIPPED_TO_MIN]

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 12
    automation_config.minimum_cover_position = 22
    automation_config.only_force_minimum_when_sun_in_front_of_window = False
    sun.now = sun.sunrise - timedelta(hours=1)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 22
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [
        CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE,
        CoverControlTweaks.CLIPPED_TO_MIN,
    ]

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 12
    automation_config.minimum_cover_position = 22
    automation_config.only_force_minimum_when_sun_in_front_of_window = True
    sun.now = sun.sunrise - timedelta(hours=1)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 12
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]


def test_max_position():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99

    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()
    window_config, sun, expected_position = default_window_and_sun_params_with_expected_cover_percentage()

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 11
    automation_config.before_sunrise_or_after_sunset_cover_position = 99
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == expected_position
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == []

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 88
    automation_config.before_sunrise_or_after_sunset_cover_position = 88
    automation_config.maximum_cover_position = 10
    automation_config.only_force_maximum_when_sun_in_front_of_window = False
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 10
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.CLIPPED_TO_MAX]

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 88
    automation_config.before_sunrise_or_after_sunset_cover_position = 88
    automation_config.maximum_cover_position = 10
    automation_config.only_force_maximum_when_sun_in_front_of_window = True
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 10
    assert cp.reason == CoverControlReason.SUN_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.CLIPPED_TO_MAX]

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 88
    automation_config.before_sunrise_or_after_sunset_cover_position = 88
    automation_config.maximum_cover_position = 10
    automation_config.only_force_maximum_when_sun_in_front_of_window = False
    sun.now = sun.sunrise - timedelta(hours=1)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 10
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [
        CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE,
        CoverControlTweaks.CLIPPED_TO_MAX,
    ]

    automation_config = AutomationConfiguration()
    automation_config.default_cover_position = 88
    automation_config.before_sunrise_or_after_sunset_cover_position = 88
    automation_config.maximum_cover_position = 10
    automation_config.only_force_maximum_when_sun_in_front_of_window = True
    sun.now = sun.sunrise - timedelta(hours=1)
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 88
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE]


def test_clipping():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    sun = SunPosition()
    sun.sunrise = datetime.now(tz=UTC)
    sun.sunset = sun.sunrise + timedelta(hours=10)
    sun.now = sun.sunrise - timedelta(hours=1)

    automation_config = AutomationConfiguration()
    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()
    window_config = WindowConfiguration()

    automation_config.before_sunrise_or_after_sunset_cover_position = -155
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 0
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [
        CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE,
        CoverControlTweaks.CLIPPED_TO_0_100_RANGE,
    ]

    automation_config.before_sunrise_or_after_sunset_cover_position = 155
    cp = calculate_sun_tracking_vertical_cover_position(
        hass,
        logger,
        sun,
        automation_config,
        blind_spot_config,
        sensor_config,
        window_config,
    )
    assert cp.target_position == 100
    assert cp.reason == CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW
    assert cp.tweaks == [
        CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE,
        CoverControlTweaks.CLIPPED_TO_0_100_RANGE,
    ]


def test_invalid_sun_position():
    hass = FakeHass()
    logger = LogContextAdapter(logging.getLogger(__name__))

    automation_config = AutomationConfiguration()
    blind_spot_config = BlindSpotConfiguration()
    sensor_config = SensorConfiguration()
    window_config = WindowConfiguration()

    with pytest.raises(Exception) as ex:
        sun = SunPosition()
        sun.sunrise = datetime.now(tz=UTC)
        sun.sunset = sun.sunrise + timedelta(hours=10)
        sun.now = sun.sunrise - timedelta(hours=1)

        sun.now = sun.now.replace(tzinfo=None)

        calculate_sun_tracking_vertical_cover_position(
            hass,
            logger,
            sun,
            automation_config,
            blind_spot_config,
            sensor_config,
            window_config,
        )
    assert "now" in str(ex.value)

    with pytest.raises(Exception) as ex:
        sun = SunPosition()
        sun.sunrise = datetime.now(tz=UTC)
        sun.sunset = sun.sunrise + timedelta(hours=10)
        sun.now = sun.sunrise - timedelta(hours=1)

        sun.sunrise = sun.sunrise.replace(tzinfo=None)

        calculate_sun_tracking_vertical_cover_position(
            hass,
            logger,
            sun,
            automation_config,
            blind_spot_config,
            sensor_config,
            window_config,
        )
    assert "sunrise" in str(ex.value)

    with pytest.raises(Exception) as ex:
        sun = SunPosition()
        sun.sunrise = datetime.now(tz=UTC)
        sun.sunset = sun.sunrise + timedelta(hours=10)
        sun.now = sun.sunrise - timedelta(hours=1)

        sun.sunset = sun.sunset.replace(tzinfo=None)

        calculate_sun_tracking_vertical_cover_position(
            hass,
            logger,
            sun,
            automation_config,
            blind_spot_config,
            sensor_config,
            window_config,
        )
    assert "sunset" in str(ex.value)
