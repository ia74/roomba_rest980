"""Bring back the sensor attributes from the YAML config."""

from datetime import datetime

from .const import (
    binMappings,
    cleanBaseMappings,
    cycleMappings,
    errorMappings,
    jobInitiatorMappings,
    mopRanks,
    notReadyMappings,
    padMappings,
    phaseMappings,
    yesNoMappings,
)


def createExtendedAttributes(self) -> dict[str, any]:
    """Return all the given attributes from rest980."""
    data = self.coordinator.data or {}
    status = data.get("cleanMissionStatus", {})
    # Mission State
    cycle = status.get("cycle")
    phase = status.get("phase")
    err = status.get("error")
    notReady = status.get("notReady")
    initiator = status.get("initiator")
    missionStartTime = status.get("mssnStrtTm")
    rechargeTime = status.get("rechrgTm")
    expireTime = status.get("expireTm")
    # Generic Data
    softwareVer = data.get("softwareVer")
    vacuumHigh = data.get("vacHigh")
    carpetBoost = data.get("carpetBoost")
    if vacuumHigh is not None:
        if not vacuumHigh and not carpetBoost:
            robotCarpetBoost = "Eco"
        elif vacuumHigh and not carpetBoost:
            robotCarpetBoost = "Performance"
        else:
            robotCarpetBoost = "Auto"
    else:
        robotCarpetBoost = "n-a"
    battery = data.get("batPct")
    if "+" in softwareVer:
        softwareVer = softwareVer.split("+")[1]
    if cycle == "none" and notReady == 39:
        extv = "Pending"
    elif notReady > 0:
        extv = f"Not Ready ({notReady})"
    else:
        extv = cycleMappings.get(cycle, cycle)
    if phase == "charge" and battery == 100:
        rPhase = "Idle"
    elif cycle == "none" and phase == "stop":
        rPhase = "Stopped"
    else:
        rPhase = phaseMappings.get(phase, phase)
    if missionStartTime != 0:
        time = datetime.fromtimestamp(missionStartTime)
        elapsed = round((datetime.now().timestamp() - time.timestamp()) / 60)
        if elapsed > 60:
            jobTime = f"{elapsed // 60}h {f'{elapsed % 60:0>2d}'}m"
        else:
            jobTime = f"{elapsed}m"
    else:
        jobTime = "n-a"
    if rechargeTime != 0:
        time = datetime.fromtimestamp(rechargeTime)
        resume = round((datetime.now().timestamp() - time.timestamp()) / 60)
        if elapsed > 60:
            jobResumeTime = f"{resume // 60}h {f'{resume % 60:0>2d}'}m"
        else:
            jobResumeTime = f"{resume}m"
    else:
        jobResumeTime = "n-a"
    if expireTime != 0:
        time = datetime.fromtimestamp(expireTime)
        expire = round((datetime.now().timestamp() - time.timestamp()) / 60)
        if elapsed > 60:
            jobExpireTime = f"{expire // 60}h {f'{expire % 60:0>2d}'}m"
        else:
            jobExpireTime = f"{expire}m"
    else:
        jobExpireTime = "n-a"
    # Bin
    robotBin = data.get("bin", {"full": False, "present": False})
    binFull = robotBin.get("full")
    binPresent = robotBin.get("present")
    # Dock
    dock = data.get("dock")
    dockState = dock.get("state")
    # Pose
    ## NOTE: My roomba's firmware does not support this anymore, so I'm blindly guessing based on the previous YAML integration details.
    pose = data.get("pose") or {}
    theta = pose.get("theta")
    point = pose.get("point") or {}
    pointX = point.get("x")
    pointY = point.get("y")
    if theta is not None:
        location = f"{pointX}, {pointY}, {theta}"
    else:
        location = "n-a"
    # Networking
    signal = data.get("signal")
    rssi = signal.get("rssi")
    # Runtime Statistics
    runtimeStats = data.get("runtimeStats")
    sqft = runtimeStats.get("sqft")
    hr = runtimeStats.get("hr")
    timeMin = runtimeStats.get("min")
    # Mission total(s?)
    bbmssn = data.get("bbmssn")
    numMissions = bbmssn.get("nMssn")
    # Run total(s?)
    bbrun = data.get("bbrun")
    numDirt = bbrun.get("nScrubs")
    numEvacs = bbrun.get("nEvacs")
    # numEvacs only for I7+/S9+ Models (Clean Base)
    pmaps = data.get("pmaps", [])
    pmap0id = next(iter(pmaps[0]), None) if pmaps else None
    noAutoPasses = data.get("noAutoPasses")
    twoPass = data.get("twoPass")
    if noAutoPasses is not None and twoPass is not None:
        if noAutoPasses is True and twoPass is False:
            robotCleanMode = "One"
        elif noAutoPasses is True and twoPass is True:
            robotCleanMode = "Two"
        else:
            robotCleanMode = "Auto"
    else:
        robotCleanMode = "n-a"

    robotObject = {
        "extendedStatus": extv,
        "notready_msg": notReadyMappings.get(notReady, notReady),
        "error_msg": errorMappings.get(err, err),
        "battery": f"{battery}%",
        "software_ver": softwareVer,
        "phase": rPhase,
        "bin": binMappings.get(binFull, binFull),
        "bin_present": yesNoMappings.get(binPresent, binPresent),
        "clean_base": cleanBaseMappings.get(dockState, dockState),
        "location": location,
        "rssi": rssi,
        "total_area": f"{round(sqft / 10.764 * 100)}m²",
        "total_time": f"{hr}h {timeMin}m",
        "total_jobs": numMissions,
        "dirt_events": numDirt,
        "evac_events": numEvacs,
        "job_initiator": jobInitiatorMappings.get(initiator, initiator),
        "job_time": jobTime,
        "job_recharge": jobResumeTime,
        "job_expire": jobExpireTime,
        "clean_mode": robotCleanMode,
        "carpet_boost": robotCarpetBoost,
        "clean_edges": "true" if not data.get("openOnly", False) else "false",
        "maint_due": False,
        "pmap0_id": pmap0id,
    }

    if data.get("padWetness"):
        # It's a mop
        # TODO: Make sure this works! I don't own a mop, so I'm just re-using what jeremywillans has written.
        pad = data.get("padWetness", {})
        if isinstance(pad, dict):
            # priority: disposable > reusable
            if "disposable" in pad:
                robotCleanMode = pad["disposable"]
            elif "reusable" in pad:
                robotCleanMode = pad["reusable"]
            else:
                robotCleanMode = 0
        else:
            robotCleanMode = pad
        mopRankOverlap = data.get("rankOverlap")
        if not mopRankOverlap:
            robotObject["mop_behavior"] = "n-a"
        else:
            robotObject["mop_behavior"] = mopRanks.get(mopRankOverlap, mopRankOverlap)
        detectedPad = data.get("detectedPad")
        tankPresent = data.get("tankPresent")
        lidOpen = data.get("lidOpen")
        if detectedPad:
            robotObject["pad"] = padMappings.get(detectedPad)
        if tankPresent:
            if notReady == 31:  # Fill Tank
                robotObject["tank"] = "Fill Tank"
            elif not lidOpen:
                robotObject["tank"] = "Ready"
            elif lidOpen:
                robotObject["tank"] = "Lid Open"
        else:
            robotObject["tank"] = "Tank Missing"

    return robotObject
