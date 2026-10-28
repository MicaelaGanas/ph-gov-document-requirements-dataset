# Intelligent Planning and Geospatial Mapping of Document Acquisition Routes

Research dataset pipeline for **Philippine government IDs and official documents**, collected only from official `.gov.ph` websites and Citizen's Charters.

**Research title:** *Intelligent Planning and Geospatial Mapping of Document Acquisition Routes for Philippine Government IDs and Official Documents*

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m playwright install chromium   # optional, for Cloudflare sites

# Full pipeline: scrape → raw → cleaned → 5 final CSV tables
python build.py

# Scrape specific agencies only
python build.py -a dfa nbi philsys sss psa

# Rebuild final tables from existing raw scrape (no network)
python build.py --export-only
```

## Project structure

```
build.py                      # End-to-end pipeline entry point
scrape.py                     # Scraper-only CLI (writes data/raw/)
config/sources.yaml           # Official source registry (documentation)
scraper/
  common.py                   # Shared fetch/parse helpers
  psa_scraper.py              # PSA prototype entry point
  agencies/                   # One module per agency (13 agencies)
  models.py                   # Raw RequirementRecord model
processing/
  build_dataset.py            # Raw → 5 normalized CSV tables
  clean_data.py               # Dedupe + type normalization
  normalize_documents.py      # Document/agency name normalization
  validate_data.py            # FK / ID integrity checks
mining/
  association_analysis.py     # Document co-occurrence mining starter
data/
  raw/                        # Unprocessed scrape output
  cleaned/                    # Deduped flat requirements
  final/                      # Research dataset (5 CSV files)
output/                       # Mining / analysis outputs
notebooks/                    # Exploratory analysis
```

## Official data sources

| Agency | Acronym | Service | Official URLs |
|--------|---------|---------|---------------|
| PhilSys / PSA | PHILSYS | National ID Registration | philsys.gov.ph/registration-process, supporting-documents |
| PSA | PSA | Birth, marriage, death, and CENOMAR | psa.gov.ph/birth-certificate, marriage-certificate, death-certificate, cenomar |
| DFA | DFA | Passport (Adult New) | consular.dfa.gov.ph passport requirements, valid IDs |
| NBI | NBI | NBI Clearance | nbi.gov.ph citizens-charter, how-to-apply |
| LTO | LTO | Student permit, new license, and renewal | lto.gov.ph Citizen's Charter 2025 PDF |
| PRC | PRC | Professional Licensure | prc.gov.ph/list-of-requirements |
| COMELEC | COMELEC | Voter Registration | comelec.gov.ph registration-requirements HTML fragment |
| DTI | DTI | Business Name Registration | bnrs.dti.gov.ph FAQ and Annex A ID list |
| SSS | SSS | Membership Registration | sss.gov.ph become-a-member, valid IDs |
| PhilHealth | PHILHEALTH | Formal Economy Registration | philhealth.gov.ph/members/formal/registration.php |
| Pag-IBIG | PAGIBIG | Membership | pagibigfund.gov.ph |
| GSIS | GSIS | UMID eCard Enrollment | gsis.gov.ph Citizen's Charter PDF |
| Davao City LGU | LGU-DAVAO | Business permit and online renewal | davaocity.gov.ph checklist images |

**Not used:** Kaggle, UCI, Wikipedia, blogs, or unofficial third-party sites.

## Final dataset tables (`data/final/`)

### 1. `government_services.csv`
One row per government service (passport, NBI clearance, SSS registration, etc.).

| Column | Description |
|--------|-------------|
| `service_id` | Stable unique ID |
| `agency`, `agency_acronym` | Issuing agency |
| `service_name`, `target_document` | Service and output credential |
| `transaction_type`, `applicant_type` | Who / what transaction |
| `application_method`, `appointment_required` | How to apply |
| `processing_time`, `fee` | Service-level metadata when stated |
| `source_url`, `source_title`, `last_verified` | Provenance |
| `scrape_status`, `record_count` | Data quality |

### 2. `requirements.csv`
One row per requirement (document, ID, procedure step, fee line).

| Column | Description |
|--------|-------------|
| `requirement_id`, `service_id` | IDs + foreign key |
| `requirement_name` | **Original official wording** |
| `requirement_name_normalized` | Canonical label for analysis joins |
| `requirement_type`, `requirement_role` | `required_document`, `acceptable_id`, `supporting_document`, `procedure`, etc. |
| `conditional`, `condition` | Branching logic |
| `issuing_agency`, `document_format`, `quantity` | Document metadata |
| `source_url`, `source_section`, `requirement_description` | Traceability |

### 3. `government_offices.csv`
Office/location entities from official `.gov.ph` sources, Citizen's Charters, and the Davao City enrichment pass.

| Column | Description |
|--------|-------------|
| `office_id`, `office_name`, `office_type` | e.g. consular_office, regional_office, bureau |
| `region`, `province`, `city`, `barangay`, `address` | Geographic fields from official listings |
| `latitude`, `longitude` | From **OpenStreetMap Nominatim** geocoding (`geocode_source`, `geocode_status`) — never fabricated |
| `services_offered` | Pipe-separated document/service tags for route planning |
| `office_image_url`, `office_image_path`, `office_image_source` | Exterior building photo; `official_gov_ph` first, then Bing image search fallback (`web_search_bing`) |
| `contact_number`, `operating_hours` | When available from source |

**Davao City first:** run `python build.py --offices-only` to scrape 10 Davao offices (PhilSys, PSA, NBI, LTO, SSS, COMELEC, LGU), geocode addresses, download images, and write `data/final/davao_government_offices.csv`. Service links are added to `service_locations.csv`.

Geocoding uses `processing/geocode.py` (Nominatim, 1 req/s, building-specific fallbacks for known sites such as Ango Building and LTO MVIS Compound).

### 4. `service_locations.csv`
Links services to offices where they can be applied for.

### 5. `document_dependencies.csv`
Prerequisite graph for pathway planning.

| `relationship_type` | Meaning |
|---------------------|---------|
| `required` | Must submit |
| `conditional` | Required only if condition applies |
| `alternative` | Pick any one (e.g. acceptable IDs) |

## Raw vs cleaned vs final

| Stage | Path | Contents |
|-------|------|----------|
| Raw | `data/raw/gov_requirements.csv` | Flat scrape, one row per requirement |
| Cleaned | `data/cleaned/gov_requirements.csv` | Deduped + normalized types |
| Final | `data/final/*.csv` | Normalized 5-table research schema |

## Data collection ethics

- Respects rate limits (sequential requests, retries with backoff)
- No personal information about citizens
- No fabricated coordinates or fees
- Blocked/seed rows clearly marked via `scrape_status`
- Every record preserves `source_url`

## Analysis filter (recommended)

The application reads `relationship_type` on `document_dependencies.csv`. `required`, `conditional`, and `alternative` stay separate. Official readings with `scrape_status` of `success` or `partial` enter that table. `seed` and `blocked` rows stay out of it, so a missing page is an unavailable service rather than a filled-in checklist.

Association mining uses only `relationship_type = required`. Alternatives and conditionals remain in the dependency table for the application and are not counted as jointly required.

```text
relationship_type = 'required'
AND scrape_status IN ('success', 'partial')
```

Run association mining:

```bash
python -m mining.association_analysis   # or via build.py (default)
```

Output: `output/association_document_pairs.csv`

## Browser fallback (Cloudflare)

```bash
python build.py --browser -a dfa psa lto comelec
```

The scraper reuses **one Playwright browser** per run (faster for DFA’s many pages), waits between requests, and retries with the browser when a page is a bot challenge or an empty JavaScript shell.

| Site | Status |
|------|--------|
| DFA consular | Live via Playwright when the page renders; a failed page is `blocked`, with no seed copy |
| NBI, PRC, SSS, PhilHealth, DTI | Usually live via HTTP |
| PhilSys | Supporting-documents page is under maintenance. The 27 August 2026 reading is stored as `partial`, and each primary line is one alternative |
| COMELEC | HTML fragment behind the JavaScript shell; blocked if that fragment has no ID list |
| Davao City business permit | Checklist is an image on davaocity.gov.ph; rows are a reading of that image (`partial`) |
| PSA, LTO, GSIS | Cloudflare or WAF; a reading of the official page or Citizen's Charter is kept as `partial` |
| Pag-IBIG | Membership page is behind reCAPTCHA. No seed checklist is stored; the service stays `blocked` until an official list can be read |

## License / disclaimer

Public-domain government information. Always verify on official websites before legal or compliance use.
