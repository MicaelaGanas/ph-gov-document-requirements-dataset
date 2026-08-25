"""Registry of all agency scrapers."""

from __future__ import annotations

from typing import Type

from scraper.agencies.comelec import COMELECScraper
from scraper.agencies.davao import DavaoCityScraper
from scraper.agencies.dfa import DFAScraper
from scraper.agencies.dti import DTIScraper
from scraper.agencies.gsis import GSISScraper
from scraper.agencies.lto import LTOScraper
from scraper.agencies.nbi import NBIScraper
from scraper.agencies.pagibig import PagIBIGScraper
from scraper.agencies.philhealth import PhilHealthScraper
from scraper.agencies.philsys import PhilSysScraper
from scraper.agencies.prc import PRCScraper
from scraper.agencies.psa import PSAScraper
from scraper.agencies.sss import SSSScraper
from scraper.base import BaseScraper

SCRAPER_REGISTRY: dict[str, Type[BaseScraper]] = {
    "philsys": PhilSysScraper,
    "psa": PSAScraper,
    "dfa": DFAScraper,
    "nbi": NBIScraper,
    "lto": LTOScraper,
    "prc": PRCScraper,
    "comelec": COMELECScraper,
    "dti": DTIScraper,
    "sss": SSSScraper,
    "philhealth": PhilHealthScraper,
    "pagibig": PagIBIGScraper,
    "gsis": GSISScraper,
    "davao": DavaoCityScraper,
}

ALL_AGENCY_KEYS = list(SCRAPER_REGISTRY.keys())
