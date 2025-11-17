from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENTITIES, DOMAIN
from .coordinator import AutomatedCoverControlDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AutomatedCoverControlDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    if len(config_entry.options.get(CONF_ENTITIES, [])) < 1:
        return

    reset_manual = ResetManualOverrideButton(
        config_entry=config_entry, unique_id=config_entry.entry_id, coordinator=coordinator
    )
    async_add_entities([reset_manual])


class ResetManualOverrideButton(CoordinatorEntity[AutomatedCoverControlDataUpdateCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:cog-refresh-outline"

    def __init__(
        self,
        config_entry,
        unique_id: str,
        coordinator: AutomatedCoverControlDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator=coordinator)

        self._name = config_entry.data["name"]
        self._device_name = f"{self._name} Automated Cover Control"
        self._attr_unique_id = f"{unique_id}_reset_manual_override"
        self._device_id = unique_id
        self._button_name = "Reset Manual Override"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
        )

    @property
    def name(self):
        return f"{self._button_name}"

    async def async_press(self) -> None:
        await self.coordinator.async_reset_manual_override()
