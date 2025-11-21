"""Shared ticket entry type constants and helpers."""

ENTRY_TYPE_TIME = "time"
ENTRY_TYPE_HARDWARE = "hardware"
ENTRY_TYPE_DEPLOYMENT_FLAT_RATE = "deployment_flat_rate"
ENTRY_TYPE_SOFTWARE = "software"
ENTRY_TYPE_COMPONENT = "component"
ENTRY_TYPE_ACCESSORY = "accessory"

ENTRY_TYPE_CHOICES = (
    ENTRY_TYPE_TIME,
    ENTRY_TYPE_HARDWARE,
    ENTRY_TYPE_DEPLOYMENT_FLAT_RATE,
    ENTRY_TYPE_SOFTWARE,
    ENTRY_TYPE_COMPONENT,
    ENTRY_TYPE_ACCESSORY,
)

# These entry types behave like hardware items (no time math, unit price x quantity).
HARDWARE_LIKE_ENTRY_TYPES = {
    ENTRY_TYPE_HARDWARE,
    ENTRY_TYPE_SOFTWARE,
    ENTRY_TYPE_COMPONENT,
    ENTRY_TYPE_ACCESSORY,
}


def normalize_entry_type(value: str | None) -> str:
    """Return a lowercase entry_type with a safe default."""

    return (value or ENTRY_TYPE_TIME).strip().lower()


__all__ = [
    "ENTRY_TYPE_ACCESSORY",
    "ENTRY_TYPE_CHOICES",
    "ENTRY_TYPE_COMPONENT",
    "ENTRY_TYPE_DEPLOYMENT_FLAT_RATE",
    "ENTRY_TYPE_HARDWARE",
    "ENTRY_TYPE_SOFTWARE",
    "ENTRY_TYPE_TIME",
    "HARDWARE_LIKE_ENTRY_TYPES",
    "normalize_entry_type",
]
