from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENTITIES, DOMAIN
from .coordinator import AutomatedCoverControlDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AutomatedCoverControlDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    if CONF_ENTITIES not in config_entry.options or len(config_entry.options.get(CONF_ENTITIES)) < 1:
        return

    manual_switch = CoordinatorActionSwitch(
        config_entry=config_entry,
        unique_id=config_entry.entry_id,
        switch_name="Enable Detection of Manual Overrides",
        key="enable_detection_of_manual_overrides",
        initial_state=True,
        coordinator=coordinator,
        on_turned_on=lambda coord, on_added: coord.async_enable_detection_of_manual_override(on_added),
        on_turned_off=lambda coord, on_added: coord.async_disable_detection_of_manual_override(on_added),
    )

    control_switch = CoordinatorActionSwitch(
        config_entry=config_entry,
        unique_id=config_entry.entry_id,
        switch_name="Enable Automated Control",
        key="enable_automated_control",
        initial_state=True,
        coordinator=coordinator,
        on_turned_on=lambda coord, on_added: coord.async_enable_automated_control(on_added),
        on_turned_off=lambda coord, on_added: coord.async_disable_automated_control(on_added),
    )

    async_add_entities([control_switch, manual_switch])


class CoordinatorActionSwitch(
    CoordinatorEntity[AutomatedCoverControlDataUpdateCoordinator],
    SwitchEntity,
    RestoreEntity,
):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        switch_name: str,
        key: str,
        initial_state: bool,
        coordinator: AutomatedCoverControlDataUpdateCoordinator,
        device_class: SwitchDeviceClass | None = None,
        on_turned_on: Callable[[AutomatedCoverControlDataUpdateCoordinator, bool], bool] | None = None,
        on_turned_off: Callable[[AutomatedCoverControlDataUpdateCoordinator, bool], bool] | None = None,
    ) -> None:
        super().__init__(coordinator=coordinator)

        self._name = config_entry.data["name"]
        self._state: bool | None = None
        self._key = key
        self._attr_translation_key = key
        self._device_name = f"{self._name} Automated Cover Control"
        self._switch_name = switch_name
        self._attr_device_class = device_class
        self._initial_state = initial_state
        self._attr_unique_id = f"{unique_id}_{key}"
        self._device_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )
        self._on_turned_on = on_turned_on
        self._on_turned_off = on_turned_off

    @property
    def name(self):
        return f"{self._switch_name}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        if self._on_turned_on is not None and await self._on_turned_on(
            self.coordinator, kwargs.get("on_added_to_hass")
        ):
            await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        if self._on_turned_off is not None and await self._on_turned_off(
            self.coordinator, kwargs.get("on_added_to_hass")
        ):
            await self.coordinator.async_refresh()
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        last_state = await self.async_get_last_state()
        self.coordinator.logger.debug("%s: last state is %s", self._name, last_state)
        if (last_state is None and self._initial_state) or (last_state is not None and last_state.state == STATE_ON):
            await self.async_turn_on(on_added_to_hass=True)
        else:
            await self.async_turn_off(on_added_to_hass=True)
