"""Constants for the Roomba (Rest980) integration."""

from datetime import timedelta

DOMAIN = "roomba_rest980"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)  # or whatever interval you want

notReadyMappings = {
    0: "n-a",
    2: "Uneven Ground",
    15: "Low Battery",
    31: "Fill Tank",
    39: "Pending",
    48: "Path Blocked",
    68: "Updating Map",
}

## Some mappings thanks to https://github.com/NickWaterton/Roomba980-Python/blob/master/roomba/roomba.py
errorMappings = {
    0: "n-a",
    15: "Reboot Required",
    18: "Docking Issue",
    68: "Updating Map",
    1: "Left wheel off floor",
    2: "Main brushes stuck",
    3: "Right wheel off floor",
    4: "Left wheel stuck",
    5: "Right wheel stuck",
    6: "Stuck near a cliff",
    7: "Left wheel error",
    8: "Bin error",
    9: "Bumper stuck",
    10: "Right wheel error",
    11: "Bin error",
    12: "Cliff sensor issue",
    13: "Both wheels off floor",
    14: "Bin missing",
    16: "Bumped unexpectedly",
    17: "Path blocked",
    19: "Undocking issue",
    20: "Docking issue",
    21: "Navigation problem",
    22: "Navigation problem",
    23: "Battery issue",
    24: "Navigation problem",
    25: "Reboot required",
    26: "Vacuum problem",
    27: "Vacuum problem",
    29: "Software update needed",
    30: "Vacuum problem",
    31: "Reboot required",
    32: "Smart map problem",
    33: "Path blocked",
    34: "Reboot required",
    35: "Unrecognised cleaning pad",
    36: "Bin full",
    37: "Tank needed refilling",
    38: "Vacuum problem",
    39: "Reboot required",
    40: "Navigation problem",
    41: "Timed out",
    42: "Localization problem",
    43: "Navigation problem",
    44: "Pump issue",
    45: "Lid open",
    46: "Low battery",
    47: "Reboot required",
    48: "Path blocked",
    52: "Pad required attention",
    53: "Software update required",
    65: "Hardware problem detected",
    66: "Low memory",
    73: "Pad type changed",
    74: "Max area reached",
    75: "Navigation problem",
    76: "Hardware problem detected",
    88: "Back-up refused",
    89: "Mission runtime too long",
    101: "Battery isn't connected",
    102: "Charging error",
    103: "Charging error",
    104: "No charge current",
    105: "Charging current too low",
    106: "Battery too warm",
    107: "Battery temperature incorrect",
    108: "Battery communication failure",
    109: "Battery error",
    110: "Battery cell imbalance",
    111: "Battery communication failure",
    112: "Invalid charging load",
    114: "Internal battery failure",
    115: "Cell failure during charging",
    116: "Charging error of Home Base",
    118: "Battery communication failure",
    119: "Charging timeout",
    120: "Battery not initialized",
    122: "Charging system error",
    123: "Battery not initialized",
    216: "Charging base bag full",
}

cycleMappings = {
    "clean": "Clean",
    "quick": "Clean (Quick)",
    "spot": "Spot",
    "evac": "Emptying",
    "dock": "Docking",
    "train": "Training",
    "none": "Ready",
}

## Some mappings thanks to https://github.com/NickWaterton/Roomba980-Python/blob/master/roomba/roomba.py
phaseMappings = {
    "new": "New Mission",
    "resume": "Resumed",
    "recharge": "Recharging",
    "completed": "Mission Completed",
    "cancelled": "Cancelled",
    "pause": "Paused",
    "chargingerror": "Base Unplugged",
    "charge": "Charge",
    "run": "Run",
    "evac": "Empty",
    "stop": "Paused",
    "stuck": "Stuck",
    "hmUsrDock": "Sent Home",
    "hmMidMsn": "Docking",
    "hmPostMsn": "Docking - Ending Job",
    "idle": "Idle",  # Added for RoombaPhase
    "stopped": "Stopped",  # Added for RoombaPhase
}

binMappings = {True: "Full", False: "Not Full"}

yesNoMappings = {True: "Yes", False: "No"}

cleanBaseMappings = {
    300: "Ready",
    301: "Ready",
    302: "Empty",
    303: "Empty",
    350: "Bag Missing",
    351: "Clogged",
    352: "Sealing Problem",
    353: "Bag Full",
    360: "IR Comms Problem",
    364: "Bin Full Sensors Not Cleared",
}

jobInitiatorMappings = {
    "schedule": "iRobot Schedule",
    "rmtApp": "iRobot App",
    "manual": "Robot",
    "localApp": "HA",
    "none": "None",  # Added for RoombaJobInitiator
}

mopRanks = {15: "No Mop", 25: "Extended", 67: "Standard", 85: "Deep"}

padMappings = {
    "reusableDry": "Dry",
    "reusableWet": "Wet",
    "dispDry": "Single Dry",
    "dispWet": "Single Wet",
    "invalid": "No Pad",
}

regionTypeMappings = {
    "default": "mdi:map-marker",
    "custom": "mdi:face-agent",
    "basement": "mdi:home-floor-b",
    "bathroom": "mdi:shower",
    "bedroom": "mdi:bed-king",
    "breakfast_room": "mdi:silverware-fork-knief",
    "closet": "mdi:hanger",
    "den": "mdi:sofa-single",
    "dining_room": "mdi:silverware-fork-knife",
    "entryway": "mdi:door-open",
    "family_room": "mdi:sofa-single",
    "foyer": "mdi:door-open",
    "garage": "mdi:garage",
    "guest_bathroom": "mdi:shower",
    "guest_bedroom": "mdi:bed-king",
    "hallway": "mdi:shoe-print",
    "kitchen": "mdi:fridge",
    "kids_room": "mdi:teddy-bear",
    "laundry_room": "mdi:washing-machine",
    "living_room": "mdi:sofa",
    "lounge": "mdi:sofa",
    "media_room": "mdi:television",
    "mud_room": "mdi:landslide",
    "office": "mdi:chair-rolling",
    "outside": "mdi:asterisk",
    "pantry": "mdi:archive",
    "playroom": "mdi:teddy-bear",
    "primary_bathroom": "mdi:shower",
    "primary_bedroom": "mdi:bed-king",
    "recreation_room": "mdi:sofa",
    "storage_room": "mdi:archive",
    "study": "mdi:bookshelf",
    "sun_room": "mdi:sun-angle",
    "unfinished_basement": "mdi:home-floor-b",
    "workshop": "mdi:toolbox",
}

# I need to find more of these!
zoneTypeMappings = {
    "default": "mdi:map-marker",
    "furniture": "mdi:sofa-single",
}
