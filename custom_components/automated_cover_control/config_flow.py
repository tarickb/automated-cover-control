from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION,
    CONF_BLIND_SPOT_ELEVATION,
    CONF_BLIND_SPOT_ENABLED,
    CONF_BLIND_SPOT_LEFT,
    CONF_BLIND_SPOT_RIGHT,
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
    DOMAIN,
)

BASE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): selector.TextSelector(),
    }
)

WINDOW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WINDOW_AZIMUTH, default=180): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=359, mode="slider", unit_of_measurement="°")
        ),
        vol.Required(CONF_WINDOW_HEIGHT, default=2.1): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.1, max=6, step=0.01, mode="slider", unit_of_measurement="m")
        ),
        vol.Required(CONF_DISTANCE_FROM_WINDOW, default=0.5): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.1, max=2, step=0.1, mode="slider", unit_of_measurement="m")
        ),
        vol.Optional(CONF_MIN_SOLAR_ELEVATION): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
        vol.Optional(CONF_MAX_SOLAR_ELEVATION): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
        vol.Optional(CONF_FOV_LEFT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=90, step=1, mode="slider", unit_of_measurement="°")
        ),
        vol.Optional(CONF_FOV_RIGHT, default=90): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=90, step=1, mode="slider", unit_of_measurement="°")
        ),
        vol.Optional(CONF_BLIND_SPOT_ENABLED, default=False): bool,
    }
)

BLIND_SPOT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BLIND_SPOT_LEFT, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="slider", unit_of_measurement="°", min=0, max=180)
        ),
        vol.Required(CONF_BLIND_SPOT_RIGHT, default=1): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="slider", unit_of_measurement="°", min=1, max=180)
        ),
        vol.Optional(CONF_BLIND_SPOT_ELEVATION): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    }
)

COVER_POSITION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTITIES, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                multiple=True,
                filter=selector.EntityFilterSelectorConfig(
                    domain="cover",
                    supported_features=["cover.CoverEntityFeature.SET_POSITION"],
                ),
            )
        ),
        vol.Required(CONF_DEFAULT_COVER_POSITION, default=60): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode="slider", unit_of_measurement="%")
        ),
        vol.Optional(CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode="slider", unit_of_measurement="%")
        ),
        vol.Optional(CONF_MAXIMUM_COVER_POSITION): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        vol.Optional(CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW, default=False): bool,
        vol.Optional(CONF_MINIMUM_COVER_POSITION): vol.All(vol.Coerce(int), vol.Range(min=0, max=99)),
        vol.Optional(CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW, default=False): bool,
        vol.Optional(CONF_INVERT, default=False): bool,
    }
)

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PRESENCE_ENTITY): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["device_tracker", "zone", "binary_sensor", "input_boolean"])
        ),
        vol.Optional(CONF_WINDOW_SENSOR_ENTITY): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["binary_sensor", "input_boolean"], device_class="window")
        ),
        vol.Optional(CONF_LUX_ENTITY): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain=["sensor"], device_class="illuminance")
        ),
        vol.Optional(CONF_LUX_THRESHOLD, default=1000): selector.NumberSelector(
            selector.NumberSelectorConfig(mode="box", unit_of_measurement="lux")
        ),
        vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
            selector.EntityFilterSelectorConfig(domain="weather")
        ),
        vol.Optional(CONF_WEATHER_STATE, default=["sunny", "partlycloudy", "cloudy", "clear"]): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=True,
                sort=False,
                options=[
                    "clear-night",
                    "clear",
                    "cloudy",
                    "fog",
                    "hail",
                    "lightning",
                    "lightning-rainy",
                    "partlycloudy",
                    "pouring",
                    "rainy",
                    "snowy",
                    "snowy-rainy",
                    "sunny",
                    "windy",
                    "windy-variant",
                    "exceptional",
                ],
            )
        ),
    }
)

AUTOMATION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SUNRISE_OFFSET): selector.DurationSelector(),
        vol.Optional(CONF_SUNSET_OFFSET): selector.DurationSelector(),
        vol.Optional(CONF_START_TIME): selector.TimeSelector(),
        vol.Optional(CONF_START_TIME_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        vol.Optional(CONF_END_TIME): selector.TimeSelector(),
        vol.Optional(CONF_END_TIME_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        vol.Optional(CONF_MINIMUM_CHANGE_PERCENTAGE, default=1): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=90, step=1, mode="slider", unit_of_measurement="%")
        ),
        vol.Optional(CONF_MINIMUM_CHANGE_TIME, default={"minutes": 2}): selector.DurationSelector(),
        vol.Optional(CONF_RETURN_TO_DEFAULT_AT_END_TIME, default=False): bool,
    }
)

MANUAL_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MANUAL_OVERRIDE_DURATION, default={"minutes": 15}): selector.DurationSelector(),
        vol.Optional(CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT, default=False): bool,
        vol.Optional(CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD): vol.All(vol.Coerce(int), vol.Range(min=0, max=99)),
        vol.Optional(CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS, default=False): bool,
    }
)


def _validate_window_params(user_input: dict[str, Any]) -> dict[str, str] | None:
    if (
        user_input.get(CONF_MAX_SOLAR_ELEVATION) is not None
        and user_input.get(CONF_MIN_SOLAR_ELEVATION) is not None
        and user_input[CONF_MAX_SOLAR_ELEVATION] <= user_input[CONF_MIN_SOLAR_ELEVATION]
    ):
        return {CONF_MAX_SOLAR_ELEVATION: "max_solar_elevation_less_than_min"}
    return None


def _validate_blind_spot_params(user_input: dict[str, Any]) -> dict[str, str] | None:
    if (
        user_input.get(CONF_BLIND_SPOT_LEFT) is not None
        and user_input.get(CONF_BLIND_SPOT_RIGHT) is not None
        and user_input[CONF_BLIND_SPOT_LEFT] >= user_input[CONF_BLIND_SPOT_RIGHT]
    ):
        return {CONF_BLIND_SPOT_RIGHT: "blind_spot_right_less_than_left"}
    return None


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    def __init__(self) -> None:
        super().__init__()
        self.config: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(step_id="init", data_schema=BASE_SCHEMA)
        self.config = user_input
        return await self.async_step_window()

    async def async_step_window(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = _validate_window_params(user_input) if user_input else None
        if errors or not user_input:
            return self.async_show_form(
                step_id="window",
                data_schema=WINDOW_SCHEMA,
                errors=errors,
            )
        self.config.update(user_input)
        if self.config[CONF_BLIND_SPOT_ENABLED]:
            return await self.async_step_blind_spot()
        return await self.async_step_cover_position()

    async def async_step_blind_spot(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = _validate_blind_spot_params(user_input) if user_input else None
        if errors or not user_input:
            return self.async_show_form(
                step_id="blind_spot",
                data_schema=BLIND_SPOT_SCHEMA,
                errors=errors,
            )
        self.config.update(user_input)
        return await self.async_step_cover_position()

    async def async_step_cover_position(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="cover_position",
                data_schema=COVER_POSITION_SCHEMA,
            )
        self.config.update(user_input)
        return await self.async_step_sensor()

    async def async_step_sensor(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="sensor",
                data_schema=SENSOR_SCHEMA,
            )
        self.config.update(user_input)
        return await self.async_step_automation()

    async def async_step_automation(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="automation",
                data_schema=AUTOMATION_SCHEMA,
            )
        self.config.update(user_input)
        return await self.async_step_manual_override()

    async def async_step_manual_override(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="manual_override",
                data_schema=MANUAL_OVERRIDE_SCHEMA,
            )
        self.config.update(user_input)
        return await self.async_step_update()

    async def async_step_update(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_create_entry(
            title=f"{self.config['name']} Automated Cover Control",
            data={
                "name": self.config["name"],
            },
            options={
                CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION: self.config.get(
                    CONF_BEFORE_SUNRISE_OR_AFTER_SUNSET_COVER_POSITION
                ),
                CONF_BLIND_SPOT_ELEVATION: self.config.get(CONF_BLIND_SPOT_ELEVATION, None),
                CONF_BLIND_SPOT_ENABLED: self.config.get(CONF_BLIND_SPOT_ENABLED),
                CONF_BLIND_SPOT_LEFT: self.config.get(CONF_BLIND_SPOT_LEFT, None),
                CONF_BLIND_SPOT_RIGHT: self.config.get(CONF_BLIND_SPOT_RIGHT, None),
                CONF_DEFAULT_COVER_POSITION: self.config.get(CONF_DEFAULT_COVER_POSITION),
                CONF_DISTANCE_FROM_WINDOW: self.config.get(CONF_DISTANCE_FROM_WINDOW),
                CONF_END_TIME: self.config.get(CONF_END_TIME),
                CONF_END_TIME_ENTITY: self.config.get(CONF_END_TIME_ENTITY),
                CONF_ENTITIES: self.config.get(CONF_ENTITIES),
                CONF_FOV_LEFT: self.config.get(CONF_FOV_LEFT),
                CONF_FOV_RIGHT: self.config.get(CONF_FOV_RIGHT),
                CONF_INVERT: self.config.get(CONF_INVERT),
                CONF_LUX_ENTITY: self.config.get(CONF_LUX_ENTITY),
                CONF_LUX_THRESHOLD: self.config.get(CONF_LUX_THRESHOLD),
                CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD: self.config.get(CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD),
                CONF_MANUAL_OVERRIDE_DURATION: self.config.get(CONF_MANUAL_OVERRIDE_DURATION),
                CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS: self.config.get(
                    CONF_MANUAL_OVERRIDE_IGNORE_INTERMEDIATE_POSITIONS
                ),
                CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: self.config.get(
                    CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT
                ),
                CONF_MAXIMUM_COVER_POSITION: self.config.get(CONF_MAXIMUM_COVER_POSITION),
                CONF_MAX_SOLAR_ELEVATION: self.config.get(CONF_MAX_SOLAR_ELEVATION, None),
                CONF_MINIMUM_CHANGE_PERCENTAGE: self.config.get(CONF_MINIMUM_CHANGE_PERCENTAGE),
                CONF_MINIMUM_CHANGE_TIME: self.config.get(CONF_MINIMUM_CHANGE_TIME),
                CONF_MINIMUM_COVER_POSITION: self.config.get(CONF_MINIMUM_COVER_POSITION),
                CONF_MIN_SOLAR_ELEVATION: self.config.get(CONF_MIN_SOLAR_ELEVATION, None),
                CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: self.config.get(
                    CONF_ONLY_FORCE_MAXIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW
                ),
                CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW: self.config.get(
                    CONF_ONLY_FORCE_MINIMUM_WHEN_SUN_IN_FRONT_OF_WINDOW
                ),
                CONF_PRESENCE_ENTITY: self.config.get(CONF_PRESENCE_ENTITY),
                CONF_RETURN_TO_DEFAULT_AT_END_TIME: self.config.get(CONF_RETURN_TO_DEFAULT_AT_END_TIME),
                CONF_START_TIME: self.config.get(CONF_START_TIME),
                CONF_START_TIME_ENTITY: self.config.get(CONF_START_TIME_ENTITY),
                CONF_SUNRISE_OFFSET: self.config.get(CONF_SUNRISE_OFFSET),
                CONF_SUNSET_OFFSET: self.config.get(CONF_SUNSET_OFFSET),
                CONF_WEATHER_ENTITY: self.config.get(CONF_WEATHER_ENTITY),
                CONF_WEATHER_STATE: self.config.get(CONF_WEATHER_STATE),
                CONF_WINDOW_AZIMUTH: self.config.get(CONF_WINDOW_AZIMUTH),
                CONF_WINDOW_HEIGHT: self.config.get(CONF_WINDOW_HEIGHT),
                CONF_WINDOW_SENSOR_ENTITY: self.config.get(CONF_WINDOW_SENSOR_ENTITY),
            },
        )


class OptionsFlowHandler(OptionsFlowWithReload):
    def _build_updated_entry(self, user_input: dict[str, Any], schema: vol.Schema) -> ConfigFlowResult:
        options = dict(self.config_entry.options)
        for key in schema.schema:
            if not isinstance(key, vol.schema_builder.Optional):
                continue
            if key in options and key not in user_input:
                del options[key]
        options.update(user_input)
        return self.async_create_entry(title="", data=options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        options = ["window"]
        if self.config_entry.options.get(CONF_BLIND_SPOT_ENABLED):
            options.append("blind_spot")
        options.extend(["cover_position", "sensor", "automation", "manual_override"])
        return self.async_show_menu(step_id="init", menu_options=options)

    async def async_step_window(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = _validate_window_params(user_input) if user_input else None
        if errors or not user_input:
            return self.async_show_form(
                step_id="window",
                data_schema=self.add_suggested_values_to_schema(WINDOW_SCHEMA, self.config_entry.options),
                errors=errors,
            )
        return self._build_updated_entry(user_input, WINDOW_SCHEMA)

    async def async_step_blind_spot(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = _validate_blind_spot_params(user_input) if user_input else None
        if errors or not user_input:
            return self.async_show_form(
                step_id="blind_spot",
                data_schema=self.add_suggested_values_to_schema(BLIND_SPOT_SCHEMA, self.config_entry.options),
                errors=errors,
            )
        return self._build_updated_entry(user_input, BLIND_SPOT_SCHEMA)

    async def async_step_cover_position(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="cover_position",
                data_schema=self.add_suggested_values_to_schema(COVER_POSITION_SCHEMA, self.config_entry.options),
            )
        return self._build_updated_entry(user_input, COVER_POSITION_SCHEMA)

    async def async_step_sensor(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="sensor",
                data_schema=self.add_suggested_values_to_schema(SENSOR_SCHEMA, self.config_entry.options),
            )
        return self._build_updated_entry(user_input, SENSOR_SCHEMA)

    async def async_step_automation(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="automation",
                data_schema=self.add_suggested_values_to_schema(AUTOMATION_SCHEMA, self.config_entry.options),
            )
        return self._build_updated_entry(user_input, AUTOMATION_SCHEMA)

    async def async_step_manual_override(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not user_input:
            return self.async_show_form(
                step_id="manual_override",
                data_schema=self.add_suggested_values_to_schema(MANUAL_OVERRIDE_SCHEMA, self.config_entry.options),
            )
        return self._build_updated_entry(user_input, MANUAL_OVERRIDE_SCHEMA)
