import types
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import State

from .config import ManualOverrideConfiguration
from .log_context_adapter import LogContextAdapter


class ManualOverrideManager:
    _logger: LogContextAdapter
    _config: ManualOverrideConfiguration
    _enable_detection: bool
    _override_expiry: dict[str, datetime]

    def __init__(self, logger: LogContextAdapter) -> None:
        self._logger = logger
        self._config = ManualOverrideConfiguration()
        self._enable_detection = False
        self._override_expiry = {}

    def _mark_manual_control(self, entity_id: str, last_updated: datetime):
        if entity_id not in self._override_expiry or self._config.reset_timer_at_each_adjustment:
            self._override_expiry[entity_id] = last_updated + (self._config.override_duration or timedelta())
            self._logger.debug(
                "[ManualOverrideManager._mark_manual_control] Manual control of %s expires at %s",
                entity_id,
                self._override_expiry[entity_id],
            )
        elif not self._config.reset_timer_at_each_adjustment:
            self._logger.debug(
                "[ManualOverrideManager._mark_manual_control] %s under manual control, reset not allowed",
                entity_id,
            )

    def update_config(self, config: types.MappingProxyType[str, Any]) -> None:
        self._config.read(config)

    def enable_detection(self) -> None:
        self._enable_detection = True

    def disable_detection(self) -> None:
        self._enable_detection = False

    def clear_all(self) -> None:
        self._override_expiry = {}

    def should_ignore_state_change(self, new_state: State) -> bool:
        if self._config.ignore_intermediate_positions and new_state.state in [
            "opening",
            "closing",
        ]:
            return True
        self._logger.debug(
            "[ManualOverrideManager.should_ignore_state_change] context: %s", new_state.context.as_dict()
        )
        if self._config.ignore_non_user_triggered_changes and not new_state.context.user_id:
            self._logger.debug("[ManualOverrideManager.should_ignore_state_change] ignoring non-user-triggered change")
            return True
        return False

    def get_config(self) -> ManualOverrideConfiguration:
        return self._config

    def handle_state_change(self, entity_id: str, new_state: State, target_position: int):
        if not self._enable_detection:
            self._logger.debug("[ManualOverrideManager.handle_state_change] Detection disabled")
            return
        new_position = new_state.attributes.get("current_position") or 0
        if new_position == target_position:
            self._logger.debug(
                "[ManualOverrideManager.handle_state_change] New position %s matches expected state for %s",
                new_position,
                entity_id,
            )
            return

        if abs(target_position - new_position) < (self._config.detection_threshold or 0):
            self._logger.debug(
                "[ManualOverrideManager.handle_state_change] Position change less than threshold %s for %s",
                self._config.detection_threshold,
                entity_id,
            )
            return

        self._logger.debug(
            "[ManualOverrideManager.handle_state_change] Manual change detected for %s. Our state: %s, new state: %s, manual threshold: %s",
            entity_id,
            target_position,
            new_position,
            self._config.detection_threshold,
        )
        self._logger.debug(
            "[ManualOverrideManager.handle_state_change] Set manual control for %s, for at least %s",
            entity_id,
            self._config.override_duration,
        )
        self._mark_manual_control(entity_id, new_state.last_updated)

    def reset_expired_overrides(self, now=None):
        if now is None:
            now = datetime.now(tz=UTC)
        expiry_copy = self._override_expiry.copy()
        for entity_id, expiry in expiry_copy.items():
            if now > expiry:
                self._logger.debug(
                    "[ManualOverrideManager.reset_expired_overrides] Resetting %s, expired at %s",
                    entity_id,
                    expiry,
                )
                del self._override_expiry[entity_id]

    def is_cover_manual(self, entity_id):
        return entity_id in self._override_expiry

    def is_any_cover_under_manual_control(self) -> bool:
        return len(self._override_expiry) > 0

    def covers_under_manual_control(self):
        return list(self._override_expiry.keys())
