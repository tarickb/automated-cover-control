from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time, timedelta
from types import MappingProxyType
from typing import Any

from .const import (
    CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_ENABLED,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
    CONF_CALC_ROUNDING,
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
)


def _config_option_or_default(config: MappingProxyType[str, Any], key: str, default: Any) -> Any:
    value = config.get(key, None)
    if value is None:
        return default
    return value


@dataclass
class ManualOverrideConfiguration:
    reset_timer_at_each_adjustment: bool = False
    override_duration: timedelta = None
    ignore_intermediate_positions: bool = True
    detection_threshold: int = None

    def read(self, config: MappingProxyType[str, Any]) -> None:
        self.reset_timer_at_each_adjustment = config.get(CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT, False)
        self.override_duration = timedelta(
            **_config_option_or_default(config, CONF_MANUAL_OVERRIDE_DURATION, {"minutes": 15})
        )
        self.ignore_intermediate_positions = config.get(CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS, True)
        self.detection_threshold = _config_option_or_default(config, CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD, 2)
        if self.detection_threshold < 2:
            self.detection_threshold = 2


@dataclass
class AutomationConfiguration:
    entities: list[str] = field(default_factory=list)

    default_cover_position: int = 0
    before_sunrise_or_after_sunset_cover_position: int = 0

    invert: bool = False
    return_to_default_at_end_time: bool = False

    minimum_change_percentage: int = 1
    minimum_change_time: timedelta = timedelta(minutes=2)

    start_time: time | None = None
    start_time_entity: str = None
    end_time: time | None = None
    end_time_entity: str = None

    sunrise_offset: timedelta = None
    sunset_offset: timedelta = None

    minimum_cover_position: int = None
    maximum_cover_position: int = None
    only_force_minimum_when_sun_in_front_of_window: bool = False
    only_force_maximum_when_sun_in_front_of_window: bool = False

    cover_calculation_rounding: int = 0

    def read(self, config: MappingProxyType[str, Any]) -> None:
        self.entities = config.get(CONF_ENTITIES, [])

        self.default_cover_position = config.get(CONF_DEFAULT_COVER_POSITION, 0)
        self.before_sunrise_or_after_sunset_cover_position = config.get(
            CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION, 0
        )

        self.invert = config.get(CONF_INVERT, False)
        self.return_to_default_at_end_time = config.get(CONF_RETURN_TO_DEFAULT_AT_END_TIME, False)

        self.minimum_change_percentage = config.get(CONF_MINIMUM_CHANGE_PERCENTAGE, 1)
        self.minimum_change_time = timedelta(**config.get(CONF_MINIMUM_CHANGE_TIME, {"minutes": 2}))

        self.start_time = config.get(CONF_START_TIME)
        self.start_time_entity = config.get(CONF_START_TIME_ENTITY)
        self.end_time = config.get(CONF_END_TIME)
        self.end_time_entity = config.get(CONF_END_TIME_ENTITY)

        self.sunrise_offset = timedelta(**_config_option_or_default(config, CONF_SUNRISE_OFFSET, {}))
        self.sunset_offset = timedelta(**_config_option_or_default(config, CONF_SUNSET_OFFSET, {}))

        self.minimum_cover_position = config.get(CONF_MINIMUM_COVER_POSITION)
        self.maximum_cover_position = config.get(CONF_MAXIMUM_COVER_POSITION)
        self.only_force_minimum_when_sun_in_front_of_window = config.get(
            CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW, False
        )
        self.only_force_maximum_when_sun_in_front_of_window = config.get(
            CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW, False
        )

        self.cover_calculation_rounding = config.get(CONF_CALC_ROUNDING, 0)


@dataclass
class BlindSpotConfiguration:
    enabled: bool = False
    # Left, right specified as angles between 0 and 180, anchored on the plane of the window.
    left: int = None
    right: int = None
    elevation: int = None

    def read(self, config: MappingProxyType[str, Any]) -> None:
        self.enabled = config.get(CONF_BLIND_SPOT_ENABLED, False)
        self.left = config.get(CONF_BLIND_SPOT_LEFT)
        self.right = config.get(CONF_BLIND_SPOT_RIGHT)
        self.elevation = config.get(CONF_BLIND_SPOT_ELEVATION)


@dataclass
class SensorConfiguration:
    presence_entity: str = None
    window_sensor_entity: str = None
    weather_entity: str = None
    weather_condition: list[str] = field(default_factory=list)
    lux_entity: str = None
    lux_threshold: int = None

    def read(self, config: MappingProxyType[str, Any]) -> None:
        self.presence_entity = config.get(CONF_PRESENCE_ENTITY)
        self.window_sensor_entity = config.get(CONF_WINDOW_SENSOR_ENTITY)
        self.weather_entity = config.get(CONF_WEATHER_ENTITY)
        self.weather_condition = config.get(CONF_WEATHER_STATE)
        self.lux_entity = config.get(CONF_LUX_ENTITY)
        self.lux_threshold = config.get(CONF_LUX_THRESHOLD)


@dataclass
class WindowConfiguration:
    window_azimuth: int = 0
    window_height: float = 0.0
    distance_from_window: float = 0.0
    fov_left: int = 90
    fov_right: int = 90
    min_solar_elevation: int = None
    max_solar_elevation: int = None

    def read(self, config: MappingProxyType[str, Any]) -> None:
        self.window_azimuth = config.get(CONF_WINDOW_AZIMUTH, 0)
        self.window_height = config.get(CONF_WINDOW_HEIGHT, 0.0)
        self.distance_from_window = config.get(CONF_DISTANCE_FROM_WINDOW, 0.0)
        self.fov_left = config.get(CONF_FOV_LEFT, 90)
        self.fov_right = config.get(CONF_FOV_RIGHT, 90)
        self.min_solar_elevation = config.get(CONF_MIN_SOLAR_ELEVATION, None)
        self.max_solar_elevation = config.get(CONF_MAX_SOLAR_ELEVATION, None)
