# Philippine Government Document Requirements Dataset

A Python web scraper that extracts government service requirements from official Philippine government websites and stores each requirement as a separate row in a CSV file.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python scrape.py
```

Output is written to `data/gov_requirements.csv` by default.

## Scrape specific agencies

```bash
python scrape.py -a dfa nbi philsys sss
python scrape.py -o data/passport_only.csv -a dfa
python scrape.py -v
```

## Supported agencies

| Key | Agency | Primary source |
|-----|--------|----------------|
| `philsys` | PhilSys / PSA National ID | philsys.gov.ph |
| `psa` | PSA Civil Registration | psa.gov.ph |
| `dfa` | DFA Passport | consular.dfa.gov.ph, passport.gov.ph |
| `nbi` | NBI Clearance | nbi.gov.ph |
| `lto` | LTO Driver's License | lto.gov.ph |
| `prc` | PRC Licensure | prc.gov.ph |
| `comelec` | COMELEC Voter Registration | comelec.gov.ph |
| `dti` | DTI Business Name Registration | bnrs.dti.gov.ph |
| `sss` | SSS Membership | sss.gov.ph |
| `philhealth` | PhilHealth Registration | philhealth.gov.ph |
| `pagibig` | Pag-IBIG Membership | pagibigfund.gov.ph |
| `gsis` | GSIS Member Services | gsis.gov.ph |
| `davao` | Davao City LGU (sample LGU) | davaocity.gov.ph |

## CSV schema

### Core columns (requested)

| Column | Description |
|--------|-------------|
| `record_id` | Stable unique ID (`AGENCY-service-requirement-hash`) |
| `agency` | Issuing government agency |
| `service_name` | Service being applied for |
| `target_document` | Output document or credential |
| `transaction_type` | e.g. `new_application`, `renewal` |
| `applicant_type` | Who the requirement applies to |
| `requirement_name` | Short label for the requirement |
| `requirement_type` | `document`, `procedure`, `fee`, `eligibility`, etc. |
| `requirement_role` | `required_document`, `acceptable_id`, `supporting_document`, `procedure`, etc. |
| `conditional` | `yes` / `no` — is this requirement conditional? |
| `condition` | When the requirement applies |
| `issuing_agency` | Agency that issues the supporting document |
| `application_method` | `online`, `walk_in`, `online_and_walk_in`, etc. |
| `appointment_required` | `yes` / `no` / `unknown` |
| `processing_time` | Stated processing duration |
| `fee` | Stated fee amount |
| `location` | Where to apply |
| `source_url` | Official page scraped |
| `last_verified` | Date the record was scraped (ISO 8601) |

### Analyst extensions

| Column | Description |
|--------|-------------|
| `agency_code` | Short code for joins/filters |
| `service_category` | High-level grouping |
| `requirement_description` | Full extracted text |
| `document_format` | e.g. `original`, `photocopy`, `notarized` |
| `quantity` | Copies required, if stated |
| `fee_currency` | Default `PHP` |
| `source_section` | Heading/section on the source page |
| `requirement_order` | Sequence on the page |
| `scrape_status` | `success`, `partial`, `seed`, or `blocked` |
| `notes` | Scraper comments, fallback context |

## Scrape status values

- **success** — Parsed directly from live HTML
- **partial** — Some content extracted; page incomplete or portal-only
- **seed** — Baseline requirements when the site blocks bots or uses JS rendering
- **blocked** — Scraper could not access the page; manual verification needed

Several `.gov.ph` sites use Cloudflare, WAF, reCAPTCHA, or JavaScript rendering (PSA, LTO, Pag-IBIG, GSIS, COMELEC). The scraper records this explicitly rather than silently omitting agencies.

## Project layout

```
scrape.py                 # CLI entry point
config/sources.yaml       # Source registry (documentation)
scraper/
  models.py               # RequirementRecord + CSV columns
  http.py                 # HTTP client with retries
  base.py                 # Base scraper class
  registry.py             # Agency scraper registry
  csv_writer.py           # CSV export
  parsers/generic.py      # Shared HTML parsers
  agencies/               # One module per agency
data/
  gov_requirements.csv    # Generated output
```

## Design notes for data analysts

Each **requirement** is one row, not one service. A passport application might produce dozens of rows: core documents, conditional supporting documents, acceptable IDs, fees, and processing times.

Use `conditional` + `condition` to model branching logic (e.g. married females, late-registered birth certificates). Use `scrape_status` to filter production-ready vs. seeded records. Join on `agency_code` + `service_name` for service-level dashboards.

## Bypassing 403 / Cloudflare (PSA, LTO, DFA consular)

Some `.gov.ph` sites block plain HTTP requests. This project supports **Playwright** (headless Chromium) as a fallback.

### Setup (one time)

```bash
pip install playwright
python -m playwright install chromium
```

### Usage

```bash
# Automatic: try HTTP first, then Playwright on 403 (default)
python scrape.py

# Force browser for all fetches (slower, use for blocked agencies only)
python scrape.py --browser -a dfa psa lto

# Scrape only agencies that benefit from browser
python scrape.py -a dfa lto psa
```

### What works today

| Site | HTTP | Playwright fallback | Notes |
|------|------|---------------------|-------|
| DFA consular | 403 | **Works** | Full passport requirements |
| LTO portal | 403 on lto.gov.ph | Portal loads but is login-only | Use seed data; requirements not published on portal |
| PSA | 403 | Still blocked | Cloudflare blocks headless browsers; use seed data or manual browser export |

If PSA remains blocked, request certificates via [PSA Serbilis](https://psa.gov.ph/) and add a manual CSV supplement, or export requirements from the site in your browser and place them in `data/manual/psa_requirements.csv` (future enhancement).

## Limitations

- LGU requirements vary by city/municipality; this repo includes **Davao City** as a template.
- PRC list-of-requirements is large; parsing captures list items and documentary requirement blocks but may include navigation noise — filter by `requirement_type=document` for clean document lists.
- For blocked sites, install Playwright (see above) or use manual CSV supplements.

## License

Public domain government information; verify requirements on official sites before relying on this dataset for legal or compliance purposes.
