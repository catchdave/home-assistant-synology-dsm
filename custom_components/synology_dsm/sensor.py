"""Support for Synology DSM sensors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from typing import Any

from synology_dsm.api.core.utilization import SynoCoreUtilization
from synology_dsm.api.dsm.information import SynoDSMInformation
from synology_dsm.api.storage.storage import SynoStorage

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DATA_MEGABYTES,
    DATA_RATE_KILOBYTES_PER_SECOND,
    DATA_TERABYTES,
    PERCENTAGE,
    TEMP_CELSIUS,
    DATA_GIGABYTES,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import utcnow

from . import SynoApi
from .const import CONF_VOLUMES, DOMAIN, ENTITY_UNIT_LOAD, CONF_TASKS, CONF_DISKS
from .entity import (
    SynologyDSMBaseEntity,
    SynologyDSMDeviceEntity,
    SynologyDSMEntityDescription,
    SynologyDSMBackupTaskEntity,
)
from .models import SynologyDSMData
from .py_synologydsm_api_aux.backup.backup import SynoBackup


@dataclass
class SynologyDSMSensorEntityDescription(
    SensorEntityDescription, SynologyDSMEntityDescription
):
    """Describes Synology DSM sensor entity."""


UTILISATION_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_other_load",
        name="CPU Utilization (Other)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_user_load",
        name="CPU Utilization (User)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_system_load",
        name="CPU Utilization (System)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_total_load",
        name="CPU Utilization (Total)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_1min_load",
        name="CPU Load Average (1 min)",
        native_unit_of_measurement=ENTITY_UNIT_LOAD,
        icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_5min_load",
        name="CPU Load Average (5 min)",
        native_unit_of_measurement=ENTITY_UNIT_LOAD,
        icon="mdi:chip",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_15min_load",
        name="CPU Load Average (15 min)",
        native_unit_of_measurement=ENTITY_UNIT_LOAD,
        icon="mdi:chip",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_real_usage",
        name="Memory Usage (Real)",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_size",
        name="Memory Size",
        native_unit_of_measurement=DATA_MEGABYTES,
        icon="mdi:memory",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_cached",
        name="Memory Cached",
        native_unit_of_measurement=DATA_MEGABYTES,
        icon="mdi:memory",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_available_swap",
        name="Memory Available (Swap)",
        native_unit_of_measurement=DATA_MEGABYTES,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_available_real",
        name="Memory Available (Real)",
        native_unit_of_measurement=DATA_MEGABYTES,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_total_swap",
        name="Memory Total (Swap)",
        native_unit_of_measurement=DATA_MEGABYTES,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_total_real",
        name="Memory Total (Real)",
        native_unit_of_measurement=DATA_MEGABYTES,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="network_up",
        name="Upload Throughput",
        native_unit_of_measurement=DATA_RATE_KILOBYTES_PER_SECOND,
        icon="mdi:upload",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="network_down",
        name="Download Throughput",
        native_unit_of_measurement=DATA_RATE_KILOBYTES_PER_SECOND,
        icon="mdi:download",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
STORAGE_VOL_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_status",
        name="Status",
        icon="mdi:checkbox-marked-circle-outline",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_size_total",
        name="Total Size",
        native_unit_of_measurement=DATA_TERABYTES,
        icon="mdi:chart-pie",
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_size_used",
        name="Used Space",
        native_unit_of_measurement=DATA_TERABYTES,
        icon="mdi:chart-pie",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_percentage_used",
        name="Volume Used",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:chart-pie",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_disk_temp_avg",
        name="Average Disk Temp",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_disk_temp_max",
        name="Maximum Disk Temp",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)
STORAGE_DISK_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_smart_status",
        name="Status (Smart)",
        icon="mdi:checkbox-marked-circle-outline",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_status",
        name="Status",
        icon="mdi:checkbox-marked-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_temp",
        name="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

INFORMATION_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoDSMInformation.API_KEY,
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoDSMInformation.API_KEY,
        key="uptime",
        name="Last Boot",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

HYPER_BACKUP_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="used_size",
        name="Target Current Size",
        native_unit_of_measurement=DATA_GIGABYTES,
        icon="mdi:chart-pie",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="is_backing_up",
        name="Currently Backing Up",
        icon="mdi:backup-restore",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="used_size",
        name="Backup Progress",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:progress-upload",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="status",
        name="Status",
        icon="mdi:checkbox-marked-circle-outline",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="health",
        name="Health",
        icon="mdi:hospital-box-outline",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="previous_backup_time",
        name="Most Recent Backup",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:backburger",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="next_backup_time",
        name="Next Scheduled Backup",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:forwardburger",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="previous_result",
        name="Most Recent Result",
        icon="mdi:history",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="previous_error",
        name="Most Recent Error",
        icon="mdi:alert-circle-outline",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="state",
        name="Task State (raw)",
        entity_registry_enabled_default=False,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="raw_status",
        name="Status (raw)",
        entity_registry_enabled_default=False,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoBackup.API_KEY,
        key="has_schedule",
        name="Schedule Enabled",
        icon="mdi:calendar-clock",
        entity_registry_enabled_default=False,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Synology NAS Sensor."""
    data: SynologyDSMData = hass.data[DOMAIN][entry.unique_id]
    api = data.api
    coordinator = data.coordinator_central

    entities: list[SynoDSMUtilSensor | SynoDSMStorageSensor | SynoDSMInfoSensor | SynoDSMHyperBackupSensor] = [
        SynoDSMUtilSensor(api, coordinator, description)
        for description in UTILISATION_SENSORS
    ]

    # Handle all volumes
    if api.storage.volumes_ids:
        entities.extend(
            [
                SynoDSMStorageSensor(api, coordinator, description, volume)
                for volume in entry.data.get(CONF_VOLUMES, api.storage.volumes_ids)
                for description in STORAGE_VOL_SENSORS
            ]
        )

    # Handle all disks
    if api.storage.disks_ids:
        entities.extend(
            [
                SynoDSMStorageSensor(api, coordinator, description, disk)
                for disk in entry.data.get(CONF_DISKS, api.storage.disks_ids)
                for description in STORAGE_DISK_SENSORS
            ]
        )

    # Handle all hyper backup tasks
    if api.hyper_backup.task_ids:
        entities.extend(
            [
                SynoDSMHyperBackupSensor(api, coordinator, description, task)
                for task in entry.data.get(CONF_TASKS, api.hyper_backup.task_ids)
                for description in HYPER_BACKUP_SENSORS
            ]
        )

    entities.extend(
        [
            SynoDSMInfoSensor(api, coordinator, description)
            for description in INFORMATION_SENSORS
        ]
    )

    async_add_entities(entities)


class SynoDSMSensor(SynologyDSMBaseEntity, SensorEntity):
    """Mixin for sensor specific attributes."""

    entity_description: SynologyDSMSensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: DataUpdateCoordinator[dict[str, dict[str, Any]]],
        description: SynologyDSMSensorEntityDescription,
    ) -> None:
        """Initialize the Synology DSM sensor entity."""
        super().__init__(api, coordinator, description)


class SynoDSMUtilSensor(SynoDSMSensor):
    """Representation a Synology Utilisation sensor."""

    @property
    def native_value(self) -> Any | None:
        """Return the state."""
        attr = getattr(self._api.utilisation, self.entity_description.key)
        if callable(attr):
            attr = attr()
        if attr is None:
            return None

        # Data (RAM)
        if self.native_unit_of_measurement == DATA_MEGABYTES:
            return round(attr / 1024.0**2, 1)

        # Network
        if self.native_unit_of_measurement == DATA_RATE_KILOBYTES_PER_SECOND:
            return round(attr / 1024.0, 1)

        # CPU load average
        if self.native_unit_of_measurement == ENTITY_UNIT_LOAD:
            return round(attr / 100, 2)

        return attr

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self._api.utilisation)


class SynoDSMStorageSensor(SynologyDSMDeviceEntity, SynoDSMSensor):
    """Representation a Synology Storage sensor."""

    entity_description: SynologyDSMSensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: DataUpdateCoordinator[dict[str, dict[str, Any]]],
        description: SynologyDSMSensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the Synology DSM storage sensor entity."""
        super().__init__(api, coordinator, description, device_id)

    @property
    def native_value(self) -> Any | None:
        """Return the state."""
        attr = getattr(self._api.storage, self.entity_description.key)(self._device_id)
        if attr is None:
            return None

        # Data (disk space)
        if self.native_unit_of_measurement == DATA_TERABYTES:
            return round(attr / 1024.0**4, 2)

        return attr

class SynoDSMHyperBackupSensor(SynologyDSMBackupTaskEntity, SynoDSMSensor):
    """Representation a Synology HyperBackup sensor."""

    entity_description: SynologyDSMSensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: DataUpdateCoordinator[dict[str, dict[str, Any]]],
        description: SynologyDSMSensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the Synology DSM HyperBackup sensor entity."""
        super().__init__(api, coordinator, description, device_id)

    @property
    def native_value(self) -> Any | None:
        """Return the state."""
        attr = getattr(self._api.hyper_backup, self.entity_description.key)(self._device_id)
        if attr is None:
            return None

        # Add timezone to datetime objects
        # TODO: Parse `self._api.system.time_zone` to timezones. E.g. "(GMT-08:00) Pacific Time (US & Canada); Tijuana"
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            if attr.tzinfo is None:
                attr = attr.replace(tzinfo=datetime.now(timezone.utc).astimezone().tzinfo)

        if self.native_unit_of_measurement == DATA_GIGABYTES:
            return round(attr / 1024.0 ** 2, 1)

        return attr


class SynoDSMInfoSensor(SynoDSMSensor):
    """Representation a Synology information sensor."""

    def __init__(
        self,
        api: SynoApi,
        coordinator: DataUpdateCoordinator[dict[str, dict[str, Any]]],
        description: SynologyDSMSensorEntityDescription,
    ) -> None:
        """Initialize the Synology SynoDSMInfoSensor entity."""
        super().__init__(api, coordinator, description)
        self._previous_uptime: str | None = None
        self._last_boot: datetime | None = None

    @property
    def native_value(self) -> Any | None:
        """Return the state."""
        attr = getattr(self._api.information, self.entity_description.key)
        if attr is None:
            return None

        if self.entity_description.key == "uptime":
            # reboot happened or entity creation
            if self._previous_uptime is None or self._previous_uptime > attr:
                self._last_boot = utcnow() - timedelta(seconds=attr)

            self._previous_uptime = attr
            return self._last_boot
        return attr
