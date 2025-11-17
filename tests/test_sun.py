from datetime import datetime

from dateutil import tz

from custom_components.automated_cover_control.config import WindowConfiguration
from custom_components.automated_cover_control.sun import SolarTimeCalculator


class FakeHass:
    class FakeConfig:
        latitude = 37.80
        longitude = -122.46
        time_zone = "America/Los_Angeles"
        elevation = 0

    config = FakeConfig()
    data = {}


def test_solar_time_calculator():
    hass = FakeHass()

    window = WindowConfiguration()
    window.window_azimuth = 86

    zone = tz.gettz("America/Los_Angeles")

    calc = SolarTimeCalculator(hass, window)
    start, end = calc.get_solar_start_and_end_times()
    assert start.date() == datetime.now(zone).date()
    assert end.date() == datetime.now(zone).date()
    assert end > start
