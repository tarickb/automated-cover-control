from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AutomatedCoverControlDataUpdateCoordinator
from .why import CoverControlReason


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    name = config_entry.data["name"]
    coordinator: AutomatedCoverControlDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    sun_in_window_start = TimeSensorEntity(
        unique_id=config_entry.entry_id,
        hass=hass,
        config_entry=config_entry,
        name=name,
        sensor_name="Sun in Window Start",
        key="sun_in_window_start",
        icon="mdi:sun-clock-outline",
        coordinator=coordinator,
    )
    sun_in_window_end = TimeSensorEntity(
        unique_id=config_entry.entry_id,
        hass=hass,
        config_entry=config_entry,
        name=name,
        sensor_name="Sun in Window End",
        key="sun_in_window_end",
        icon="mdi:sun-clock",
        coordinator=coordinator,
    )
    cover_position = CoverPositionSensorEntity(
        unique_id=config_entry.entry_id, hass=hass, config_entry=config_entry, name=name, coordinator=coordinator
    )
    cover_state = CoverStateSensorEntity(
        unique_id=config_entry.entry_id, hass=hass, config_entry=config_entry, name=name, coordinator=coordinator
    )

    async_add_entities([sun_in_window_start, sun_in_window_end, cover_position, cover_state])


class TimeSensorEntity(CoordinatorEntity[AutomatedCoverControlDataUpdateCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        sensor_name: str,
        key: str,
        icon: str,
        coordinator: AutomatedCoverControlDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator=coordinator)

        self._attr_icon = icon
        self.key = key
        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._attr_unique_id = f"{unique_id}_{key}"
        self._device_id = unique_id
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._sensor_name = sensor_name
        self._device_name = f"{self._name} Automated Cover Control"

    @callback
    def _handle_coordinator_update(self) -> None:
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def name(self):
        return f"{self._sensor_name}"

    @property
    def native_value(self) -> str | None:
        return self.data.states[self.key]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )


class CoverStateSensorEntity(CoordinatorEntity[AutomatedCoverControlDataUpdateCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = None
    _attr_icon = "mdi:sun-compass"
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_visible_default = False
    _attr_options = [e.value for e in CoverControlReason]

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: AutomatedCoverControlDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator=coordinator)

        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._sensor_name = "State"
        self._attr_unique_id = f"{unique_id}_state"
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._device_name = f"{self._name} Automated Cover Control"
        self._device_id = unique_id

    @callback
    def _handle_coordinator_update(self) -> None:
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def name(self):
        return f"{self._sensor_name}"

    @property
    def native_value(self) -> str | None:
        return self.data.states["reason"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "config": self.data.attributes,
            "tweaks": self.data.states.get("tweaks", []),
            "per_cover_reasons": self.data.states.get("per_cover_reasons", {}),
        }


class CoverPositionSensorEntity(CoordinatorEntity[AutomatedCoverControlDataUpdateCoordinator], SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:sun-compass"
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        unique_id: str,
        hass,
        config_entry,
        name: str,
        coordinator: AutomatedCoverControlDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator=coordinator)

        self.coordinator = coordinator
        self.data = self.coordinator.data
        self._sensor_name = "Target Cover Position"
        self._attr_unique_id = f"{unique_id}_target_cover_position"
        self.hass = hass
        self.config_entry = config_entry
        self._name = name
        self._device_name = f"{self._name} Automated Cover Control"
        self._device_id = unique_id

    @callback
    def _handle_coordinator_update(self) -> None:
        self.data = self.coordinator.data
        self.async_write_ha_state()

    @property
    def name(self):
        return f"{self._sensor_name}"

    @property
    def native_value(self) -> str | None:
        return self.data.states.get("target_position", None)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )
