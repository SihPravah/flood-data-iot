from enum import Enum

class DataStatus(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"
    SIMULATED = "SIMULATED"
    MISSING = "MISSING"

class DataQuality(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    UNUSABLE = "UNUSABLE"
