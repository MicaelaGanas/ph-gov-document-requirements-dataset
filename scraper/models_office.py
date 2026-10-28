"""Government office location record."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from processing.schemas import GOVERNMENT_OFFICES_COLUMNS
from processing.id_utils import make_office_id


@dataclass
class GovernmentOfficeRecord:
    agency: str
    agency_acronym: str
    office_name: str
    address: str
    source_url: str
    office_type: str = "service_center"
    region: str = ""
    province: str = ""
    city: str = "Davao City"
    municipality: str = ""
    barangay: str = ""
    latitude: str = ""
    longitude: str = ""
    contact_number: str = ""
    email: str = ""
    official_url: str = ""
    operating_hours: str = ""
    services_offered: str = ""
    office_image_url: str = ""
    office_image_path: str = ""
    office_image_source: str = ""
    geocode_source: str = ""
    geocode_status: str = ""
    last_verified: str = field(default_factory=lambda: date.today().isoformat())
    office_id: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if not self.office_id:
            self.office_id = make_office_id(
                self.agency_acronym, self.office_name, self.address
            )

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        return {col: row.get(col, "") for col in GOVERNMENT_OFFICES_COLUMNS}
