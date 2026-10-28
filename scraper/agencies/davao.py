"""Davao City business permit requirements.

The city page does not publish a text checklist. The basic requirements are
the guide image, and the online renewal documents are the process-flow image.
"""

from __future__ import annotations

import requests

from scraper.base import BaseScraper

GUIDE_IMAGE = (
    "https://davaocity.gov.ph/wp-content/uploads/2019/01/Processing-of-Business-Permit.jpg"
)
RENEWAL_IMAGE = (
    "https://davaocity.gov.ph/wp-content/uploads/2021/10/"
    "new-application-of-business-permit-2-1024x614.gif"
)
PAGE_URL = "https://davaocity.gov.ph/services/processing-of-business-permits/"
ONLINE_URL = "https://appbts.davaocity.gov.ph/"

_IMAGE_NOTE = (
    "The city page publishes this checklist as an image. This row is a reading of that image."
)

_WALK_IN = (
    "Business Bureau, Ground Floor, Sangguniang Panlungsod Building, "
    "San Pedro Street, Davao City"
)


class DavaoCityScraper(BaseScraper):
    agency = "Davao City LGU"
    agency_code = "LGU-DAVAO"

    def scrape(self) -> list:
        self._add_basic_permit()
        self._add_online_renewal()
        return self.records()

    def _add_basic_permit(self) -> None:
        if not _image_downloads(GUIDE_IMAGE):
            self.add_blocked_notice(
                service_name="Business Permit",
                source_url=PAGE_URL,
                reason="The basic-requirements image did not download",
            )
            return
        items = (
            (
                "Proof of business registration, incorporation, or legal personality (DTI, SEC, CDA, or DOLE registration)",
                "required_document",
                "no",
                "",
                "photocopy",
            ),
            (
                "Basis for computing taxes, fees, and charges (for example, business capitalization)",
                "required_document",
                "no",
                "",
                "",
            ),
            (
                "Copy of Occupancy Permit",
                "required_document",
                "no",
                "",
                "photocopy",
            ),
            (
                "Contract of Lease",
                "supporting_document",
                "yes",
                "Applicant is a lessee",
                "photocopy",
            ),
            (
                "Barangay Clearance",
                "required_document",
                "no",
                "",
                "photocopy",
            ),
            (
                "Duly filled-in, signed, and notarized Unified Application Form",
                "required_document",
                "no",
                "",
                "original",
            ),
            (
                "Submit the application form and clear copies of the documentary requirements to the Licensing Officer",
                "procedure",
                "no",
                "",
                "",
            ),
            (
                "Present the Business ID stub to the Assessment Officer and pay the taxes, fees, and charges",
                "procedure",
                "no",
                "",
                "",
            ),
            (
                "Present the Business ID stub when claiming the Mayor's Permit",
                "procedure",
                "no",
                "",
                "",
            ),
        )
        self._add_service(
            service_name="Business Permit",
            transaction_type="new_application",
            application_method="walk_in",
            location=_WALK_IN,
            source_url=GUIDE_IMAGE,
            source_section="Guide to Securing your Business Permit",
            items=items,
        )

    def _add_online_renewal(self) -> None:
        if not _image_downloads(RENEWAL_IMAGE):
            self.add_blocked_notice(
                service_name="Online Renewal of Business Permit",
                source_url=PAGE_URL,
                reason="The renewal process-flow image did not download",
            )
            return
        items = (
            (
                "BIR Form 2551Q (Quarterly Percentage Tax return)",
                "required_document",
                "no",
                "",
                "",
            ),
            (
                "Financial Statement",
                "required_document",
                "no",
                "",
                "",
            ),
            (
                "Register with the Business Bureau when the taxpayer's email is not yet on file",
                "procedure",
                "yes",
                "Taxpayer email is not yet registered in the online system",
                "",
            ),
            (
                "Upload the required documents after logging in with the Business ID and access code",
                "procedure",
                "no",
                "",
                "",
            ),
            (
                "Pay online through Landbank or DBP when the application status is approved",
                "procedure",
                "no",
                "",
                "",
            ),
        )
        self._add_service(
            service_name="Online Renewal of Business Permit",
            transaction_type="renewal",
            application_method="online",
            location=ONLINE_URL,
            source_url=RENEWAL_IMAGE,
            source_section="Online Renewal of Business Permit process flow",
            items=items,
            notes=(
                f"{_IMAGE_NOTE} Questions: (082) 241-1000 loc 380/381. "
                "The image file name says new-application; the image title is the online renewal flow."
            ),
        )

    def _add_service(
        self,
        *,
        service_name: str,
        transaction_type: str,
        application_method: str,
        location: str,
        source_url: str,
        source_section: str,
        items: tuple,
        notes: str = _IMAGE_NOTE,
    ) -> None:
        for order, (name, role, conditional, condition, document_format) in enumerate(items, start=1):
            issuing = "BIR" if name.startswith("BIR Form") else ""
            self.add(
                service_name=service_name,
                service_category="LGU Business Licensing",
                target_document="Davao City Mayor's Permit",
                transaction_type=transaction_type,
                applicant_type="Business owner",
                requirement_name=name,
                requirement_description=name,
                requirement_role=role,
                conditional=conditional,
                condition=condition,
                issuing_agency=issuing,
                document_format=document_format,
                application_method=application_method,
                appointment_required="no",
                location=location,
                source_url=source_url,
                source_section=source_section,
                requirement_order=order,
                scrape_status="partial",
                notes=notes,
            )


def _image_downloads(url: str) -> bool:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=40,
        )
    except requests.RequestException:
        return False
    content = response.content
    return response.status_code == 200 and (
        content.startswith(b"\xff\xd8")
        or content.startswith(b"GIF8")
        or content.startswith(b"\x89PNG")
    )
