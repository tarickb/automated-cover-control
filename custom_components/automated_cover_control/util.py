import json
from dataclasses import asdict
from datetime import time
from typing import Any

from homeassistant.core import HomeAssistant


def get_state_or_none_if_unknown(hass: HomeAssistant, entity_id: str):
    state = hass.states.get(entity_id)
    if not state or state.state in ["unknown", "unavailable"]:
        return None
    return state.state


def midnight_to_end_of_day(t: time):
    return time.max.replace(tzinfo=t.tzinfo) if t == time.min.replace(tzinfo=t.tzinfo) else t


def to_json_safe_dict(x: Any):
    x = asdict(x)
    return {key: json.dumps(x[key], default=str) for key in x}
