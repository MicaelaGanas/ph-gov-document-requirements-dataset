"""PSA civil registration scraper (prototype entry point).

Official sources:
- https://psa.gov.ph/birth-certificate
- https://psa.gov.ph/marriage-certificate
- https://psa.gov.ph/death-certificate
- https://psa.gov.ph/cenomar

Implementation lives in ``scraper.agencies.psa``; this module provides the
research-project entry point requested in the project specification.
"""

from __future__ import annotations

from scraper.agencies.psa import PSAScraper

__all__ = ["PSAScraper"]
