"""Google Maps building photos for Davao offices.

Each record is the picture of the building at that office's Google Maps pin.
Street View is used when it faces the building. A few pins open onto a
neighbor or a blank side wall, so those use the front photo from the same
Google Maps place listing instead.
"""

from __future__ import annotations

VERIFIED_OFFICES: dict[str, dict[str, str]] = {
    "LGU-DAVAO-OFF-602BAC52": {
        "latitude": "7.0643071",
        "longitude": "125.6090848",
        "maps_url": "https://www.google.com/maps/place/Sangguniang+Panlungsod+ng+Dabaw/@7.0643071,125.6090848,17z",
        "image_path": "data/raw/office_images/davao/LGU-DAVAO-OFF-602BAC52.jpg",
        "image_kind": "google_maps_place_photo",
    },
    "COMELEC-OFF-B776FC43": {
        "latitude": "7.0643071",
        "longitude": "125.6090848",
        "maps_url": "https://www.google.com/maps/place/Sangguniang+Panlungsod+ng+Dabaw/@7.0643071,125.6090848,17z",
        "image_path": "data/raw/office_images/davao/COMELEC-OFF-B776FC43.jpg",
        "image_kind": "google_maps_place_photo",
    },
    "PSA-OFF-C96C1839": {
        "latitude": "7.0941587",
        "longitude": "125.6212431",
        "maps_url": "https://www.google.com/maps/place/Philippine+Statistics+Authority,+PSA,+Region+11/@7.0941587,125.6212431,17z",
        "image_path": "data/raw/office_images/davao/PSA-OFF-C96C1839.jpg",
        "image_kind": "google_maps_street_view",
    },
    "LTO-OFF-6BA7E79C": {
        "latitude": "7.0509318",
        "longitude": "125.5877093",
        "maps_url": "https://www.google.com/maps/place/LTO+MVIS/@7.0509318,125.5877093,17z",
        "image_path": "data/raw/office_images/davao/LTO-OFF-6BA7E79C.jpg",
        "image_kind": "google_maps_street_view",
    },
    "SSS-OFF-C06CA6B3": {
        "latitude": "7.0977379",
        "longitude": "125.6181772",
        "maps_url": "https://www.google.com/maps/place/Social+Security+System+-+Davao+Branch/@7.0977379,125.6181772,17z",
        "image_path": "data/raw/office_images/davao/SSS-OFF-C06CA6B3.jpg",
        "image_kind": "google_maps_place_photo",
    },
    "PHILSYS-OFF-57B80507": {
        "latitude": "7.0506083",
        "longitude": "125.5882523",
        "maps_url": "https://www.google.com/maps/place/SM+City+Davao/@7.0506083,125.5882523,17z",
        "image_path": "data/raw/office_images/davao/PHILSYS-OFF-57B80507.jpg",
        "image_kind": "google_maps_street_view",
    },
    "DFA-OFF-FFC2C19A": {
        "latitude": "7.0506083",
        "longitude": "125.5882523",
        "maps_url": "https://www.google.com/maps/place/SM+City+Davao/@7.0506083,125.5882523,17z",
        "image_path": "data/raw/office_images/davao/DFA-OFF-FFC2C19A.jpg",
        "image_kind": "google_maps_street_view",
    },
    "NBI-OFF-01374019": {
        "latitude": "7.0862278",
        "longitude": "125.6107523",
        "maps_url": "https://www.google.com/maps/place/National+Bureau+of+Investigation+XI+-+SEMRO/@7.0862278,125.6107523,17z",
        "image_path": "data/raw/office_images/davao/NBI-OFF-01374019.jpg",
        "image_kind": "google_maps_street_view",
    },
    "NBI-OFF-B558C709": {
        "latitude": "7.0778200",
        "longitude": "125.6141300",
        "maps_url": "https://www.google.com/maps/search/Gaisano+Mall+of+Davao/@7.07782,125.61413,17z",
        "image_path": "data/raw/office_images/davao/NBI-OFF-B558C709.jpg",
        "image_kind": "google_maps_place_photo",
    },
    "PHILHEALTH-OFF-65B92ADA": {
        "latitude": "7.0778200",
        "longitude": "125.6141300",
        "maps_url": "https://www.google.com/maps/search/Gaisano+Mall+of+Davao/@7.07782,125.61413,17z",
        "image_path": "data/raw/office_images/davao/PHILHEALTH-OFF-65B92ADA.jpg",
        "image_kind": "google_maps_place_photo",
    },
    "PRC-OFF-0832FC0C": {
        "latitude": "7.0535534",
        "longitude": "125.5914294",
        "maps_url": "https://www.google.com/maps/place/Professional+Regulation+Commission+Region+XI/@7.0535534,125.5914294,17z",
        "image_path": "data/raw/office_images/davao/PRC-OFF-0832FC0C.jpg",
        "image_kind": "google_maps_street_view",
    },
    "PHILHEALTH-OFF-1EB16BDF": {
        "latitude": "7.0624590",
        "longitude": "125.6077500",
        "maps_url": "https://www.google.com/maps/place/PhilHealth+Regional+Office+XI/@7.062459,125.60775,17z",
        "image_path": "data/raw/office_images/davao/PHILHEALTH-OFF-1EB16BDF.jpg",
        "image_kind": "google_maps_street_view",
    },
    "PHILHEALTH-OFF-E23E5367": {
        "latitude": "7.0624590",
        "longitude": "125.6077500",
        "maps_url": "https://www.google.com/maps/place/PhilHealth+Regional+Office+XI/@7.062459,125.60775,17z",
        "image_path": "data/raw/office_images/davao/PHILHEALTH-OFF-E23E5367.jpg",
        "image_kind": "google_maps_street_view",
    },
    "PHILHEALTH-OFF-C270317A": {
        "latitude": "7.1892323",
        "longitude": "125.4522447",
        "maps_url": "https://www.google.com/maps/place/Calinan+Proper+Barangay+Hall/@7.1892323,125.4522447,17z",
        "image_path": "data/raw/office_images/davao/PHILHEALTH-OFF-C270317A.jpg",
        "image_kind": "google_maps_street_view",
    },
    "PHILHEALTH-OFF-D89ACA15": {
        "latitude": "7.0198198",
        "longitude": "125.4973253",
        "maps_url": "https://www.google.com/maps/place/Toril+Health+Center/@7.0198198,125.4973253,17z",
        "image_path": "data/raw/office_images/davao/PHILHEALTH-OFF-D89ACA15.jpg",
        "image_kind": "google_maps_street_view",
    },
    "DTI-OFF-D11D9798": {
        "latitude": "7.0755035",
        "longitude": "125.6194165",
        "maps_url": "https://www.google.com/maps/place/Department+of+Trade+and+Industry+-+Region+11/@7.0755035,125.6194165,17z",
        "image_path": "data/raw/office_images/davao/DTI-OFF-D11D9798.jpg",
        "image_kind": "google_maps_street_view",
    },
}


def verified_office(office_id: str) -> dict[str, str] | None:
    record = VERIFIED_OFFICES.get(office_id)
    return dict(record) if record else None
