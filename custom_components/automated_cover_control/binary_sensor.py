from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AutomatedCoverControlDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AutomatedCoverControlDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    sun_in_front_of_window = CoverStateBinarySensorEntity(
        config_entry=config_entry,
        unique_id=config_entry.entry_id,
        sensor_name="Sun in Front of Window",
        state=False,
        key="sun_in_front_of_window",
        device_class=BinarySensorDeviceClass.MOTION,
        coordinator=coordinator,
    )
    manual_override = CoverStateBinarySensorEntity(
        config_entry=config_entry,
        unique_id=config_entry.entry_id,
        sensor_name="Manual Override Detected",
        state=False,
        key="manual_override",
        device_class=BinarySensorDeviceClass.MOTION,
        coordinator=coordinator,
        extra_data_generator=lambda coord: {"manually_controlled": coord.data.states["covers_under_manual_control"]},
    )
    async_add_entities([sun_in_front_of_window, manual_override])


class CoverStateBinarySensorEntity(CoordinatorEntity[AutomatedCoverControlDataUpdateCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        config_entry,
        unique_id: str,
        sensor_name: str,
        state: bool,
        key: str,
        device_class: BinarySensorDeviceClass,
        coordinator: AutomatedCoverControlDataUpdateCoordinator,
        extra_data_generator: Callable[[AutomatedCoverControlDataUpdateCoordinator], Mapping[str, Any]] | None = None,
    ) -> None:
        super().__init__(coordinator=coordinator)

        self._key = key
        self._attr_translation_key = key
        self._name = config_entry.data["name"]
        self._device_name = f"{self._name} Automated Cover Control"
        self._sensor_name = sensor_name
        self._attr_unique_id = f"{unique_id}_{key}"
        self._device_id = unique_id
        self._state = state
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )
        self._extra_data_generator = extra_data_generator

    @property
    def name(self):
        return f"{self._sensor_name}"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.states.get(self._key, None)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        if self._extra_data_generator is not None:
            return self._extra_data_generator(self.coordinator)
        return {}
