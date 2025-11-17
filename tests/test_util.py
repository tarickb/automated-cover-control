from dataclasses import dataclass
from datetime import UTC, time

from custom_components.automated_cover_control.util import (
    get_state_or_none_if_unknown,
    midnight_to_end_of_day,
)


@dataclass
class FakeState:
    state: str = None


class FakeHass:
    states = {}


def test_get_state():
    hass = FakeHass()
    hass.states["entity_1"] = None
    hass.states["entity_2"] = FakeState()
    hass.states["entity_3"] = FakeState("unknown")
    hass.states["entity_4"] = FakeState("unavailable")
    hass.states["entity_5"] = FakeState("ok")

    assert get_state_or_none_if_unknown(hass, "foo") is None
    assert get_state_or_none_if_unknown(hass, "entity_1") is None
    assert get_state_or_none_if_unknown(hass, "entity_2") is None
    assert get_state_or_none_if_unknown(hass, "entity_3") is None
    assert get_state_or_none_if_unknown(hass, "entity_4") is None
    assert get_state_or_none_if_unknown(hass, "entity_5") == "ok"


def test_midnight():
    assert midnight_to_end_of_day(time.min) == time.max
    assert midnight_to_end_of_day(time(hour=0, minute=0)) == time.max
    assert midnight_to_end_of_day(time(hour=0, minute=1)) == time(0, 1)
    assert midnight_to_end_of_day(time(hour=23, minute=0)) == time(23, 0)
    assert midnight_to_end_of_day(time(hour=23, minute=59)) == time(23, 59)
    assert midnight_to_end_of_day(time.max) == time.max


def test_midnight_with_tz():
    assert midnight_to_end_of_day(time(hour=0, minute=0, tzinfo=UTC)) == time.max.replace(tzinfo=UTC)
    assert midnight_to_end_of_day(time(hour=0, minute=1, tzinfo=UTC)) == time(0, 1, tzinfo=UTC)
    assert midnight_to_end_of_day(time(hour=23, minute=0, tzinfo=UTC)) == time(23, 0, tzinfo=UTC)
    assert midnight_to_end_of_day(time(hour=23, minute=59, tzinfo=UTC)) == time(23, 59, tzinfo=UTC)
