"""Base entity for Diyanet Prayer Times."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from . import i18n
from .const import DOMAIN
from .coordinator import DiyanetCoordinator


class DiyanetEntity(CoordinatorEntity[DiyanetCoordinator]):
    """Entity attached to one service device per city.

    Names come from the integration's own language setting rather than
    Home Assistant's, so they are set directly instead of via translations.
    Entity IDs are language-independent: <platform>.<device>_<object_id>.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DiyanetCoordinator,
        platform: str,
        key: str,
        object_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}_{object_id}"
        # Same prefix Home Assistant derives from the device name.
        self.entity_id = f"{platform}.{slugify(entry.title)}_{object_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Diyanet İşleri Başkanlığı",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def name(self) -> str:
        """Return the name in the integration's language."""
        return i18n.name(self._key, self.coordinator.language)
