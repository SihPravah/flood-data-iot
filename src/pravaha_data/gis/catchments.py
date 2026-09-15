from dataclasses import dataclass

from pravaha_data.demo.ids import DEMO_CATCHMENT_ID
from pravaha_data.gis.study_area import study_area_bbox
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
        bbox = study_area_bbox()
        return cls(
            (
                BoundingBoxCatchment(
                    catchment_id=DEMO_CATCHMENT_ID,
                    min_latitude=bbox["south"],
                    max_latitude=bbox["north"],
                    min_longitude=bbox["west"],
                    max_longitude=bbox["east"],
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
