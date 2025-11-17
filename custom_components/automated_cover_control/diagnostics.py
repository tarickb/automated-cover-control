from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry):
    return {
        "title": "Automated Cover Control",
        "type": "config_entry",
        "identifier": config_entry.entry_id,
        "config_data": dict(config_entry.data),
        "config_options": dict(config_entry.options),
    }
