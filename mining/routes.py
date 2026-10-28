"""Document sequences and Davao office routes for charter-confirmed rules.

Antecedent documents come before consequent documents. The last stop is the
Davao office that receives the application. Documents in the same group are
not ordered against each other. A road leg is drawn only when both offices
already have coordinates. An empty coordinate stays unlocated.
"""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

from mining.charter_check import _rule_roles, _split_docs

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
MINING = ROOT / "output" / "mining"
LOCALITY = "Davao City"
BUILT_ON = "2026-10-29"
RECEIVING_AGENCY = "PRC"

ISSUER = {
    "Certificate of Live Birth (PSA)": (
        "PSA",
        "The Philippine Statistics Authority issues this certificate.",
    ),
    "PSA Marriage Certificate": (
        "PSA",
        "The Philippine Statistics Authority issues this certificate.",
    ),
    "NBI Clearance": (
        "NBI",
        "The National Bureau of Investigation issues this clearance.",
    ),
    "Copy of passport data page or any equivalent document to establish citizenship": (
        "DFA",
        "The Department of Foreign Affairs issues the passport whose data page is copied.",
    ),
    "Transcript of Records (TOR)": (
        "",
        "A school issues the transcript. No school office was collected.",
    ),
    "College Diploma": (
        "",
        "A school issues the diploma. No school office was collected.",
    ),
    "One (1) Certificate of Good Moral Character from any of the following:": (
        "",
        "The page names a barangay, school, church, or employer. None of those issuers is an office in the table.",
    ),
    "Certificate of Good Moral Character to be issued by any of the following: employer, school/college/university or any competent authority acceptable to the Board; and": (
        "",
        "The page names an employer, school, or other authority. None of those issuers is an office in the table.",
    ),
    "Other requirements that the Board may prescribe (e.g. CHED Certificate of equivalency)": (
        "",
        "The page leaves this as a note the board may add. It has no issuing office.",
    ),
}

OSRM_SERVERS = (
    "https://router.project-osrm.org",
    "https://routing.openstreetmap.de/routed-car",
)


def build_routes(mining_dir: Path = MINING, final_dir: Path = FINAL) -> Path:
    offices = _read_csv(final_dir / "government_offices.csv")
    services = {
        row["service_id"]: row
        for row in _read_csv(final_dir / "government_services.csv")
    }
    baskets: dict[str, set[str]] = defaultdict(set)
    for row in _read_csv(final_dir / "document_dependencies.csv"):
        if row.get("relationship_type") == "required":
            baskets[row["service_id"]].add(row["required_document_normalized"])
    by_service: dict[str, dict[str, str]] = defaultdict(dict)
    for row in _read_csv(mining_dir / "charter_check_services.csv"):
        by_service[row["service_id"]][row["document"]] = row["page_role"]

    rules = _read_csv(mining_dir / "rules_charter_confirmed.csv")
    rules.sort(key=lambda row: (row["antecedent_documents"], row["consequent_documents"]))
    davao = _davao_offices(offices)

    route_rows = []
    stop_rows = []
    leg_rows = []
    for index, rule in enumerate(rules, start=1):
        route_id = f"ROUTE-{index:04d}"
        roles = _rule_roles(rule, baskets, by_service)
        situation = _situation(roles)
        built = _build_one(route_id, rule, situation, davao, services, baskets)
        route_rows.append(built["route"])
        stop_rows.extend(built["stops"])
        leg_rows.extend(built["legs"])

    _fill_road_legs(leg_rows)
    _check(route_rows, stop_rows, leg_rows, rules)
    _write_routes(mining_dir / "routes.csv", route_rows)
    _write_stops(mining_dir / "route_stops.csv", stop_rows)
    _write_legs(mining_dir / "route_legs.csv", leg_rows)
    _write_summary(mining_dir / "route_summary.txt", route_rows, stop_rows, leg_rows)
    return mining_dir / "routes.csv"


def _build_one(route_id, rule, situation, davao, services, baskets) -> dict:
    antecedent = _split_docs(rule["antecedent_documents"])
    consequent = _split_docs(rule["consequent_documents"])
    groups = [
        ("1", "antecedent", antecedent),
        ("2", "consequent", consequent),
        ("3", "receiving_office", []),
    ]
    stops = []
    for group_order, group_label, documents in groups:
        if group_label == "receiving_office":
            stops.append(_receiving_stop(route_id, davao))
            continue
        for document in sorted(documents):
            stops.append(_document_stop(route_id, group_order, group_label, document, davao))

    legs = []
    for left_order, right_order in (("1", "2"), ("2", "3")):
        left_stops = [stop for stop in stops if stop["group_order"] == left_order]
        right_stops = [stop for stop in stops if stop["group_order"] == right_order]
        for left in left_stops:
            for right in right_stops:
                legs.extend(_legs_between(route_id, left, right))

    supporters = _supporters(rule, baskets)
    agencies = sorted({services[service_id]["agency_acronym"] for service_id in supporters})
    route = {
        "route_id": route_id,
        "locality": LOCALITY,
        "situation": situation,
        "antecedent_ids": rule["antecedent_ids"],
        "consequent_ids": rule["consequent_ids"],
        "antecedent_documents": rule["antecedent_documents"],
        "consequent_documents": rule["consequent_documents"],
        "support_count": rule["support_count"],
        "confidence": rule["confidence"],
        "lift": rule["lift"],
        "services_checked": rule["services_checked"],
        "receiving_agencies": "|".join(agencies),
        "sequence": _sequence_text(stops),
    }
    return {"route": route, "stops": stops, "legs": legs}


def _document_stop(route_id, group_order, group_label, document, davao) -> dict:
    agency, note = ISSUER.get(document, ("", "No issuing office was collected for this document."))
    offices = davao.get(agency, []) if agency else []
    return _stop(route_id, group_order, group_label, document, agency, offices, note)


def _receiving_stop(route_id, davao) -> dict:
    offices = davao.get(RECEIVING_AGENCY, [])
    return _stop(
        route_id,
        "3",
        "receiving_office",
        "",
        RECEIVING_AGENCY,
        offices,
        "PRC Regional Office XI receives the licensure application in Davao City.",
    )


def _stop(route_id, group_order, group_label, document, agency, offices, note) -> dict:
    located = [office for office in offices if _has_coordinate(office)]
    status = "unlocated"
    if len(located) == 1 and len(offices) == 1:
        status = "located"
    elif len(located) > 1:
        status = "alternate_offices"
    elif located:
        status = "located"
    return {
        "route_id": route_id,
        "group_order": group_order,
        "group_label": group_label,
        "document": document,
        "issuer_agency": agency,
        "office_ids": ";".join(office["office_id"] for office in offices),
        "office_names": ";".join(office["office_name"] for office in offices),
        "location_status": status,
        "location_note": note,
        "_offices": offices,
    }


def _legs_between(route_id, left, right) -> list[dict]:
    left_offices = left["_offices"] or [None]
    right_offices = right["_offices"] or [None]
    rows = []
    for origin in left_offices:
        for destination in right_offices:
            rows.append(_one_leg(route_id, left, right, origin, destination))
    return rows


def _one_leg(route_id, left, right, origin, destination) -> dict:
    origin_id = origin["office_id"] if origin else ""
    destination_id = destination["office_id"] if destination else ""
    both = origin is not None and destination is not None
    same = both and origin_id == destination_id
    road = both and not same and _has_coordinate(origin) and _has_coordinate(destination)
    if same:
        status = "same_office"
        distance = "0"
        duration = "0"
    elif road:
        status = "road"
        distance = ""
        duration = ""
    else:
        status = "unlocated"
        distance = ""
        duration = ""
    return {
        "route_id": route_id,
        "from_group": left["group_order"],
        "to_group": right["group_order"],
        "from_document": left["document"],
        "to_document": right["document"] or "PRC licensure application",
        "from_office_id": origin_id,
        "to_office_id": destination_id,
        "from_office_name": origin["office_name"] if origin else "",
        "to_office_name": destination["office_name"] if destination else "",
        "leg_status": status,
        "distance_meters": distance,
        "duration_seconds": duration,
        "distance_source": "same office" if same else "",
        "_origin": origin if road else None,
        "_destination": destination if road else None,
    }


def _fill_road_legs(legs: list[dict]) -> None:
    cache: dict[tuple[str, str], dict] = {}
    for leg in legs:
        if leg["leg_status"] != "road":
            continue
        key = (leg["from_office_id"], leg["to_office_id"])
        if key not in cache:
            cache[key] = _road_leg(leg["_origin"], leg["_destination"])
        measured = cache[key]
        leg["distance_meters"] = measured["distance_meters"]
        leg["duration_seconds"] = measured["duration_seconds"]
        leg["distance_source"] = measured["distance_source"]
        if not measured["distance_meters"]:
            leg["leg_status"] = "road_not_retrieved"
    for leg in legs:
        leg.pop("_origin", None)
        leg.pop("_destination", None)


def _road_leg(origin: dict, destination: dict) -> dict:
    lon1, lat1 = origin["longitude"], origin["latitude"]
    lon2, lat2 = destination["longitude"], destination["latitude"]
    path = f"{lon1},{lat1};{lon2},{lat2}"
    for server in OSRM_SERVERS:
        url = f"{server}/route/v1/driving/{path}?overview=false"
        try:
            payload = _get_json(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            continue
        routes = payload.get("routes") if payload.get("code") == "Ok" else None
        if not routes:
            continue
        return {
            "distance_meters": str(round(float(routes[0]["distance"]))),
            "duration_seconds": str(round(float(routes[0]["duration"]))),
            "distance_source": f"OpenStreetMap driving route via {server}",
        }
    return {"distance_meters": "", "duration_seconds": "", "distance_source": ""}


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "govdocpath-routes/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _situation(roles: set[str]) -> str:
    if roles == {"joint"}:
        return "every applicant"
    if "married_female" in roles or "conditional" in roles:
        return "married applicant"
    return "foreign applicant"


def _supporters(rule, baskets) -> list[str]:
    union = set(_split_docs(rule["antecedent_documents"]) + _split_docs(rule["consequent_documents"]))
    return [service_id for service_id, basket in baskets.items() if union <= basket]


def _sequence_text(stops: list[dict]) -> str:
    parts = []
    for group_order in ("1", "2", "3"):
        labels = []
        for stop in stops:
            if stop["group_order"] != group_order:
                continue
            name = stop["document"] or "PRC licensure application"
            office = stop["office_names"] or "unlocated"
            labels.append(f"{name} [{office}]")
        if labels:
            parts.append(" + ".join(labels))
    return " → ".join(parts)


def _davao_offices(offices: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for office in offices:
        if office.get("city") == LOCALITY:
            grouped[office["agency_acronym"]].append(office)
    for rows in grouped.values():
        rows.sort(key=lambda office: office["office_id"])
    return grouped


def _has_coordinate(office: dict) -> bool:
    return bool((office.get("latitude") or "").strip() and (office.get("longitude") or "").strip())


def _check(routes, stops, legs, rules) -> None:
    if len(routes) != len(rules):
        raise SystemExit(f"Expected one route per confirmed rule, got {len(routes)} for {len(rules)} rules.")
    counts = defaultdict(int)
    for route in routes:
        counts[route["situation"]] += 1
        if route["receiving_agencies"] != RECEIVING_AGENCY:
            raise SystemExit(f"{route['route_id']} is not received by PRC.")
        if "PSA Marriage Certificate" in route["consequent_documents"]:
            raise SystemExit(f"{route['route_id']} puts the marriage certificate on the consequent side.")
    expected = {"every applicant": 36, "married applicant": 42, "foreign applicant": 376}
    if dict(counts) != expected:
        raise SystemExit(f"Situation counts {dict(counts)} do not match the charter reading {expected}.")
    for stop in stops:
        if stop["document"] == "Transcript of Records (TOR)" and stop["location_status"] != "unlocated":
            raise SystemExit("A transcript stop was given an office.")
        if stop["document"] == "NBI Clearance" and "NBI-OFF-B558C709" not in stop["office_ids"]:
            raise SystemExit("An NBI stop dropped a Davao office.")
        if stop["document"] == "NBI Clearance" and "NBI-OFF-01374019" not in stop["office_ids"]:
            raise SystemExit("An NBI stop dropped a Davao office.")
        if stop["document"] == "Certificate of Live Birth (PSA)" and stop["office_ids"] != "PSA-OFF-C96C1839":
            raise SystemExit("A birth-certificate stop is not the Davao PSA outlet.")
        if stop["group_label"] == "receiving_office" and stop["office_ids"] != "PRC-OFF-0832FC0C":
            raise SystemExit("The receiving stop is not PRC Regional Office XI.")
    for leg in legs:
        if leg["leg_status"] == "road" and (not leg["from_office_id"] or not leg["to_office_id"] or not leg["distance_meters"]):
            raise SystemExit("A road leg is missing an office or a distance.")
        if leg["leg_status"] == "unlocated" and (leg["distance_meters"] or leg["duration_seconds"]):
            raise SystemExit("An unlocated leg was given a distance.")
        if leg["leg_status"] == "road_not_retrieved":
            raise SystemExit(f"OpenStreetMap returned no driving route for {leg['from_office_id']} to {leg['to_office_id']}.")


def _write_routes(path: Path, rows: list[dict]) -> None:
    fields = [
        "route_id", "locality", "situation", "antecedent_ids", "consequent_ids",
        "antecedent_documents", "consequent_documents", "support_count", "confidence",
        "lift", "services_checked", "receiving_agencies", "sequence",
    ]
    _write(path, fields, rows)


def _write_stops(path: Path, rows: list[dict]) -> None:
    fields = [
        "route_id", "group_order", "group_label", "document", "issuer_agency",
        "office_ids", "office_names", "location_status", "location_note",
    ]
    _write(path, fields, rows)


def _write_legs(path: Path, rows: list[dict]) -> None:
    fields = [
        "route_id", "from_group", "to_group", "from_document", "to_document",
        "from_office_id", "to_office_id", "from_office_name", "to_office_name",
        "leg_status", "distance_meters", "duration_seconds", "distance_source",
    ]
    _write(path, fields, rows)


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, routes, stops, legs) -> None:
    situations = defaultdict(int)
    for route in routes:
        situations[route["situation"]] += 1
    leg_counts = defaultdict(int)
    unique_roads = {}
    for leg in legs:
        leg_counts[leg["leg_status"]] += 1
        if leg["leg_status"] == "road":
            unique_roads[(leg["from_office_id"], leg["to_office_id"])] = leg
    unlocated_docs = sorted({stop["document"] for stop in stops if stop["location_status"] == "unlocated" and stop["document"]})
    lines = [
        "Office routes",
        f"Built on: {BUILT_ON}",
        f"Locality: {LOCALITY}",
        "Source rules: output/mining/rules_charter_confirmed.csv",
        "",
        "Each confirmed rule has one sequence. Antecedent documents come before consequent documents.",
        "The last stop is PRC Regional Office XI, which receives the licensure application.",
        "Documents in the same group are not ordered against each other.",
        "A road leg is an OpenStreetMap driving route and is drawn only when both offices already have coordinates.",
        "The driving time is travel between offices. It is not waiting time inside an office.",
        "",
        f"Routes: {len(routes)}",
        f"  every applicant: {situations['every applicant']}",
        f"  married applicant: {situations['married applicant']}",
        f"  foreign applicant: {situations['foreign applicant']}",
        f"Stops: {len(stops)}",
        f"Legs: {len(legs)}",
        f"  road: {leg_counts['road']}",
        f"  same office: {leg_counts['same_office']}",
        f"  unlocated: {leg_counts['unlocated']}",
        "",
        "Documents with no office in the table: " + "; ".join(unlocated_docs),
        "",
        "Measured driving legs in Davao:",
    ]
    for key in sorted(unique_roads):
        leg = unique_roads[key]
        kilometers = int(leg["distance_meters"]) / 1000
        minutes = int(leg["duration_seconds"]) / 60
        lines.append(
            f"  {leg['from_office_name']} → {leg['to_office_name']}: "
            f"{kilometers:.1f} km, {minutes:.0f} minutes"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    print(build_routes())
