import logging
from datetime import datetime, timedelta

from homeassistant.core import State

from custom_components.automated_cover_control.config import (
    CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT,
)
from custom_components.automated_cover_control.log_context_adapter import (
    LogContextAdapter,
)
from custom_components.automated_cover_control.manual_override_manager import (
    ManualOverrideManager,
)


def test_manual_overrides_disabled():
    logger = LogContextAdapter(logging.getLogger(__name__))
    manager = ManualOverrideManager(logger)
    manager.update_config({})
    manager.disable_detection()

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 22},
    )
    manager.handle_state_change("cover.foo", state, 44)

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0


def test_manual_overrides_enabled():
    logger = LogContextAdapter(logging.getLogger(__name__))
    manager = ManualOverrideManager(logger)
    manager.update_config({})
    manager.enable_detection()

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0

    # State change with no position difference
    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 22},
    )
    manager.handle_state_change("cover.foo", state, 22)

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 22},
    )
    manager.handle_state_change("cover.foo", state, 44)

    assert manager.is_any_cover_under_manual_control()
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]
    assert manager.is_cover_manual("cover.foo")

    manager.clear_all()

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 22},
    )
    manager.handle_state_change("cover.foo", state, 44)

    assert manager.is_any_cover_under_manual_control()
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]
    assert manager.is_cover_manual("cover.foo")

    manager.disable_detection()

    state = State(
        entity_id="cover.bar",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 22},
    )
    manager.handle_state_change("cover.bar", state, 44)

    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    manager.clear_all()

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 22},
    )
    manager.handle_state_change("cover.foo", state, 44)

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0


def test_manual_overrides_detection_threshold():
    logger = LogContextAdapter(logging.getLogger(__name__))
    manager = ManualOverrideManager(logger)
    manager.update_config({CONF_MANUAL_OVERRIDE_DETECTION_THRESHOLD: 20})
    manager.enable_detection()

    # State change with position difference under threshold
    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 32},
    )
    manager.handle_state_change("cover.foo", state, 22)

    assert not manager.is_any_cover_under_manual_control()
    assert len(manager.covers_under_manual_control()) == 0

    # State change with position difference over threshold
    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=datetime.now(),
        attributes={"current_position": 55},
    )
    manager.handle_state_change("cover.foo", state, 22)

    assert manager.is_any_cover_under_manual_control()
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]
    assert manager.is_cover_manual("cover.foo")


def test_manual_overrides_rearm_disabled():
    logger = LogContextAdapter(logging.getLogger(__name__))
    manager = ManualOverrideManager(logger)
    manager.update_config(
        {
            CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: False,
            CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 60},
        }
    )
    manager.enable_detection()

    first_event_time = datetime.now()

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=first_event_time,
        attributes={"current_position": 33},
    )
    manager.handle_state_change("cover.foo", state, 22)
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    manager.reset_expired_overrides(now=first_event_time + timedelta(minutes=30))
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=first_event_time + timedelta(minutes=30),
        attributes={"current_position": 33},
    )
    manager.handle_state_change("cover.foo", state, 22)
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    manager.reset_expired_overrides(now=first_event_time + timedelta(minutes=61))
    assert len(manager.covers_under_manual_control()) == 0


def test_manual_overrides_rearm_enabled():
    logger = LogContextAdapter(logging.getLogger(__name__))
    manager = ManualOverrideManager(logger)
    manager.update_config(
        {
            CONF_MANUAL_OVERRIDE_RESET_TIMER_AT_EACH_ADJUSTMENT: True,
            CONF_MANUAL_OVERRIDE_DURATION: {"minutes": 60},
        }
    )
    manager.enable_detection()

    first_event_time = datetime.now()

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=first_event_time,
        attributes={"current_position": 33},
    )
    manager.handle_state_change("cover.foo", state, 22)
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    manager.reset_expired_overrides(now=first_event_time + timedelta(minutes=30))
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    state = State(
        entity_id="cover.foo",
        state=None,
        last_updated=first_event_time + timedelta(minutes=30),
        attributes={"current_position": 33},
    )
    manager.handle_state_change("cover.foo", state, 22)
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    manager.reset_expired_overrides(now=first_event_time + timedelta(minutes=61))
    assert list(manager.covers_under_manual_control()) == ["cover.foo"]

    manager.reset_expired_overrides(now=first_event_time + timedelta(minutes=91))
    assert len(manager.covers_under_manual_control()) == 0
