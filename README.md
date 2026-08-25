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
| PSA | PSA | Civil Registration | psa.gov.ph/civilregistration |
| DFA | DFA | Passport (Adult New) | consular.dfa.gov.ph passport requirements, valid IDs |
| NBI | NBI | NBI Clearance | nbi.gov.ph citizens-charter, how-to-apply |
| LTO | LTO | Driver's License | lto.gov.ph (Cloudflare; seed when blocked) |
| PRC | PRC | Professional Licensure | prc.gov.ph/list-of-requirements |
| COMELEC | COMELEC | Voter Registration | comelec.gov.ph (JS-rendered; seed when blocked) |
| DTI | DTI | Business Name Registration | bnrs.dti.gov.ph |
| SSS | SSS | Membership Registration | sss.gov.ph become-a-member, valid IDs |
| PhilHealth | PHILHEALTH | Formal Economy Registration | philhealth.gov.ph/members/formal/registration.php |
| Pag-IBIG | PAGIBIG | Membership | pagibigfund.gov.ph |
| GSIS | GSIS | Member Services | gsis.gov.ph |
| Davao City LGU | LGU-DAVAO | Business Permit | davaocity.gov.ph |

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
Office/location entities extracted from Citizen's Charters and location fields.

| Column | Description |
|--------|-------------|
| `office_id`, `office_name`, `office_type` | e.g. consular_office, regional_office, bureau |
| `region`, `province`, `city`, `address` | Geographic fields (empty when not stated) |
| `latitude`, `longitude` | **Empty until geocoded** — never fabricated |
| `contact_number`, `operating_hours` | When available from source |

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

For document requirement mining:

```text
requirement_role IN ('required_document', 'acceptable_id', 'supporting_document')
AND scrape_status = 'success'
```

Run association mining:

```bash
python -m mining.association_analysis   # or via build.py (default)
```

Output: `output/association_document_pairs.csv`

## Browser fallback (Cloudflare)

```bash
python build.py --browser -a dfa psa lto
```

| Site | Status |
|------|--------|
| DFA consular | Live via Playwright |
| PhilSys, NBI, PRC, SSS, PhilHealth | Live via HTTP |
| PSA, LTO, Pag-IBIG, GSIS, COMELEC | Often blocked → seed/blocked rows |

## License / disclaimer

Public-domain government information. Always verify on official websites before legal or compliance use.
