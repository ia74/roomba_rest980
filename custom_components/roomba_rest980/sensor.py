"""Create sensors that poll Roomba's data."""

import logging

from .sensors.vacuum import *
from .sensors.mop import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create the sensors needed to poll Roomba's data."""
    coordinator = entry.runtime_data.local_coordinator
    cloudCoordinator = entry.runtime_data.cloud_coordinator
    async_add_entities(
        [
            RoombaAttributes(coordinator, entry),
            RoombaBatterySensor(coordinator, entry),
            RoombaBinSensor(coordinator, entry),
            RoombaJobInitiator(coordinator, entry),
            RoombaPhase(coordinator, entry),
            RoombaTotalArea(coordinator, entry),
            RoombaTotalTime(coordinator, entry),
            RoombaCleanBase(coordinator, entry),
            RoombaTotalJobs(coordinator, entry),
            RoombaMissionStartTime(coordinator, entry),
            RoombaMissionElapsedTime(coordinator, entry),
            RoombaRechargeTime(coordinator, entry),
            RoombaMissionExpireTime(coordinator, entry),
            RoombaCarpetBoostMode(coordinator, entry),
            RoombaCleanEdges(coordinator, entry),
            RoombaCleanMode(coordinator, entry),
            RoombaNotReady(coordinator, entry),
            RoombaError(coordinator, entry),
            RoombaIP(coordinator, entry),
            RoombaRSSI(coordinator, entry),
            RoombaNetworkNoise(coordinator, entry),
            RoombaSNR(coordinator, entry),
            RoombaCloudAttributes(cloudCoordinator, entry),
            MopCleanMode(coordinator, entry),
            MopBehavior(coordinator, entry),
            MopPad(coordinator, entry),
            MopTank(coordinator, entry),
            MopTankLevel(coordinator, entry),
        ],
        update_before_add=True,
    )

    # Create cloud pmap entities if cloud data is available
    cloud_entities = []
    if cloudCoordinator and cloudCoordinator.data:
        blid = entry.runtime_data.robot_blid
        # Get cloud data for the specific robot
        if blid in cloudCoordinator.data:
            cloud_data = cloudCoordinator.data[blid]
            # Create pmap entities from cloud data
            if "pmaps" in cloud_data:
                for pmap in cloud_data["pmaps"]:
                    try:
                        cloud_entities.append(
                            RoombaCloudPmap(cloudCoordinator, entry, pmap)
                        )
                    except (KeyError, TypeError) as e:
                        _LOGGER.warning(
                            "Failed to create pmap entity for %s: %s",
                            pmap.get("pmap_id", "unknown"),
                            e,
                        )
    if cloud_entities:
        async_add_entities(cloud_entities)

