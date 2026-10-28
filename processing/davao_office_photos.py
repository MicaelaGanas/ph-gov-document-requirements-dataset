"""Official exterior building photos for Davao City government offices.

Only direct image URLs of building facades from .gov.ph sources are listed.
Press-release photos (interiors, mobile units, ceremonies) are intentionally excluded.
When no verified exterior exists on official sites, the office has no photo.
"""

from __future__ import annotations

from typing import TypedDict


class PhotoSource(TypedDict, total=False):
    image_url: str
    source_url: str


# Most-specific rules first. Exterior building photos only.
_PHOTO_RULES: tuple[tuple[dict[str, str], PhotoSource], ...] = (
    (
        {"agency_acronym": "PHILSYS", "name_contains": "SM City"},
        {
            "image_url": (
                "https://tourism.davaocity.gov.ph/wp-content/uploads/2018/10/"
                "SM_City_Davao_Annex_-_panoramio.jpg"
            ),
            "source_url": (
                "https://tourism.davaocity.gov.ph/explore-the-city/shopping/malls/sm-city-davao/"
            ),
        },
    ),
    (
        {"agency_acronym": "LGU-DAVAO"},
        {
            "image_url": (
                "https://sp.davaocity.gov.ph/wp-content/uploads/2020/06/SP-Building-2019.jpg"
            ),
            "source_url": "https://sp.davaocity.gov.ph/?page_id=3113",
        },
    ),
    (
        {"agency_acronym": "COMELEC"},
        {
            "image_url": (
                "https://sp.davaocity.gov.ph/wp-content/uploads/2020/06/SP-Building-2019.jpg"
            ),
            "source_url": "https://sp.davaocity.gov.ph/?page_id=3113",
        },
    ),
)


def resolve_photo_source(office: dict) -> PhotoSource | None:
    """Pick an official exterior building photo, or None if none is verified."""
    acronym = office.get("agency_acronym", "")
    name = office.get("office_name", "").lower()

    for match, source in _PHOTO_RULES:
        if match.get("agency_acronym") and match["agency_acronym"] != acronym:
            continue
        needle = match.get("name_contains", "").lower()
        if needle and needle not in name:
            continue
        return dict(source)
    return None
