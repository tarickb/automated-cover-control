from datetime import datetime, time

import astral
import pandas as pd
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_location
from homeassistant.util.dt import get_time_zone

from .config import WindowConfiguration


class SolarTimeCalculator:
    _hass: HomeAssistant
    _window_config: WindowConfiguration
    _location: astral.location.Location
    _elevation: astral.Elevation

    def __init__(self, hass: HomeAssistant, window_config: WindowConfiguration) -> None:
        self._hass = hass
        self._window_config = window_config
        self._location, self._elevation = get_astral_location(self._hass)

    def _get_times(self) -> pd.DatetimeIndex:
        zone = get_time_zone(self._hass.config.time_zone)
        start_date = datetime.combine(datetime.now(zone), time.min, zone)
        end_date = datetime.combine(datetime.now(zone), time.max, zone)
        return pd.date_range(start=start_date, end=end_date, freq="5min", name="time")

    def _get_solar_azimuths(self) -> list:
        return [self._location.solar_azimuth(t, self._elevation) for t in self._get_times()]

    def _get_solar_elevations(self) -> list:
        return [self._location.solar_elevation(t, self._elevation) for t in self._get_times()]

    def _azi_min_abs(self) -> int:
        return (self._window_config.window_azimuth - self._window_config.fov_left + 360) % 360

    def _azi_max_abs(self) -> int:
        return (self._window_config.window_azimuth + self._window_config.fov_right + 360) % 360

    def get_solar_start_and_end_times(self):
        df_today = pd.DataFrame(
            {
                "azimuth": self._get_solar_azimuths(),
                "elevation": self._get_solar_elevations(),
            }
        )
        solpos = df_today.set_index(self._get_times())

        alpha = solpos["azimuth"]
        frame = ((alpha - self._azi_min_abs()) % 360 <= (self._azi_max_abs() - self._azi_min_abs()) % 360) & (
            solpos["elevation"] > 0
        )

        if solpos[frame].empty:
            return None, None

        return (
            solpos[frame].index[0].to_pydatetime(),
            solpos[frame].index[-1].to_pydatetime(),
        )
