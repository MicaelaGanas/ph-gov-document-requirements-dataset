"""Davao City government office locations (official sources)."""

from __future__ import annotations

import re

from scraper.base import BaseScraper
from scraper.http import fetch_page
from scraper.models_office import GovernmentOfficeRecord
from scraper.parsers.generic import clean_text, soup_from_html

# Official seed offices — addresses from .gov.ph pages (see source_url on each record).
DAVAO_OFFICE_SEEDS: tuple[dict, ...] = (
    {
        "agency": "Davao City LGU",
        "agency_acronym": "LGU-DAVAO",
        "office_name": "Davao City Business Bureau",
        "office_type": "bureau",
        "address": "Ground Floor, Sangguniang Panlungsod Building, San Pedro Street, Barangay 40-D, Davao City",
        "barangay": "Barangay 40-D",
        "contact_number": "(082) 241-1000 Local 377/378",
        "email": "busbureau@davaocity.gov.ph",
        "official_url": "https://davaocity.gov.ph/services/processing-of-business-permits/",
        "operating_hours": "Office hours per Davao City Business Bureau advisory",
        "services_offered": "business_permit|mayors_permit|lgu_document",
        "source_url": "https://davaocity.gov.ph/services/processing-of-business-permits/",
        "office_image_url": "",
    },
    {
        "agency": "Philippine Statistics Authority",
        "agency_acronym": "PSA",
        "office_name": "PSA Davao CRS Outlet",
        "office_type": "regional_office",
        "address": "Ango Building, Cabaguio Avenue, Davao City",
        "barangay": "Agdao",
        "contact_number": "(082) 224-1140 / (082) 221-3593",
        "email": "psaregion11@yahoo.com.ph",
        "official_url": "https://rsso11.psa.gov.ph/",
        "operating_hours": "Per PSA Davao Region advisory",
        "services_offered": "birth_certificate|marriage_certificate|death_certificate|cenomar|civil_registration",
        "source_url": "https://rsso11.psa.gov.ph/content/public-advisory-crs-online-appointment-system",
        "office_image_url": "",
    },
    {
        "agency": "Land Transportation Office",
        "agency_acronym": "LTO",
        "office_name": "LTO Region XI / Davao City District Offices (MVIS Compound)",
        "office_type": "regional_office",
        "address": "LTO MVIS Compound, Quimpo Boulevard, Barangay 39-D, Davao City",
        "barangay": "Barangay 39-D",
        "contact_number": "(082) 227-2513 / (082) 227-1471",
        "email": "r11_dcdo@yahoo.com",
        "official_url": "https://lto.gov.ph/",
        "operating_hours": "Monday–Friday 8:00 AM – 5:00 PM",
        "services_offered": "drivers_license|student_permit|vehicle_registration",
        "source_url": "https://lto.gov.ph/",
        "office_image_url": "",
    },
    {
        "agency": "Commission on Elections",
        "agency_acronym": "COMELEC",
        "office_name": "COMELEC Davao City Election Officer",
        "office_type": "district_office",
        "address": "3rd Floor, Sangguniang Panlungsod Building, San Pedro Street, Davao City",
        "barangay": "Barangay 40-D",
        "contact_number": "(082) 224-0663",
        "official_url": "https://comelec.gov.ph/",
        "operating_hours": "Per COMELEC field office schedule",
        "services_offered": "voter_registration|voters_id",
        "source_url": "https://www.comelec.gov.ph/?r=VoterRegistration/RegistrationProcedures",
        "office_image_url": "",
    },
    {
        "agency": "Social Security System",
        "agency_acronym": "SSS",
        "office_name": "SSS Davao Branch",
        "office_type": "branch",
        "address": "SSS Building, J.P. Laurel Avenue, Bajada, Davao City",
        "barangay": "Bajada",
        "contact_number": "1455",
        "official_url": "https://www.sss.gov.ph/",
        "operating_hours": "Monday–Friday per SSS branch advisory",
        "services_offered": "sss_number|sss_id|membership",
        "source_url": "https://www.sss.gov.ph/become-an-sss-member/",
        "office_image_url": "",
    },
    {
        "agency": "Philippine Statistics Authority (PhilSys)",
        "agency_acronym": "PHILSYS",
        "office_name": "PhilSys Mall Registration Center — SM City Davao",
        "office_type": "mall_registration_center",
        "address": "SM City Davao, Ecoland Drive, Davao City",
        "contact_number": "(082) 224-1140",
        "email": "psaregion11@yahoo.com.ph",
        "official_url": "https://rsso11.psa.gov.ph/",
        "operating_hours": "Per PSA Davao Region advisory",
        "services_offered": "national_id|philsys_registration",
        "source_url": "https://rsso11.psa.gov.ph/content/press-release-national-id-registration-and-other-national-id-services-continue-davao-del",
        "office_image_url": "",
    },
)

PHILSYS_URL = "https://philsys.gov.ph/registration-center/"
NBI_OFFICES_URL = "https://nbi.gov.ph/nbi-clearance-offices/"
PRC_DIRECTORY_URL = "https://www.prc.gov.ph/regional-offices-contact-information"
PHILHEALTH_DIRECTORY_URL = "https://www.philhealth.gov.ph/about_us/directory/"
DTI_REGION_URL = "https://www.dti.gov.ph/dti-regions/dti-region-11"
DFA_DIRECTORY_URL = "https://consular.dfa.gov.ph/directory"

REGION_XI = "Region XI (Davao Region)"
PROVINCE_DAVAO_CITY = "Davao del Sur"


class DavaoOfficesScraper(BaseScraper):
    """Collect Davao City office locations from official government websites."""

    agency = "Davao City LGU"
    agency_code = "LGU-DAVAO"

    def __init__(self) -> None:
        super().__init__()
        self._offices: list[GovernmentOfficeRecord] = []

    def scrape(self) -> list:
        # Requirement records unused; this scraper produces office records via offices().
        self._offices = []
        self._load_seeds()
        self._scrape_philsys_davao_centers()
        self._scrape_nbi_davao_offices()
        self._scrape_prc_davao()
        self._scrape_philhealth_davao()
        self._scrape_dti_davao()
        self._scrape_dfa_davao()
        return self.records()

    def offices(self) -> list[GovernmentOfficeRecord]:
        return list(self._offices)

    def _load_seeds(self) -> None:
        for seed in DAVAO_OFFICE_SEEDS:
            self._add_office(GovernmentOfficeRecord(
                region=REGION_XI,
                province=PROVINCE_DAVAO_CITY,
                city="Davao City",
                **seed,
            ))

    def _scrape_philsys_davao_centers(self) -> None:
        result = self.fetch(PHILSYS_URL)
        text = soup_from_html(result.html).get_text("\n", strip=True) if result.ok else ""
        if "city of davao" not in text.lower():
            result = self.fetch(PHILSYS_URL, use_browser=True, spa=True)
            text = soup_from_html(result.html).get_text("\n", strip=True) if result.ok else ""
        if "city of davao" not in text.lower():
            return
        blocks = _extract_philsys_davao_blocks(text)
        for block in blocks:
            self._add_office(GovernmentOfficeRecord(
                agency="Philippine Statistics Authority (PhilSys)",
                agency_acronym="PHILSYS",
                office_name=block["office_name"],
                office_type=block["office_type"],
                region=REGION_XI,
                province=PROVINCE_DAVAO_CITY,
                city="Davao City",
                barangay=block.get("barangay", ""),
                address=block["address"],
                operating_hours=block.get("operating_hours", ""),
                services_offered="national_id|philsys_registration",
                official_url=PHILSYS_URL,
                source_url=PHILSYS_URL,
            ))

    def _scrape_nbi_davao_offices(self) -> None:
        result = self.fetch(NBI_OFFICES_URL)
        if not result.ok:
            return

        soup = soup_from_html(result.html)
        for row in soup.select("table tr"):
            cells = [clean_text(td.get_text(" ", strip=True)) for td in row.find_all("td")]
            if len(cells) < 3:
                continue
            location_blob = " ".join(cells).lower()
            if "davao city" not in location_blob and "onestopshop – davao" not in location_blob:
                continue
            if "bansalan" in location_blob or "mati," in location_blob or "sulop" in location_blob:
                continue

            office_name = cells[1] if len(cells) > 1 else "NBI Davao Office"
            address = cells[2] if len(cells) > 2 else ""
            hours = cells[3] if len(cells) > 3 else "8:00 AM – 5:00 PM"
            office_type = "satellite_office" if (
                "gaisano" in office_name.lower() or "onestopshop" in office_name.lower()
            ) else "regional_office"

            self._add_office(GovernmentOfficeRecord(
                agency="National Bureau of Investigation",
                agency_acronym="NBI",
                office_name=office_name,
                office_type=office_type,
                region=REGION_XI,
                province=PROVINCE_DAVAO_CITY,
                city="Davao City",
                address=address,
                operating_hours=hours,
                services_offered="nbi_clearance",
                official_url=NBI_OFFICES_URL,
                source_url=NBI_OFFICES_URL,
            ))

    def _scrape_prc_davao(self) -> None:
        result = self.fetch(PRC_DIRECTORY_URL)
        if not result.ok:
            return
        text = re.sub(r"\s+@", "@", soup_from_html(result.html).get_text("\n", strip=True))
        match = re.search(
            r"Regional Office XI - Davao City\s+(.*?)\s+Tel\.:\s*([^\n]+)\s+(\S+@prc\.gov\.ph)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match or "davao city" not in match.group(1).lower():
            return
        address = " ".join(match.group(1).split())
        self._add_office(GovernmentOfficeRecord(
            agency="Professional Regulation Commission",
            agency_acronym="PRC",
            office_name="PRC Regional Office XI",
            office_type="regional_office",
            region=REGION_XI,
            province=PROVINCE_DAVAO_CITY,
            city="Davao City",
            address=address,
            contact_number=clean_text(match.group(2)),
            email=match.group(3),
            official_url=PRC_DIRECTORY_URL,
            services_offered="professional_license",
            source_url=PRC_DIRECTORY_URL,
        ))

    def _scrape_philhealth_davao(self) -> None:
        result = self.fetch(PHILHEALTH_DIRECTORY_URL)
        if not result.ok:
            return
        soup = soup_from_html(result.html)
        region = next(
            (
                heading
                for heading in soup.find_all("h2")
                if "pro xi" in clean_text(heading.get_text()).lower()
            ),
            None,
        )
        if region is None:
            return
        node = region
        while True:
            node = node.find_next()
            if node is None or getattr(node, "name", None) == "h2":
                break
            if getattr(node, "name", None) not in {"h4", "h6"}:
                continue
            title = clean_text(node.get_text())
            if node.name == "h4" and "regional office" not in title.lower():
                continue
            block = node.find_next("p", class_="address")
            if block is None:
                continue
            lines = [clean_text(line) for line in block.get_text("\n").splitlines() if clean_text(line)]
            address_lines: list[str] = []
            phone = ""
            for line in lines:
                if "@" in line:
                    continue
                if address_lines and re.search(r"\(?\d{3}\)?[\s.-]*\d{3}", line):
                    phone = line
                    break
                address_lines.append(line)
            address = " ".join(address_lines)
            if not address or "davao city" not in f"{title} {address}".lower():
                continue
            emails = [
                anchor["href"].split(":", 1)[1]
                for anchor in block.find_all("a", href=True)
                if anchor["href"].lower().startswith("mailto:")
            ]
            self._add_office(GovernmentOfficeRecord(
                agency="Philippine Health Insurance Corporation",
                agency_acronym="PHILHEALTH",
                office_name=f"PhilHealth PRO XI — {title}",
                office_type="regional_office" if "regional" in title.lower() else "service_center",
                region=REGION_XI,
                province=PROVINCE_DAVAO_CITY,
                city="Davao City",
                address=address,
                contact_number=phone,
                email=emails[0] if emails else "",
                official_url=PHILHEALTH_DIRECTORY_URL,
                services_offered="philhealth_membership",
                source_url=PHILHEALTH_DIRECTORY_URL,
            ))

    def _scrape_dti_davao(self) -> None:
        result = self.fetch(DTI_REGION_URL)
        if not result.ok:
            return
        text = soup_from_html(result.html).get_text("\n", strip=True)
        match = re.search(
            r"Address\s+(.*?Davao City)\s+Email:\s*(\S+)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return
        hours = ""
        hours_match = re.search(
            r"OFFICE HOURS\s+(Monday[^\n]+(?:\n\s*[0-9][^\n]+)?)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if hours_match:
            hours = clean_text(hours_match.group(1))
        self._add_office(GovernmentOfficeRecord(
            agency="Department of Trade and Industry",
            agency_acronym="DTI",
            office_name="DTI Regional Office XI",
            office_type="regional_office",
            region=REGION_XI,
            province=PROVINCE_DAVAO_CITY,
            city="Davao City",
            address=" ".join(match.group(1).split()),
            email=match.group(2),
            official_url=DTI_REGION_URL,
            operating_hours=hours,
            services_offered="business_name_registration",
            source_url=DTI_REGION_URL,
        ))

    def _scrape_dfa_davao(self) -> None:
        result = self.fetch(DFA_DIRECTORY_URL, use_browser=True, spa=True)
        if not result.ok:
            return
        lines = [
            clean_text(line)
            for line in soup_from_html(result.html).get_text("\n", strip=True).splitlines()
            if clean_text(line)
        ]
        start = None
        for index, line in enumerate(lines):
            lowered = line.lower()
            if "consular office davao" in lowered:
                start = index
                break
            if lowered == "davao" and index > 0 and "consular office" in lines[index - 1].lower():
                start = index
                break
        if start is None:
            return
        address = hours = phone = email = ""
        for line in lines[start + 1 : start + 15]:
            lower = line.lower()
            if lower.startswith("consular office"):
                break
            if lower in {"view", "maps", "view maps"} or lower == "8000":
                continue
            if "davao city" in lower and not address:
                address = line
            elif lower.startswith("monday") and not hours:
                hours = line
            elif re.search(r"\(082\)", line) and not phone:
                phone = line
            elif "@dfa.gov.ph" in lower and not email:
                email = line
        if "davao city" not in address.lower():
            return
        self._add_office(GovernmentOfficeRecord(
            agency="Department of Foreign Affairs",
            agency_acronym="DFA",
            office_name="DFA Consular Office Davao",
            office_type="consular_office",
            region=REGION_XI,
            province=PROVINCE_DAVAO_CITY,
            city="Davao City",
            address=address,
            contact_number=phone,
            email=email,
            official_url=DFA_DIRECTORY_URL,
            operating_hours=hours,
            services_offered="passport",
            source_url=DFA_DIRECTORY_URL,
        ))

    def _add_office(self, office: GovernmentOfficeRecord) -> None:
        key = (office.agency_acronym, office.office_name.lower(), office.address.lower())
        existing = {
            (o.agency_acronym, o.office_name.lower(), o.address.lower()): i
            for i, o in enumerate(self._offices)
        }
        if key in existing:
            return
        self._offices.append(office)


def _extract_philsys_davao_blocks(text: str) -> list[dict[str, str]]:
    """Parse PhilSys registration-center text for Davao City sites."""
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    blocks: list[dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lower() != "davao del sur, city of davao":
            i += 1
            continue
        i += 1
        while i < len(lines) and not lines[i].lower().startswith("davao "):
            address = lines[i]
            if address.startswith("[") or address.lower().startswith("monday"):
                i += 1
                continue
            site_type = "PSA-based"
            hours = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("["):
                site_type = lines[i + 1].strip("[]")
                i += 1
            if i + 1 < len(lines) and "monday" in lines[i + 1].lower():
                hours = lines[i + 1]
                if i + 2 < len(lines) and lines[i + 2].startswith("["):
                    hours = f"{hours} {lines[i + 2].strip('[]')}"
                    i += 1
                i += 1

            barangay = ""
            barangay_match = re.search(r"brgy\.?\s*([\w\-]+)", address, re.I)
            if barangay_match:
                barangay = barangay_match.group(0)

            office_type = "registration_center"
            if "mall" in address.lower() or "sm city" in address.lower():
                office_type = "mall_registration_center"
            elif "co-location" in site_type.lower():
                office_type = "colocation_site"

            blocks.append({
                "office_name": f"PhilSys Registration Center — {address.split(',')[0][:60]}",
                "office_type": office_type,
                "address": address,
                "barangay": barangay,
                "operating_hours": hours,
            })
            i += 1
        break
    return blocks
