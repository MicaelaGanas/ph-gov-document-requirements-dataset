"""NBI Clearance requirements."""

from __future__ import annotations

import re

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, extract_label_value_pairs, find_main_content, soup_from_html
from scraper.parsers.requirements import infer_quantity


class NBIScraper(BaseScraper):
    agency = "National Bureau of Investigation"
    agency_code = "NBI"

    CHARTER_URL = "https://nbi.gov.ph/citizens-charter/nbi-clearance-application/"
    HOWTO_URL = "https://nbi.gov.ph/how-to-apply-nbi-clearance/"

    def scrape(self) -> list:
        self._scrape_citizens_charter()
        self._scrape_how_to_apply()
        return self.records()

    def _scrape_citizens_charter(self) -> None:
        result = self.fetch(self.CHARTER_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="NBI Clearance Application",
                source_url=self.CHARTER_URL,
                reason=result.error or "fetch failed",
            )
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        pairs = extract_label_value_pairs(root)

        requirements_blob = pairs.get("Requirements", "")
        fees = pairs.get("Fees", "")
        location = pairs.get("Address and Contact Information", "")

        # Core ID requirement from charter
        for req in split_id_requirements(requirements_blob):
            self.add(
                service_name="NBI Clearance Application",
                service_category="Police Clearance",
                target_document="NBI Clearance",
                transaction_type="new_application|renewal",
                applicant_type="General public",
                requirement_name=req,
                source_url=self.CHARTER_URL,
                requirement_role="acceptable_id",
                quantity=infer_quantity(req) or "2",
                conditional="no",
                notes="Two valid government-issued IDs required (or PSA Birth Certificate as alternative per how-to guide)",
                application_method="online_and_walk_in",
                appointment_required="no",
                fee=fees,
                fee_currency="PHP",
                location=location,
                source_section="Citizen's Charter - Requirements",
                requirement_order=1,
            )

        for h2 in root.find_all("h2"):
            channel = clean_text(h2.get_text())
            if not channel:
                continue
            table = h2.find_next("table")
            if not table:
                continue
            for row_idx, row in enumerate(table.select("tbody tr"), start=1):
                cells = [clean_text(td.get_text(" ", strip=True)) for td in row.find_all("td")]
                if len(cells) < 2:
                    continue
                step = cells[1]
                duration = cells[-1] if len(cells) >= 6 else ""
                self.add(
                    service_name="NBI Clearance Application",
                    service_category="Police Clearance",
                    target_document="NBI Clearance",
                    transaction_type="new_application",
                    applicant_type="General public",
                    requirement_name=step,
                    source_url=self.CHARTER_URL,
                    requirement_role="procedure",
                    application_method=channel.lower().replace(" ", "_"),
                    appointment_required="no",
                    processing_time=duration,
                    fee=fees,
                    location=cells[4] if len(cells) > 4 else location,
                    source_section=channel,
                    requirement_order=row_idx,
                )

    def _scrape_how_to_apply(self) -> None:
        result = self.fetch(self.HOWTO_URL)
        if not result.ok:
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 10

        for li in root.select(".entry-content li"):
            text = clean_text(li.get_text(" ", strip=True))
            if not text or len(text) < 8:
                continue
            lower = text.lower()

            if "what to bring" in lower:
                items = split_what_to_bring(text)
                for item in items:
                    role = classify_nbi_item(item)
                    order += 1
                    self.add(
                        service_name="NBI Clearance Application",
                        service_category="Police Clearance",
                        target_document="NBI Clearance",
                        transaction_type="new_application",
                        applicant_type="General public",
                        requirement_name=item,
                        source_url=self.HOWTO_URL,
                        requirement_role=role,
                        quantity=infer_quantity(item) or ("2" if role == "acceptable_id" else ""),
                        conditional="yes" if "first-time job seeker" in item.lower() else "no",
                        condition="First-time job seeker" if "first-time job seeker" in item.lower() else "",
                        application_method="online_and_walk_in",
                        appointment_required="no",
                        source_section="What to Bring",
                        requirement_order=order,
                    )
                continue

            if "valid" in lower and "id" in lower and len(text) < 300:
                # Skip — already captured from charter / what to bring
                continue

            role = "procedure"
            if any(k in lower for k in ("certificate", "receipt", "reference number", "qr code")):
                role = "required_document"

            order += 1
            self.add(
                service_name="NBI Clearance Application",
                service_category="Police Clearance",
                target_document="NBI Clearance",
                transaction_type="new_application",
                applicant_type="General public",
                requirement_name=text,
                source_url=self.HOWTO_URL,
                requirement_role=role,
                application_method="online_and_walk_in",
                appointment_required="no",
                source_section="Application Steps",
                requirement_order=order,
            )


def split_id_requirements(blob: str) -> list[str]:
    blob = clean_text(blob)
    if not blob:
        return []
    return [blob]


def split_what_to_bring(text: str) -> list[str]:
    text = re.sub(r"^What to Bring:\s*", "", text, flags=re.I).strip()
    parts = re.split(r"\.\s+(?=\()", text)
    if len(parts) > 1:
        base = parts[0]
        items = []
        for chunk in re.split(r"\.\s+(?=[A-Z])", base):
            chunk = clean_text(chunk)
            if chunk:
                items.append(chunk)
        items.extend(clean_text(p) for p in parts[1:] if clean_text(p))
        return items

    items = []
    patterns = [
        r"(Your printed or digital Reference Number \(or QR code\))",
        r"(Proof of payment / receipt)",
        r"(Two \(2\) Valid Government-issued IDs[^.]*)",
        r"(\(For First-Time Job Seekers:[^)]+\))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            items.append(clean_text(match.group(1)))
    return items or [text]


def classify_nbi_item(text: str) -> str:
    lower = text.lower()
    if "first-time job seeker" in lower:
        return "required_document"
    if "reference number" in lower or "qr code" in lower or "proof of payment" in lower or "receipt" in lower:
        return "required_document"
    if "valid" in lower and "id" in lower:
        return "acceptable_id"
    return "procedure"
