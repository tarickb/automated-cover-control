import enum


class CoverControlReason(enum.StrEnum):
    UNKNOWN = enum.auto()
    AUTOMATION_DISABLED = enum.auto()
    WINDOW_OPEN = enum.auto()
    PRESENCE_NOT_DETECTED = enum.auto()
    LUX_BELOW_THRESHOLD = enum.auto()
    WEATHER_CONDITIONS_NOT_MATCHED = enum.auto()
    SUN_IN_FRONT_OF_WINDOW = enum.auto()
    SUN_NOT_IN_FRONT_OF_WINDOW = enum.auto()
    END_TIME_REACHED = enum.auto()
    UNDER_MANUAL_CONTROL = enum.auto()
    TIME_THRESHOLD_DISALLOWED = enum.auto()
    ALREADY_AT_TARGET = enum.auto()
    OUTSIDE_CONTROL_TIME_RANGE = enum.auto()


class CoverControlTweaks(enum.StrEnum):
    NONE = enum.auto()
    CLIPPED_TO_MIN = enum.auto()
    CLIPPED_TO_MAX = enum.auto()
    SUN_IN_BLIND_SPOT = enum.auto()
    SOLAR_ELEVATION_OUT_OF_RANGE = enum.auto()
    AFTER_SUNSET_OR_BEFORE_SUNRISE = enum.auto()
    CLIPPED_TO_0_100_RANGE = enum.auto()
    INVERTED = enum.auto()
