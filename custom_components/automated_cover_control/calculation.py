from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant, split_entity_id
from numpy import clip, cos, radians, tan

from .config import (
    AutomationConfiguration,
    BlindSpotConfiguration,
    SensorConfiguration,
    WindowConfiguration,
)
from .log_context_adapter import LogContextAdapter
from .util import get_state_or_none_if_unknown
from .why import CoverControlReason, CoverControlTweaks


@dataclass
class SunPosition:
    solar_azimuth: float = 0.0
    solar_elevation: float = 0.0
    sunrise: datetime = None
    sunset: datetime = None
    now: datetime = None  # for testing, uses now if None


@dataclass
class SunTrackingVerticalCoverPosition:
    is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk: bool = False
    target_position: float = 0.0
    reason: CoverControlReason = CoverControlReason.UNKNOWN
    tweaks: list[CoverControlTweaks] = field(default_factory=list)


def calculate_sun_tracking_vertical_cover_position(
    hass: HomeAssistant,
    logger: LogContextAdapter,
    sun_position: SunPosition,
    automation_config: AutomationConfiguration,
    blind_spot_config: BlindSpotConfiguration,
    sensor_config: SensorConfiguration,
    window_config: WindowConfiguration,
) -> SunTrackingVerticalCoverPosition:
    def _gamma() -> float:
        return (window_config.window_azimuth - sun_position.solar_azimuth + 180) % 360 - 180

    def _is_sun_in_blind_spot() -> bool:
        if blind_spot_config.enabled and blind_spot_config.left is not None and blind_spot_config.right is not None:
            gamma = _gamma()
            gamma = 90 - gamma if gamma < 0 else gamma
            in_blind_spot = gamma >= blind_spot_config.left and gamma <= blind_spot_config.right
            if blind_spot_config.elevation is not None:
                in_blind_spot = in_blind_spot and sun_position.solar_elevation <= blind_spot_config.elevation
            logger.debug(
                "[_is_sun_in_blind_spot] bs_left=%s, bs_right=%s, bs_elev=%s, gamma=%s, _gamma=%s, elev=%s == %s",
                blind_spot_config.left,
                blind_spot_config.right,
                blind_spot_config.elevation,
                gamma,
                _gamma(),
                sun_position.solar_elevation,
                in_blind_spot,
            )
            return in_blind_spot
        return False

    def _is_solar_elevation_within_range() -> bool:
        within_range = False
        if window_config.min_solar_elevation is None and window_config.max_solar_elevation is None:
            within_range = sun_position.solar_elevation >= 0
        elif window_config.min_solar_elevation is None:
            within_range = sun_position.solar_elevation <= window_config.max_solar_elevation
        elif window_config.max_solar_elevation is None:
            within_range = sun_position.solar_elevation >= window_config.min_solar_elevation
        else:
            within_range = (
                window_config.min_solar_elevation <= sun_position.solar_elevation <= window_config.max_solar_elevation
            )
        logger.debug(
            "[_is_solar_elevation_within_range] %s -> %s",
            sun_position.solar_elevation,
            within_range,
        )
        return within_range

    def _is_sun_in_front_of_window() -> bool:
        azi_min = min(window_config.fov_left, 90)
        azi_max = min(window_config.fov_right, 90)

        in_front_of_window = _gamma() < azi_min and _gamma() > -azi_max and _is_solar_elevation_within_range()
        logger.debug("[_is_sun_in_front_of_window] %s", in_front_of_window)
        return in_front_of_window

    def _is_after_sunset_or_before_sunrise() -> bool:
        sunset_offset = automation_config.sunset_offset
        if sunset_offset is None:
            sunset_offset = timedelta(seconds=0)
        sunrise_offset = automation_config.sunrise_offset
        if sunrise_offset is None:
            sunrise_offset = timedelta(seconds=0)

        after_sunset = sun_position.now > (sun_position.sunset + sunset_offset)
        before_sunrise = sun_position.now < (sun_position.sunrise - sunrise_offset)
        logger.debug("[_is_after_sunset_or_before_sunrise] %s", (after_sunset or before_sunrise))
        return after_sunset or before_sunrise

    def _default_position() -> float:
        default = automation_config.default_cover_position
        if _is_after_sunset_or_before_sunrise():
            default = automation_config.before_sunrise_or_after_sunset_cover_position
        return default

    def _should_apply_min_position() -> bool:
        if automation_config.minimum_cover_position is not None and automation_config.minimum_cover_position != 0:
            if automation_config.only_force_minimum_when_sun_in_front_of_window:
                return _is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk()
            return True
        return False

    def _should_apply_max_position() -> bool:
        if automation_config.maximum_cover_position is not None and automation_config.maximum_cover_position != 100:
            if automation_config.only_force_maximum_when_sun_in_front_of_window:
                return _is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk()
            return True
        return False

    def _is_window_open():
        if sensor_config.window_sensor_entity is None:
            logger.debug("[_is_window_open] No window sensor entity defined")
            return False
        is_open = get_state_or_none_if_unknown(hass, sensor_config.window_sensor_entity)
        if is_open is None:
            logger.debug("[_is_window_open] No open state")
            return False
        logger.debug(
            "[_is_window_open] State for %s is %s",
            sensor_config.window_sensor_entity,
            is_open,
        )
        return is_open == "on"

    def _is_presence_detected():
        if sensor_config.presence_entity is None:
            logger.debug("[_is_presence_detected] No presence entity defined")
            return True
        presence = get_state_or_none_if_unknown(hass, sensor_config.presence_entity)
        if presence is None:
            logger.debug("[_is_presence_detected] No presence state")
            return True
        domain, _ = split_entity_id(sensor_config.presence_entity)
        if domain == "device_tracker":
            return presence == "home"
        if domain == "zone":
            return int(presence) > 0
        if domain in ["binary_sensor", "input_boolean"]:
            return presence == "on"
        logger.debug("[_is_presence_detected] Don't know what to do with domain %s", domain)
        return True

    def _is_sunny() -> bool:
        if sensor_config.weather_entity is None:
            logger.debug("[_is_sunny] No weather entity defined")
            return True
        if sensor_config.weather_condition is None:
            logger.debug("[_is_sunny] No weather conditions defined")
            return True
        weather_state = get_state_or_none_if_unknown(hass, sensor_config.weather_entity)
        matches = weather_state in sensor_config.weather_condition
        logger.debug("[_is_sunny] Weather: %s = %s", weather_state, matches)
        return matches

    def _is_lux_above_threshold() -> bool:
        if sensor_config.lux_entity is None:
            logger.debug("[_is_lux_above_threshold] No lux entity defined")
            return True
        if sensor_config.lux_threshold is None:
            logger.debug("[_is_lux_above_threshold] No lux threshold defined")
            return True
        lux = get_state_or_none_if_unknown(hass, sensor_config.lux_entity)
        if lux is None:
            logger.debug(
                "[_is_lux_above_threshold] value for %s is None",
                sensor_config.lux_entity,
            )
            return True
        try:
            lux = float(lux)
        except Exception as e:
            logger.debug(
                "[_is_lux_above_threshold] value for %s is not a float (%s): %s",
                sensor_config.lux_entity,
                lux,
                e,
            )
            return True
        return float(lux) > sensor_config.lux_threshold

    def _calculate_percentage() -> float:
        blind_height = clip(
            (window_config.distance_from_window / cos(radians(_gamma()))) * tan(radians(sun_position.solar_elevation)),
            0,
            window_config.window_height,
        )
        percentage = round(
            blind_height / window_config.window_height * 100,
            automation_config.cover_calculation_rounding,
        )
        logger.debug(
            "[_calculate_percentage] %s / %s * 100 = %s",
            blind_height,
            window_config.window_height,
            percentage,
        )
        return percentage

    def _get_target_position_unclipped() -> (int, CoverControlReason):
        if _is_window_open():
            logger.debug("[_get_target_position_unclipped] Window open, using default")
            return _default_position(), CoverControlReason.WINDOW_OPEN

        if not _is_presence_detected():
            logger.debug("[_get_target_position_unclipped] No one present, using default")
            # TODO(tarick): configuration option: no presence = full light, no presence = no light, no presence = default
            return _default_position(), CoverControlReason.PRESENCE_NOT_DETECTED

        if not _is_lux_above_threshold():
            logger.debug("[_get_target_position_unclipped] Lux below threshold, using default")
            return _default_position(), CoverControlReason.LUX_BELOW_THRESHOLD

        if not _is_sunny():
            logger.debug("[_get_target_position_unclipped] Not sunny, using default")
            return (
                _default_position(),
                CoverControlReason.WEATHER_CONDITIONS_NOT_MATCHED,
            )

        in_front_of_window = _is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk()
        logger.debug(
            "[_get_target_position_unclipped] Sun directly in front of window & before sunset + offset? %s",
            in_front_of_window,
        )
        if in_front_of_window:
            target = _calculate_percentage()
            logger.debug(
                "[_get_target_position_unclipped] Yes sun in window: using calculated percentage (%s)",
                target,
            )
            return target, CoverControlReason.SUN_IN_FRONT_OF_WINDOW

        logger.debug("[_get_target_position_unclipped] No sun in window: using default value")
        return _default_position(), CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW

    def _is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk() -> bool:
        return (
            (_is_sun_in_front_of_window()) & (not _is_after_sunset_or_before_sunrise()) & (not _is_sun_in_blind_spot())
        )

    if sun_position.now is None:
        sun_position.now = datetime.now(tz=UTC)

    if sun_position.now.tzinfo is None:
        raise Exception(f"now ({sun_position.now}) lacks timezone")
    if sun_position.sunrise.tzinfo is None:
        raise Exception(f"sunrise ({sun_position.sunrise}) lacks timezone")
    if sun_position.sunset.tzinfo is None:
        raise Exception(f"sunset ({sun_position.sunset}) lacks timezone")

    result, reason = _get_target_position_unclipped()
    result = round(result)
    tweaks = []
    logger.debug("[get_target_position] unclipped result: %s", result)

    if _is_sun_in_blind_spot():
        tweaks.append(CoverControlTweaks.SUN_IN_BLIND_SPOT)
    if not _is_solar_elevation_within_range():
        tweaks.append(CoverControlTweaks.SOLAR_ELEVATION_OUT_OF_RANGE)
    if _is_after_sunset_or_before_sunrise():
        tweaks.append(CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE)

    if _should_apply_max_position() and result > automation_config.maximum_cover_position:
        logger.debug(
            "[get_target_position] state above max, clipping to %s",
            automation_config.maximum_cover_position,
        )
        result = round(automation_config.maximum_cover_position)
        tweaks.append(CoverControlTweaks.CLIPPED_TO_MAX)
    if _should_apply_min_position() and result < automation_config.minimum_cover_position:
        logger.debug(
            "[get_target_position] state below min, clipping to %s",
            automation_config.minimum_cover_position,
        )
        result = round(automation_config.minimum_cover_position)
        tweaks.append(CoverControlTweaks.CLIPPED_TO_MIN)

    if clip(result, 0, 100) != result:
        result = clip(result, 0, 100)
        tweaks.append(CoverControlTweaks.CLIPPED_TO_0_100_RANGE)

    return SunTrackingVerticalCoverPosition(
        is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk=_is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk(),
        target_position=result,
        reason=reason,
        tweaks=tweaks,
    )
