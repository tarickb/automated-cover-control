from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from dateutil import parser, tz
from homeassistant.components.cover import ATTR_POSITION
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_SET_COVER_POSITION,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
)
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.sun import get_astral_location
from homeassistant.helpers.template import state_attr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import get_time_zone

from .calculation import (
    SunPosition,
    SunTrackingVerticalCoverPosition,
    calculate_sun_tracking_vertical_cover_position,
)
from .config import (
    AutomationConfiguration,
    BlindSpotConfiguration,
    SensorConfiguration,
    WindowConfiguration,
)
from .const import DOMAIN
from .log_context_adapter import LogContextAdapter
from .manual_override_manager import ManualOverrideManager
from .sun import SolarTimeCalculator
from .util import get_state_or_none_if_unknown, midnight_to_end_of_day, to_json_safe_dict
from .why import CoverControlReason, CoverControlTweaks


@dataclass
class CoverStateChangeData:
    entity_id: str
    new_state: State | None


@dataclass
class AutomatedCoverControlData:
    states: dict
    attributes: dict


class AutomatedCoverControlDataUpdateCoordinator(DataUpdateCoordinator[AutomatedCoverControlData]):
    @dataclass
    class _AsyncRefreshRequest:
        cover_state_change: bool = False
        end_time: bool = False

        def reset(self) -> None:
            self.cover_state_change = False
            self.end_time = False

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, logging.getLogger(__package__), name=DOMAIN)

        # TODO(tarick): types
        self._logger = LogContextAdapter(logging.getLogger(__name__))
        self._logger.set_config_name(self.config_entry.data.get("name"))

        self._automation_config = AutomationConfiguration()
        self._blind_spot_config = BlindSpotConfiguration()
        self._sensor_config = SensorConfiguration()
        self._window_config = WindowConfiguration()

        self._async_refresh_requests = AutomatedCoverControlDataUpdateCoordinator._AsyncRefreshRequest()

        self._cover_entities_in_motion = {}
        self._cover_state_change_data: CoverStateChangeData | None = None

        self._end_time_event_listener = None
        self._end_time_last_scheduled = datetime.now(tz=UTC)

        self._astral_location, _ = get_astral_location(self.hass)

        self._enable_automation = None
        self._manual_overrides = ManualOverrideManager(self._logger)

        self._sun_end_time = None
        self._sun_start_time = None
        self._next_sun_time_recompute = None

        self._update_config()

    def _update_config(self) -> None:
        self._automation_config.read(self.config_entry.options)
        self._blind_spot_config.read(self.config_entry.options)
        self._sensor_config.read(self.config_entry.options)
        self._window_config.read(self.config_entry.options)

        self._manual_overrides.update_config(self.config_entry.options)

    def _combine_local_time_with_date(self, date, time) -> datetime:
        local_time_zone = get_time_zone(self.hass.config.time_zone)
        return datetime.combine(date.astimezone(local_time_zone), time, local_time_zone)

    def _get_start_time(self) -> datetime | None:
        start_time = None
        if self._automation_config.start_time_entity is not None:
            start_time = get_state_or_none_if_unknown(self.hass, self._automation_config.start_time_entity)
        else:
            start_time = self._automation_config.start_time
        if start_time is None:
            return None
        start_time = parser.parse(start_time, ignoretz=True).time()
        return self._combine_local_time_with_date(datetime.now(tz.UTC), start_time)

    def _get_end_time(self) -> datetime | None:
        end_time = None
        if self._automation_config.end_time_entity is not None:
            end_time = get_state_or_none_if_unknown(self.hass, self._automation_config.end_time_entity)
        else:
            end_time = self._automation_config.end_time
        if end_time is None:
            return None
        end_time = parser.parse(end_time, ignoretz=True).time()
        end_time = midnight_to_end_of_day(end_time)
        return self._combine_local_time_with_date(datetime.now(tz.UTC), end_time)

    def _register_end_time_trigger(self) -> None:
        end_time = self._get_end_time()
        if self._end_time_event_listener:
            self._end_time_event_listener()
            self._end_time_event_listener = None
        self._logger.debug(
            "[_register_end_time_trigger] end time: %s, return to default: %s, scheduled time: %s",
            end_time,
            self._automation_config.return_to_default_at_end_time,
            self._end_time_last_scheduled,
        )
        self._end_time_event_listener = async_track_point_in_utc_time(self.hass, self._async_end_time_trigger, end_time)
        self._end_time_last_scheduled = end_time

    async def _async_end_time_trigger(self, event) -> None:
        now = datetime.now(tz=UTC)
        end_time = self._get_end_time()
        delta = now - end_time
        self._logger.debug(
            "[_async_end_time_trigger] End time: %s, now: %s, delta: %s",
            end_time,
            now,
            delta,
        )
        # One minute because the unit tests tick the clock at minute granularity...
        if end_time is not None and (delta <= timedelta(minutes=1)):
            self._async_refresh_requests.end_time = True
            self._logger.debug("[_async_end_time_trigger] End-time refresh triggered")
            await self.async_refresh()
        else:
            self._logger.debug(
                "[_async_end_time_trigger] End-time refresh, but not equal to end time"
            )  # pragma: no cover

    def _generate_data(self, state_updates: dict = {}) -> AutomatedCoverControlData:
        data = AutomatedCoverControlData(
            states=dict(
                {
                    "sun_in_window_start": self._sun_start_time,
                    "sun_in_window_end": self._sun_end_time,
                    "manual_override": self._manual_overrides.is_any_cover_under_manual_control(),
                    "covers_under_manual_control": self._manual_overrides.covers_under_manual_control(),
                },
                **state_updates,
            ),
            attributes={
                "automation": to_json_safe_dict(self._automation_config),
                "blind_spot": to_json_safe_dict(self._blind_spot_config),
                "sensor": to_json_safe_dict(self._sensor_config),
                "window": to_json_safe_dict(self._window_config),
                "manual_override": to_json_safe_dict(self._manual_overrides.get_config()),
            },
        )
        self._logger.debug("[_generate_data] data: %s", data)
        return data

    async def _async_update_data(self) -> AutomatedCoverControlData:
        now = datetime.now(tz=UTC)
        self._logger.debug(
            "[_async_update_data] called at %s (%s local), updating config",
            now.isoformat(),
            now.astimezone(get_time_zone(self.hass.config.time_zone)).isoformat(),
        )
        self._update_config()

        # Generate sun start, end times (purely informational).
        if self._sun_start_time is None or self._next_sun_time_recompute is None or now > self._next_sun_time_recompute:
            self._logger.debug("[_async_update_data] Recalculating solar times")
            solar_calc = SolarTimeCalculator(self.hass, self._window_config)
            loop = asyncio.get_event_loop()
            self._sun_start_time, self._sun_end_time = await loop.run_in_executor(
                None, solar_calc.get_solar_start_and_end_times
            )
            # Set next-recompute time to just past midnight on the next day.
            self._next_sun_time_recompute = self._combine_local_time_with_date(
                self._sun_start_time + timedelta(days=1), time.min
            )
            self._logger.debug(
                "[_async_update_data] Sun start time: %s, end time: %s, recompute at: %s",
                self._sun_start_time,
                self._sun_end_time,
                self._next_sun_time_recompute,
            )

        # Bail early; automation is disabled.
        if not self._enable_automation:
            self._logger.debug("[_async_update_data] automation disabled; exiting")
            return self._generate_data({"reason": CoverControlReason.AUTOMATION_DISABLED})

        calculated_target: SunTrackingVerticalCoverPosition = None
        force_set_position: bool = False

        # Handle async event-triggered refresh requests first.
        if self._async_refresh_requests.cover_state_change:
            self._logger.debug("[_async_update_data] async refresh request: cover state change")
            if self._cover_state_change_data is not None:
                if "target_position" in self.data.states:
                    self._manual_overrides.handle_state_change(
                        self._cover_state_change_data.entity_id,
                        self._cover_state_change_data.new_state,
                        self.data.states["target_position"],
                    )
                else:
                    self._logger.warning(
                        "[_async_update_data] cover state change but no previous data?"
                    )  # pragma: no cover
            else:
                self._logger.warning("[_async_update_data] cover state change but no event data?")  # pragma: no cover
        if self._async_refresh_requests.end_time:
            calculated_target = SunTrackingVerticalCoverPosition()
            calculated_target.target_position = self._automation_config.before_sunrise_or_after_sunset_cover_position
            calculated_target.reason = CoverControlReason.END_TIME_REACHED
            force_set_position = True
            self._logger.debug(
                "[_async_update_data] async refresh request: end time, setting target to %s",
                calculated_target.target_position,
            )
        # Reset tracking for async refresh requests.
        self._async_refresh_requests.reset()

        # Reset manual overrides if they've expired.
        self._manual_overrides.reset_expired_overrides()

        # Schedule end-time trigger.
        if (
            self._get_end_time()
            and self._automation_config.return_to_default_at_end_time
            and self._get_end_time() > self._end_time_last_scheduled
        ):
            self._register_end_time_trigger()

        # Bail early if we're outside the control time range.
        if not force_set_position and not self._is_within_control_time_range():
            self._logger.debug("[_async_update_data] outside control time range")
            # This hack allows us to continue returning END_TIME_REACHED for the rest of the day, to simplify debugging.
            if (
                self.data.states.get("reason", CoverControlReason.UNKNOWN) == CoverControlReason.END_TIME_REACHED
                and self.data.states.get("sun_in_window_start", datetime.min) == self._sun_start_time
            ):
                return self.data
            return self._generate_data({"reason": CoverControlReason.OUTSIDE_CONTROL_TIME_RANGE})

        if not calculated_target:
            # Get sun position and calculate cover target.
            sun_pos = SunPosition(
                solar_azimuth=state_attr(self.hass, "sun.sun", "azimuth"),
                solar_elevation=state_attr(self.hass, "sun.sun", "elevation"),
                sunrise=self._astral_location.sunrise(date.today(), local=False),
                sunset=self._astral_location.sunset(date.today(), local=False),
            )
            self._logger.debug("[_async_update_data] sun position: %s", sun_pos)

            calculated_target = calculate_sun_tracking_vertical_cover_position(
                self.hass,
                self._logger,
                sun_pos,
                self._automation_config,
                self._blind_spot_config,
                self._sensor_config,
                self._window_config,
            )
            self._logger.debug("[_async_update_data] calculated target: %s", calculated_target)

        # Invert the target if necessary.
        if self._automation_config.invert:
            calculated_target.target_position = 100 - calculated_target.target_position
            calculated_target.tweaks.append(CoverControlTweaks.INVERTED)
            self._logger.debug(
                "[_async_set_cover_position] inverted position to %s",
                calculated_target.target_position,
            )

        # Set cover positions and record reason.
        per_cover_control_reasons = {}
        for cover in self._automation_config.entities:
            if self._manual_overrides.is_cover_manual(cover):
                self._logger.debug("[_async_update_data] cover %s under manual control", cover)
                per_cover_control_reasons[cover] = CoverControlReason.UNDER_MANUAL_CONTROL
                continue
            if not force_set_position and not self._is_update_allowed_by_time_threshold(cover):
                self._logger.debug(
                    "[_async_update_data] update to %s not allowed by time threshold",
                    cover,
                )
                per_cover_control_reasons[cover] = CoverControlReason.TIME_THRESHOLD_DISALLOWED
                continue
            if self._is_already_at_position(cover, calculated_target.target_position):
                self._logger.debug("[_async_update_data] cover %s already at position", cover)
                per_cover_control_reasons[cover] = CoverControlReason.ALREADY_AT_TARGET
                continue
            # Okay now actually set the position.
            await self._async_set_cover_position(cover, calculated_target.target_position)

        # If all the covers are under manual control, report that as the reason.
        if set(per_cover_control_reasons.values()) == {CoverControlReason.UNDER_MANUAL_CONTROL}:
            calculated_target.reason = CoverControlReason.UNDER_MANUAL_CONTROL

        # Return updated data.
        return self._generate_data(
            {
                "target_position": calculated_target.target_position,
                "sun_in_front_of_window": calculated_target.is_sun_in_front_of_window_and_not_in_blind_spot_and_not_at_dawn_or_dusk,
                "reason": calculated_target.reason,
                "tweaks": calculated_target.tweaks,
                "per_cover_reasons": per_cover_control_reasons,
            }
        )

    async def _async_set_cover_position(self, entity, target_position):
        service = SERVICE_SET_COVER_POSITION
        service_data = {}
        service_data[ATTR_ENTITY_ID] = entity
        service_data[ATTR_POSITION] = target_position

        self._cover_entities_in_motion[entity] = target_position
        self._logger.debug(
            "[_async_set_cover_position] cover entities in motion: %s",
            self._cover_entities_in_motion,
        )
        self._logger.debug("[_async_set_cover_position] Run %s with data %s", service, service_data)
        await self.hass.services.async_call(COVER_DOMAIN, service, service_data)

    def _is_after_start_time(self):
        if self._get_start_time() is None:
            return True
        now = datetime.now(tz=UTC)
        self._logger.debug(
            "[_is_after_start_time] Start time: %s, now: %s, now >= time: %s",
            self._get_start_time(),
            now,
            now >= self._get_start_time(),
        )
        return now >= self._get_start_time()

    def _is_before_end_time(self):
        if self._get_end_time() is None:
            return True
        now = datetime.now(tz=UTC)
        self._logger.debug(
            "[_is_before_end_time] End time: %s, now: %s, now < time: %s",
            self._get_end_time(),
            now,
            now < self._get_end_time(),
        )
        return now < self._get_end_time()

    def _is_within_control_time_range(self):
        return self._is_before_end_time() and self._is_after_start_time()

    def _is_already_at_position(self, entity, target_position):
        OVERRIDE_POSITIONS = [0, 100]

        if self._automation_config.invert:
            OVERRIDE_POSITIONS.extend(
                [
                    100 - self._automation_config.default_cover_position,
                    100 - self._automation_config.before_sunrise_or_after_sunset_cover_position,
                ]
            )
        else:
            OVERRIDE_POSITIONS.extend(
                [
                    self._automation_config.default_cover_position,
                    self._automation_config.before_sunrise_or_after_sunset_cover_position,
                ]
            )

        position = state_attr(self.hass, entity, "current_position")

        if position is None:
            self._logger.debug("[_is_already_at_position] No position for cover %s", entity)
            return False

        if position == target_position:
            self._logger.debug(
                "[_is_already_at_position] Cover %s already at position %s",
                entity,
                position,
            )
            return True

        if target_position in OVERRIDE_POSITIONS:
            self._logger.debug(
                "[_is_already_at_position] Overriding already-at-position check for cover %s with target target_position %s",
                entity,
                target_position,
            )
            return False

        diff = abs(position - target_position)
        self._logger.debug(
            "[_is_already_at_position] cover=%s position=%s, target=%s, diff=%s, min_change=%s",
            entity,
            position,
            target_position,
            diff,
            self._automation_config.minimum_change_percentage,
        )
        return diff < self._automation_config.minimum_change_percentage

    def _is_update_allowed_by_time_threshold(self, entity):
        state = self.hass.states.get(entity)
        if state is None:
            self._logger.debug(
                "[_is_update_allowed_by_time_threshold] state not available for %s",
                entity,
            )
            return True
        if state.last_updated is None:
            self._logger.debug(
                "[_is_update_allowed_by_time_threshold] last-updated time not available for %s",
                entity,
            )  # pragma: no cover
            return True  # pragma: no cover
        now = datetime.now(tz=UTC)
        delta = now - state.last_updated
        result = delta >= self._automation_config.minimum_change_time
        self._logger.debug(
            "[_is_update_allowed_by_time_threshold] entity=%s, time delta=%s, threshold=%s, result=%s",
            entity,
            delta,
            self._automation_config.minimum_change_time,
            result,
        )
        return result

    async def async_dependent_entity_state_change(self, event: Event[EventStateChangedData]) -> None:
        self._logger.debug(
            "[async_dependent_entity_state_change] dependent entity state change: %s",
            event,
        )
        await self.async_refresh()

    async def async_cover_entity_state_change(self, event: Event[EventStateChangedData]) -> None:
        self._logger.debug("[async_cover_entity_state_change] Cover entity state change: %s", event)
        if event.data["old_state"] is None:
            self._logger.debug("[async_cover_entity_state_change] Old state is none.")  # pragma: no cover
        elif "current_position" not in event.data["old_state"].attributes:
            self._logger.debug("[async_cover_entity_state_change] Old position is unknown.")
        self._logger.debug(
            "[async_cover_entity_state_change] Processing state change event for %s: %s",
            event.data["entity_id"],
            event.data["new_state"],
        )
        if event.data["entity_id"] not in self._automation_config.entities:
            self._logger.debug(
                "[async_cover_entity_state_change] event for untracked cover %s",
                event.data["entity_id"],
            )  # pragma: no cover
            return  # pragma: no cover
        in_motion_target = self._cover_entities_in_motion.get(event.data["entity_id"], None)
        if in_motion_target is not None:
            position = event.data["new_state"].attributes.get("current_position")
            if position == in_motion_target:
                del self._cover_entities_in_motion[event.data["entity_id"]]
                self._logger.debug(
                    "[async_cover_entity_state_change] Position %s reached for %s",
                    position,
                    event.data["entity_id"],
                )
            else:
                self._logger.debug(
                    "[async_cover_entity_state_change] Waiting for %s to reach %s, currently at %s",
                    event.data["entity_id"],
                    in_motion_target,
                    position,
                )
            # Nothing to do here.
            return
        if self._manual_overrides.should_ignore_state_change(event.data["new_state"]):
            self._logger.debug(
                "[async_cover_entity_state_change] Ignoring state change for %s",
                event.data["entity_id"],
            )
            return
        self._logger.debug(
            "[async_cover_entity_state_change] Not expecting cover %s to be in motion",
            event.data["entity_id"],
        )
        self._cover_state_change_data = CoverStateChangeData(event.data["entity_id"], event.data["new_state"])
        self._async_refresh_requests.cover_state_change = True
        await self.async_refresh()

    async def async_reset_manual_override(self):
        self._manual_overrides.clear_all()
        await self.async_refresh()

    async def async_enable_detection_of_manual_override(self, on_newly_added_to_hass: bool) -> bool:
        self._manual_overrides.enable_detection()
        return True

    async def async_disable_detection_of_manual_override(self, on_newly_added_to_hass: bool) -> bool:
        self._manual_overrides.disable_detection()
        self._manual_overrides.clear_all()
        return True

    async def async_enable_automated_control(self, on_newly_added_to_hass: bool) -> bool:
        self._enable_automation = True
        # Trigger a call to async_refresh().
        return True

    async def async_disable_automated_control(self, on_newly_added_to_hass: bool) -> bool:
        self._enable_automation = False
        if not on_newly_added_to_hass:
            self._manual_overrides.clear_all()
        # Trigger a call to async_refresh().
        return True

    def get_dependencies(self) -> list[str]:
        return [
            e
            for e in [
                "sun.sun",
                self._sensor_config.presence_entity,
                self._sensor_config.window_sensor_entity,
                self._sensor_config.weather_entity,
                self._sensor_config.lux_entity,
                self._automation_config.end_time_entity,
            ]
            if e is not None
        ]

    def get_cover_entities(self) -> list[str]:
        return self._automation_config.entities
