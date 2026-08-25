"""PSA civil registration scraper (prototype entry point).

Official sources:
- https://psa.gov.ph/civilregistration — civil registration services overview
- Citizen's Charter content linked from PSA pages (when accessible)

Implementation lives in ``scraper.agencies.psa``; this module provides the
research-project entry point requested in the project specification.
"""

from __future__ import annotations

from scraper.agencies.psa import PSAScraper

__all__ = ["PSAScraper"]
