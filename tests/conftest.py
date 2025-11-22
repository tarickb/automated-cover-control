from datetime import datetime
from unittest.mock import patch

import pytest

from custom_components.automated_cover_control.coordinator import (
    AutomatedCoverControlData,
    AutomatedCoverControlDataUpdateCoordinator,
)
from custom_components.automated_cover_control.why import (
    CoverControlReason,
    CoverControlTweaks,
)


@pytest.fixture()
def return_fake_cover_data():
    with patch.object(AutomatedCoverControlDataUpdateCoordinator, "_async_update_data") as mock_method:
        mock_method.return_value = AutomatedCoverControlData(
            attributes={},
            states={
                "sun_in_window_start": datetime.fromisoformat("2025-01-01T00:00:01Z"),
                "sun_in_window_end": datetime.fromisoformat("2025-01-01T23:59:59Z"),
                "target_position": 66,
                "reason": CoverControlReason.SUN_NOT_IN_FRONT_OF_WINDOW,
                "tweaks": [CoverControlTweaks.AFTER_SUNSET_OR_BEFORE_SUNRISE],
                "manual_override": None,
                "covers_under_manual_control": [],
                "sun_in_front_of_window": None,
            },
        )
        yield mock_method


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
