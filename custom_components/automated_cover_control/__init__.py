from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import DOMAIN
from .coordinator import AutomatedCoverControlDataUpdateCoordinator
from .log_context_adapter import LogContextAdapter

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_initialize_integration(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> bool:
    return True  # pragma: no cover


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    coordinator = AutomatedCoverControlDataUpdateCoordinator(hass)
    dependencies = coordinator.get_dependencies()
    cover_entities = coordinator.get_cover_entities()

    logger = LogContextAdapter(logging.getLogger(__name__))
    logger.set_config_name(entry.data.get("name"))
    logger.info("Dependencies: %s", dependencies)
    logger.info("Covers: %s", cover_entities)

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            dependencies,
            coordinator.async_dependent_entity_state_change,
        )
    )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            cover_entities,
            coordinator.async_cover_entity_state_change,
        )
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
