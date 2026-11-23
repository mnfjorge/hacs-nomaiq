"""Read-only contact sensors for NomaIQ."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def contact_state(value: object) -> bool | None:
    """Decode Ayla boolean values without treating unknown data as closed."""
    if isinstance(value, bool):
        return value
    if type(value) is int and value in (0, 1):
        return value == 1
    return None


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up supported door/window contacts."""
    coordinator = entry.runtime_data
    async_add_entities(
        NomaIQContactSensor(coordinator, device)
        for device in coordinator.data
        if device.oem_model_number == "doorwin"
    )


class NomaIQContactSensor(CoordinatorEntity, BinarySensorEntity):
    """A door/window contact; no device commands are exposed."""

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator)
        self._serial = device.serial_number
        self._attr_unique_id = f"nomaiq_contact_{self._serial}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=device.name,
            manufacturer="NOMA iQ",
            model=device.oem_model_number,
        )

    @property
    def is_on(self) -> bool | None:
        device = next(
            (d for d in self.coordinator.data if d.serial_number == self._serial),
            None,
        )
        if device is None:
            return None
        prop = device.properties_full.get("alarm_status", {})
        return contact_state(prop.get("value"))
