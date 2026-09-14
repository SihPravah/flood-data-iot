from dataclasses import dataclass

from pravaha_data.models.observation import Location


class CatchmentAssignmentError(LookupError):
    pass


@dataclass(frozen=True)
class BoundingBoxCatchment:
    catchment_id: str
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    provenance: str = "ESTIMATED"

    def contains(self, location: Location) -> bool:
        return (
            self.min_latitude <= location.latitude <= self.max_latitude
            and self.min_longitude <= location.longitude <= self.max_longitude
        )


class DemoCatchmentAssigner:
    """
    Replaceable MVP catchment assignment.

    The demo mapping is explicit and estimated; it is not municipal
    truth and can later be replaced by a GIS polygon assigner.
    """

    def __init__(self, catchments: tuple[BoundingBoxCatchment, ...]):
        if not catchments:
            raise ValueError("At least one catchment mapping is required.")
        self._catchments = catchments

    @classmethod
    def dehradun_demo(cls) -> "DemoCatchmentAssigner":
        return cls(
            (
                BoundingBoxCatchment(
                    catchment_id="UK-CHM-DEHRADUN-01",
                    min_latitude=30.25,
                    max_latitude=30.38,
                    min_longitude=77.96,
                    max_longitude=78.10,
                    provenance="ESTIMATED",
                ),
            )
        )

    def assign(self, location: Location) -> str:
        matches = [
            catchment
            for catchment in self._catchments
            if catchment.contains(location)
        ]

        if not matches:
            raise CatchmentAssignmentError(
                "No configured catchment contains the observation location."
            )

        if len(matches) > 1:
            raise CatchmentAssignmentError(
                "Observation location matched multiple configured catchments."
            )

        return matches[0].catchment_id
